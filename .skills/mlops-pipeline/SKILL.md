---
name: mlops-pipeline
description: Best practices for implementing a reproducible ML pipeline using DVC, MLflow tracking, XGBoost classifiers, and automated promotion gates.
---

# MLOps Pipeline & Reproductibility

This skill guidelines the setup of DVC, MLflow, model training, and promotion gates in the `ml/` service.

## Data Version Control (DVC)
- Initialize DVC inside the `ml/` or root workspace directory.
- Keep raw datasets (`ml/data/raw/`) and engineered features (`ml/data/processed/`) versioned via DVC:
  ```bash
  dvc add ml/data/raw/historical_matches.csv
  dvc add ml/data/processed/engineered_features.parquet
  ```
- Track the `.dvc` files in Git to align data versions with specific code commits.

## MLflow Tracking
- Log all training runs to an MLflow server.
- Record the following for each run:
  - **Parameters**: `learning_rate`, `max_depth`, `n_estimators`, `subsample`, `colsample_bytree`.
  - **Metrics**: `log_loss`, `accuracy`, `brier_score`, `roc_auc`.
  - **Artifacts**: XGBoost model binaries (`.json`), SHAP summary plots, and feature importance configurations.
  - **Tags**: Git commit hash, dataset version (DVC hash), and target competition/season.

## Model Promotion Gates
- A newly trained model must not be automatically promoted to "production" status unless it meets validation criteria:
  1. Evaluate the new candidate model on a chronologically held-out validation set (e.g., the latest completed season/matches).
  2. Load the current production model's metrics from the `model_metrics` database table or the MLflow Model Registry.
  3. Compare accuracy, log loss, and Brier score.
  4. If the new model outperforms the production model by a defined threshold (e.g., >0.005 improvement in Brier score/log loss), transition the new model to `production` and demote the old one. Otherwise, keep it as `candidate`.
