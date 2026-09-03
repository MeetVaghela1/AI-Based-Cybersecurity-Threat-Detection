# Model & Dataset Usage Statistics

All numbers are real measurements from the saved registry (`src/models/registry/
models_metadata.json`), `data/processed/evaluation_results.json`, and the Phase 2
processing logs. Peak memory was not recorded (marked "—").

## Dataset sizes through the pipeline

| Dataset | Raw rows parsed | After cleaning (capped) | Train / Test split | After SMOTE (train only) |
|---|---|---:|---:|---:|
| NSL-KDD | 125,973 (train) / 22,544 (test) | unchanged | 125,973 / 22,544 | 154,926 (R2L & U2R boosted to 15,000) |
| CICIDS2017 | 2,830,743 (8 CSV files) | 62,422 (classes capped at 15,000, rare classes kept in full) | 62,422 / 15,606 | 108,000 (all 9 classes balanced to 12,000) |

## Feature counts

| Dataset | Raw features | After one-hot encoding | Feature-selection consensus (of the 3 methods) |
|---|---|---:|---:|
| NSL-KDD | 41 | 122 | 15 |
| CICIDS2017 | 78 | 78 | 7 |

## Hyperparameter search, per model (both datasets identical)

| Model | Grid combinations tried | Cross-validation folds | Search score |
|---|---|---:|---:|---|
| Logistic Regression | 4 (`C` × 4) | 5 | f1-macro |
| Decision Tree | 9 (depth × min_leaf) | 5 | f1-macro |
| Random Forest | 8 (trees × depth × min_leaf) | 5 | f1-macro |
| XGBoost | 8 (rounds × depth × learning rate) | 5 | f1-macro |

## Training time, CV score and inference latency

### NSL-KDD

| Model | Grid combos | CV folds | Fit time (s) | CV F1-macro | Test latency (ms/row) |
|---|---|---|---|---|---|
| Decision Tree | 9 | 5 | 25.2 | 0.8907 | 0.0004 |
| Logistic Regression | 4 | 5 | 120.4 | 0.7432 | 0.0005 |
| Random Forest | 8 | 5 | 204.7 | 0.9333 | 0.0095 |
| XGBoost | 8 | 5 | 181.3 | 0.9565 | 0.0021 |

### CICIDS2017

| Model | Grid combos | CV folds | Fit time (s) | CV F1-macro | Test latency (ms/row) |
|---|---|---|---|---|---|
| Decision Tree | 9 | 5 | 28.0 | 0.9908 | 0.0003 |
| Logistic Regression | 4 | 5 | 66.9 | 0.8755 | 0.0003 |
| Random Forest | 8 | 5 | 112.9 | 0.9765 | 0.0052 |
| XGBoost | 8 | 5 | 195.1 | 0.9848 | 0.0047 |

Notes: latency is milliseconds per test-set row, measured after warm-up on the
untouched test set. All fits ran on a single machine (see the thesis compute
notes); training is fully reproducible via `python -m src.models.train`.
