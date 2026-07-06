import os
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, log_loss
from sqlalchemy import create_engine
import json

# Try to import mlflow; if not installed/available, we will mock it
try:
    import mlflow
    import mlflow.xgboost
    mlflow_available = True
except ImportError:
    mlflow_available = False

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ballmetrix")

def compute_brier_score(y_true, y_prob):
    # outcome encoding: HOME_WIN=0, DRAW=1, AWAY_WIN=2
    num_classes = y_prob.shape[1]
    y_true_onehot = np.eye(num_classes)[y_true]
    return np.mean(np.sum((y_prob - y_true_onehot) ** 2, axis=1))

def train_model():
    print("Loading engineered features...")
    df = pd.read_csv("ml/data/processed/engineered_features.csv")
    
    # Feature columns
    feature_cols = ["home_elo", "away_elo", "elo_diff", "home_form", "away_form", "form_diff", "h2h_val"]
    X = df[feature_cols]
    
    # Target column mapping
    # HOME_WIN -> 0, DRAW -> 1, AWAY_WIN -> 2
    outcome_map = {"HOME_WIN": 0, "DRAW": 1, "AWAY_WIN": 2}
    y = df["outcome"].map(outcome_map)
    
    # Chronological Split: Train on seasons <= 2024, validate on seasons >= 2025
    train_mask = df["season"] <= 2024
    test_mask = df["season"] >= 2025
    
    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]
    
    if len(X_test) == 0:
        # Fallback if seasons don't split nicely
        print("Chronological split had no test data; using 80/20 random split instead.")
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
    print(f"Train size: {len(X_train)}, Validation size: {len(X_test)}")
    
    # Model Hyperparameters
    max_depth = 4
    n_estimators = 100
    learning_rate = 0.05
    
    model = XGBClassifier(
        max_depth=max_depth,
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        objective="multi:softprob",
        num_class=3,
        random_state=42
    )
    
    if mlflow_available:
        try:
            mlflow.set_tracking_uri("sqlite:///mlflow.db")
            mlflow.set_experiment("BallMetrix-Prediction")
            mlflow.start_run()
            mlflow.log_params({
                "max_depth": max_depth,
                "n_estimators": n_estimators,
                "learning_rate": learning_rate
            })
        except Exception as e:
            print(f"MLflow start run warning: {e}")
            
    # Train the XGBoost model
    model.fit(X_train, y_train)
    
    # Evaluate
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)
    
    accuracy = accuracy_score(y_test, preds)
    loss = log_loss(y_test, probs)
    brier = compute_brier_score(y_test.values, probs)
    
    print(f"Evaluation Metrics:")
    print(f"  Accuracy: {accuracy:.4f}")
    print(f"  Log Loss: {loss:.4f}")
    print(f"  Brier Score: {brier:.4f}")
    
    # Save the model locally
    os.makedirs("ml/models", exist_ok=True)
    model_path = "ml/models/active_model.json"
    model.save_model(model_path)
    print(f"Model saved locally to {model_path}")
    
    run_id = "local_xgboost_run"
    if mlflow_available and mlflow.active_run():
        try:
            mlflow.log_metrics({
                "accuracy": accuracy,
                "log_loss": loss,
                "brier_score": brier
            })
            mlflow.xgboost.log_model(model, "model")
            run_id = mlflow.active_run().info.run_id
            mlflow.end_run()
        except Exception as e:
            print(f"MLflow logging warning: {e}")

    # Log new model version to DB registry directly
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # Register version
            new_ver = f"v1.0.{int(pd.Timestamp.now().timestamp())}"
            # Check current models
            result = conn.execute(
                f"INSERT INTO model_versions (version_string, run_id, status, created_at) "
                f"VALUES ('{new_ver}', '{run_id}', 'candidate', NOW()) RETURNING id"
            ).fetchone()
            
            if result:
                ver_id = result[0]
                conn.execute(
                    f"INSERT INTO model_metrics (model_version_id, test_accuracy, test_log_loss, test_brier_score) "
                    f"VALUES ({ver_id}, {accuracy}, {loss}, {brier})"
                )
                print(f"Successfully registered model candidate {new_ver} in database registry!")
    except Exception as e:
        print(f"Database registration warning: {e}")

if __name__ == "__main__":
    train_model()
