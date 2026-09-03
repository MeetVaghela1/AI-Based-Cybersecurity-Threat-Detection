# Model Comparison Report

**Generated automatically by `src/models/evaluate.py` (Phase 4).**

All models were tuned with grid search + stratified 5-fold cross-validation
on the TRAINING set (Phase 3) and scored here on the untouched TEST set.
SMOTE was applied inside the cross-validation folds and never to test data.

## Headline results

| Metric (macro-averaged) | Meaning |
|---|---|
| Accuracy | share of connections classified correctly |
| Precision | of the alarms raised, the share that were real attacks |
| Recall | of the real attacks, the share that were caught |
| F1 | harmonic mean of precision & recall (single balance number) |
| AUC-ROC | chance (0.5) to perfect (1.0) ranking of attacks over normal |

## NSL-KDD (test set: 22,544 rows)

| Model | Accuracy | Precision | Recall | F1 | AUC-ROC | Latency (ms/row) |
|---|---|---|---|---|---|---|
| Logistic Regression | 0.7628 | 0.6707 | 0.6295 | 0.5572 | 0.9057 | 0.0008 |
| Decision Tree | 0.8163 | 0.7545 | 0.5836 | 0.6170 | 0.7672 | 0.0006 |
| Random Forest | 0.7488 | 0.7972 | 0.5081 | 0.5384 | 0.9489 | 0.0089 |
| XGBoost | 0.7782 | 0.8281 | 0.5653 | 0.6086 | 0.9491 | 0.0027 |


Best overall F1 on NSL-KDD: **Decision Tree** (0.6170).

### NSL-KDD — per-class recall (share of each true class caught)

| Class | Logistic Regression | Decision Tree | Random Forest | XGBoost |
|---|---|---|---|---|
| DoS | 0.810 | 0.900 | 0.760 | 0.820 |
| Normal | 0.923 | 0.962 | 0.973 | 0.973 |
| Probe | 0.727 | 0.688 | 0.592 | 0.626 |
| R2L | 0.134 | 0.234 | 0.111 | 0.154 |
| U2R | 0.552 | 0.134 | 0.104 | 0.254 |

## CICIDS2017 (test set: 15,606 rows)

| Model | Accuracy | Precision | Recall | F1 | AUC-ROC | Latency (ms/row) |
|---|---|---|---|---|---|---|
| Logistic Regression | 0.9549 | 0.8391 | 0.8622 | 0.8267 | 0.9784 | 0.0006 |
| Decision Tree | 0.9972 | 0.9951 | 0.9257 | 0.9505 | 0.9629 | 0.0004 |
| Random Forest | 0.9970 | 0.9925 | 0.8944 | 0.9276 | 0.9919 | 0.0063 |
| XGBoost | 0.9988 | 0.9974 | 0.9832 | 0.9897 | 1.0000 | 0.0067 |


Best overall F1 on CICIDS2017: **XGBoost** (0.9897).

### CICIDS2017 — per-class recall (share of each true class caught)

| Class | Logistic Regression | Decision Tree | Random Forest | XGBoost |
|---|---|---|---|---|
| Botnet | 0.985 | 0.995 | 1.000 | 0.998 |
| Brute Force | 0.995 | 1.000 | 1.000 | 1.000 |
| DDoS | 0.988 | 1.000 | 1.000 | 1.000 |
| DoS | 0.972 | 0.998 | 0.998 | 0.999 |
| Heartbleed | 0.500 | 0.500 | 0.500 | 1.000 |
| Infiltration | 0.571 | 0.857 | 0.571 | 0.857 |
| Normal | 0.831 | 0.992 | 0.991 | 0.998 |
| PortScan | 0.994 | 0.998 | 0.999 | 0.998 |
| Web Attack | 0.924 | 0.991 | 0.991 | 1.000 |

## Interpretation notes

* **Recall matters most.** A missed attack (false negative) is far more
  dangerous than a false alarm (false positive) — the attacker gets in.
  The recall column is therefore the "safety" column of this table.
* **Rare classes are the hard part.** Classes with only a handful of real
  rows in training (U2R in NSL-KDD, Heartbleed/Infiltration in CICIDS2017)
  are the hardest to detect.  SMOTE helps, but a model cannot learn from
  data it has almost never seen.
* **Latency.** Every model answers in well under a millisecond per row, so
  all four are fast enough to run on a live network link — the choice
  between them is accuracy vs. interpretability/complexity, not speed.

## Charts

Charts live in `reports/figures/` (and copies in `frontend/public/`):
`bar_metrics_<dataset>.png`, `roc_<dataset>.png`, `confusion_<dataset>.png`.
