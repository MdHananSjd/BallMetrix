import os
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ballmetrix")

def evaluate_and_promote():
    print("Running Model Evaluation Promotion Gate...")
    
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # 1. Fetch current production model version
            prod_row = conn.execute(
                "SELECT mv.id, mv.version_string, mm.test_accuracy, mm.test_log_loss, mm.test_brier_score "
                "FROM model_versions mv JOIN model_metrics mm ON mv.id = mm.model_version_id "
                "WHERE mv.status = 'production' LIMIT 1"
            ).fetchone()
            
            # 2. Fetch latest candidate model version (which is not production)
            candidate_row = conn.execute(
                "SELECT mv.id, mv.version_string, mm.test_accuracy, mm.test_log_loss, mm.test_brier_score "
                "FROM model_versions mv JOIN model_metrics mm ON mv.id = mm.model_version_id "
                "WHERE mv.status = 'candidate' "
                "ORDER BY mv.created_at DESC LIMIT 1"
            ).fetchone()
            
            if not candidate_row:
                print("No candidate models found in registry for evaluation.")
                return
                
            cand_id, cand_ver, cand_acc, cand_loss, cand_brier = candidate_row
            print(f"Latest Candidate: {cand_ver} (Acc: {cand_acc:.4f}, Loss: {cand_loss:.4f}, Brier: {cand_brier:.4f})")
            
            if not prod_row:
                # No production model exists, auto-promote candidate
                print("No production model found in registry. Auto-promoting candidate directly to production.")
                conn.execute(f"UPDATE model_versions SET status = 'production' WHERE id = {cand_id}")
                print(f"Model {cand_ver} is now promoted to PRODUCTION.")
                return
                
            prod_id, prod_ver, prod_acc, prod_loss, prod_brier = prod_row
            print(f"Current Production: {prod_ver} (Acc: {prod_acc:.4f}, Loss: {prod_loss:.4f}, Brier: {prod_brier:.4f})")
            
            # Promotion logic: Promote if Candidate's Brier Score is lower OR if Accuracy is higher
            # Lower Brier score/log loss means better calibrated probabilities.
            is_better = (cand_brier < prod_brier) or (cand_acc > prod_acc + 0.01)
            
            if is_better:
                print(f"Promotion Gate Passed! Candidate {cand_ver} outperforms Production {prod_ver}.")
                # Demote old production
                conn.execute(f"UPDATE model_versions SET status = 'deprecated' WHERE id = {prod_id}")
                # Promote candidate
                conn.execute(f"UPDATE model_versions SET status = 'production' WHERE id = {cand_id}")
                print(f"Model {cand_ver} successfully promoted to PRODUCTION.")
            else:
                print(f"Promotion Gate Failed. Candidate {cand_ver} does not outperform Production {prod_ver}. Left in candidate pool.")
                
    except Exception as e:
        print(f"Error during model evaluation: {e}")

if __name__ == "__main__":
    evaluate_and_promote()
