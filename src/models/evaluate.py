"""evaluate.py — score every trained model on its held-out TEST set.

Phase 3 tuned the models on the TRAINING set (with cross-validation).  Phase 4
holds out the untouched test set — data the models have never seen — and asks:
"how well does each model really detect attacks?".

Metrics computed, in plain English (details in the phase explanation):

  accuracy  = correct predictions / all predictions
  precision = of the alarms raised, what fraction were TRUE attacks?
  recall    = of the real attacks, what fraction did we catch?
  F1        = a single number balancing precision and recall
  AUC-ROC   = how well the model ranks attacks above normal traffic (0.5 = guessing)

These are computed per class AND averaged across classes (macro), because in a
cybersecurity context the rare classes matter as much as the common ones.

Everything here runs on the PREPROCESSED test splits saved in Phase 2, using
the label encoders and models saved in Phase 3.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib
matplotlib.use("Agg")                      # non-interactive backend (save files, no window)
import matplotlib.pyplot as plt
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from src.utils import config as C

ALGORITHMS = ["logistic", "decision_tree", "random_forest", "xgboost"]

ALGO_LABELS = {
    "logistic": "Logistic Regression",
    "decision_tree": "Decision Tree",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
}

# Consistent colour palette (matches the "security operations centre" theme).
PALETTE = ["#7aa2f7", "#ff9e64", "#9ece6a", "#bb9af7"]


def load_test_data(dataset: str):
    """Load the held-out test split + label encoder for one dataset."""
    proc = C.DATA_PROCESSED_DIR
    X_test = pd.read_pickle(proc / f"{dataset}_test_X.pkl")
    y_test = pd.read_pickle(proc / f"{dataset}_test_y.pkl")   # category names (str)
    le = joblib.load(proc / f"{dataset}_label_encoder.joblib")
    return X_test, y_test, le


def _roc_macro(y_true_num: np.ndarray, proba: np.ndarray, n_classes: int):
    """Macro-average ROC curve for a multiclass model.

    A ROC curve plots the trade-off between catching attacks (true positive
    rate) and raising false alarms (false positive rate).  For several classes
    we draw one curve per class ("is it class c, or anything else?") and then
    average the curves together -> a single "macro" curve for the model.
    """
    fpr_grid = np.linspace(0.0, 1.0, 200)
    tprs = []
    for c in range(n_classes):
        y_bin = (y_true_num == c).astype(int)
        fpr, tpr, _ = roc_curve(y_bin, proba[:, c])
        tprs.append(np.interp(fpr_grid, fpr, tpr))  # line each curve onto the same grid
    tpr_macro = np.mean(tprs, axis=0)
    tpr_macro[0] = 0.0
    auc = roc_auc_score(y_true_num, proba, multi_class="ovr", average="macro")
    return fpr_grid, tpr_macro, auc


def evaluate_model(dataset: str, model_name: str):
    """Compute every metric for ONE (dataset, model) pair on the test set.

    Returns a dict of headline metrics plus a per-class table.
    """
    X_test, y_test, le = load_test_data(dataset)
    y_true_num = le.transform(y_test)                       # names -> 0..k-1

    model = joblib.load(C.MODELS_DIR / f"{dataset}_{model_name}.joblib")

    start = time.perf_counter()
    y_pred_num = model.predict(X_test)
    proba = model.predict_proba(X_test)
    predict_time = time.perf_counter() - start
    latency_ms = predict_time / len(X_test) * 1000.0        # ms per row on the full test

    y_pred = le.inverse_transform(y_pred_num)               # back to category names
    classes = list(le.classes_)

    # Headline (macro-averaged) metrics.
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average="macro", zero_division=0)
    rec = recall_score(y_test, y_pred, average="macro", zero_division=0)
    f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
    _, _, auc = _roc_macro(y_true_num, proba, len(classes))

    # Per-class precision / recall / F1 (so we can see the RARE classes).
    per_class = {}
    for idx, c in enumerate(classes):
        per_class[c] = {
            "precision": round(float(precision_score(
                y_test, y_pred, labels=[c], average=None, zero_division=0)[0]), 4),
            "recall": round(float(recall_score(
                y_test, y_pred, labels=[c], average=None, zero_division=0)[0]), 4),
            "f1": round(float(f1_score(
                y_test, y_pred, labels=[c], average=None, zero_division=0)[0]), 4),
        }

    return {
        "dataset": dataset,
        "model": model_name,
        "model_label": ALGO_LABELS[model_name],
        "accuracy": round(float(acc), 4),
        "precision_macro": round(float(prec), 4),
        "recall_macro": round(float(rec), 4),
        "f1_macro": round(float(f1), 4),
        "auc_roc_macro": round(float(auc), 4),
        "test_latency_ms_per_row": round(float(latency_ms), 4),
        "n_test_rows": int(len(X_test)),
        "classes": classes,
        "per_class": per_class,
        "confusion": confusion_matrix(y_test, y_pred, labels=classes).tolist(),
    }


def evaluate_dataset(dataset: str) -> tuple[pd.DataFrame, list[dict]]:
    """Run all four models on one dataset's test set."""
    results = []
    for name in ALGORITHMS:
        print(f"  evaluating {dataset} / {name} ...", flush=True)
        results.append(evaluate_model(dataset, name))

    df = pd.DataFrame([{k: v for k, v in r.items() if k != "per_class"}
                       for r in results])
    return df, results


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def plot_metric_bars(df: pd.DataFrame, dataset: str) -> Path:
    """Grouped bar chart: four models x the headline metrics."""
    metrics = ["accuracy", "precision_macro", "recall_macro",
               "f1_macro", "auc_roc_macro"]
    labels = ["Accuracy", "Precision", "Recall", "F1", "AUC-ROC"]

    x = np.arange(len(metrics))
    width = 0.2
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for i, (_, row) in enumerate(df.iterrows()):
        ax.bar(x + (i - 1.5) * width, [row[m] for m in metrics],
               width, label=row["model_label"], color=PALETTE[i % 4])
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("score")
    ax.set_title(f"{dataset.upper()} — test-set metrics by model")
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.08))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    path = C.REPORTS_DIR / "figures" / f"bar_metrics_{dataset}.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def plot_roc_overlay(dataset: str, results: list[dict]) -> Path:
    """One figure: the macro-average ROC curve of all four models overlaid."""
    X_test, y_test, le = load_test_data(dataset)
    y_true_num = le.transform(y_test)
    n_classes = len(le.classes_)

    fig, ax = plt.subplots(figsize=(7, 7))
    for i, r in enumerate(results):
        model = joblib.load(C.MODELS_DIR / f"{dataset}_{r['model']}.joblib")
        proba = model.predict_proba(X_test)
        fpr, tpr, auc = _roc_macro(y_true_num, proba, n_classes)
        ax.plot(fpr, tpr, color=PALETTE[i % 4], lw=2,
                label=f"{r['model_label']} (AUC = {auc:.3f})")
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="random guessing (AUC = 0.5)")
    ax.set_xlabel("False positive rate (false alarms)")
    ax.set_ylabel("True positive rate (attacks caught)")
    ax.set_title(f"{dataset.upper()} — ROC curves (macro average)")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)
    fig.tight_layout()

    path = C.REPORTS_DIR / "figures" / f"roc_{dataset}.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def plot_confusion_grid(dataset: str, results: list[dict]) -> Path:
    """2x2 grid of confusion-matrix heatmaps, one per model.

    Rows are TRUE class, columns are what the model PREDICTED.  Each row sums
    to 100%, so the diagonal shows "of the real X's, how many we caught".
    A perfect model has a bright diagonal and nothing off it.
    """
    classes = results[0]["classes"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    for ax, r in zip(axes.flat, results):
        cm = np.array(r["confusion"], dtype=float)
        cm = cm / cm.sum(axis=1, keepdims=True)   # normalise per true class
        sns.heatmap(cm, annot=True, fmt=".2f", cmap="magma", vmin=0, vmax=1,
                    xticklabels=classes, yticklabels=classes, ax=ax,
                    annot_kws={"size": 8})
        ax.set_title(f"{r['model_label']}")
        ax.set_xlabel("predicted")
        ax.set_ylabel("true")
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.suptitle(f"{dataset.upper()} — confusion matrices on the test set (rows = 100%)",
                 y=1.0)
    fig.tight_layout()

    path = C.REPORTS_DIR / "figures" / f"confusion_{dataset}.png"
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def generate_report(
    nsl_df: pd.DataFrame, nsl_results: list[dict],
    cic_df: pd.DataFrame, cic_results: list[dict],
) -> Path:
    """Auto-write reports/model_comparison_report.md from the measured results."""
    def rows_for(df):
        return [
            [r["model_label"], f"{r['accuracy']:.4f}", f"{r['precision_macro']:.4f}",
             f"{r['recall_macro']:.4f}", f"{r['f1_macro']:.4f}",
             f"{r['auc_roc_macro']:.4f}", f"{r['test_latency_ms_per_row']:.4f}"]
            for r in df.to_dict("records")
        ]

    def md_table(rows, header):
        out = "| " + " | ".join(header) + " |\n"
        out += "|" + "|".join(["---"] * len(header)) + "|\n"
        for r in rows:
            out += "| " + " | ".join(map(str, r)) + " |\n"
        return out

    best_nsl = nsl_df.loc[nsl_df["f1_macro"].idxmax()]
    best_cic = cic_df.loc[cic_df["f1_macro"].idxmax()]

    text = f"""# Model Comparison Report

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

## NSL-KDD (test set: {nsl_df['n_test_rows'].iloc[0]:,} rows)

{md_table(rows_for(nsl_df), ["Model", "Accuracy", "Precision", "Recall", "F1", "AUC-ROC", "Latency (ms/row)"])}

Best overall F1 on NSL-KDD: **{best_nsl['model_label']}** ({best_nsl['f1_macro']:.4f}).

### NSL-KDD — per-class recall (share of each true class caught)

| Class | {" | ".join(r['model_label'] for r in nsl_results)} |
|---|{"|".join(["---"] * len(nsl_results))}|
"""
    classes_nsl = nsl_results[0]["classes"]
    rows_recall = []
    for c in classes_nsl:
        row = [c] + [f"{r['per_class'][c]['recall']:.3f}" for r in nsl_results]
        rows_recall.append(row)
    text += "\n".join("| " + " | ".join(map(str, r)) + " |" for r in rows_recall) + "\n\n"

    text += f"""## CICIDS2017 (test set: {cic_df['n_test_rows'].iloc[0]:,} rows)

{md_table(rows_for(cic_df), ["Model", "Accuracy", "Precision", "Recall", "F1", "AUC-ROC", "Latency (ms/row)"])}

Best overall F1 on CICIDS2017: **{best_cic['model_label']}** ({best_cic['f1_macro']:.4f}).

### CICIDS2017 — per-class recall (share of each true class caught)

| Class | {" | ".join(r['model_label'] for r in cic_results)} |
|---|{"|".join(["---"] * len(cic_results))}|
"""
    classes_cic = cic_results[0]["classes"]
    rows_recall_c = []
    for c in classes_cic:
        row = [c] + [f"{r['per_class'][c]['recall']:.3f}" for r in cic_results]
        rows_recall_c.append(row)
    text += "\n".join("| " + " | ".join(map(str, r)) + " |" for r in rows_recall_c) + "\n\n"

    text += """## Interpretation notes

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
"""
    path = C.REPORTS_DIR / "model_comparison_report.md"
    path.write_text(text, encoding="utf-8")
    return path


def run_all() -> dict:
    """Evaluate both datasets, draw charts, save JSON + the report."""
    all_data = {}
    for dataset in ["nslkdd", "cicids"]:
        print(f"=== Evaluating {dataset} ===")
        df, results = evaluate_dataset(dataset)
        plot_metric_bars(df, dataset)
        plot_roc_overlay(dataset, results)
        plot_confusion_grid(dataset, results)
        all_data[dataset] = results
        print(df[["model", "accuracy", "precision_macro", "recall_macro",
                  "f1_macro", "auc_roc_macro"]].to_string(index=False))

    # JSON the /compare endpoint and the frontend will read.
    out = C.DATA_PROCESSED_DIR / "evaluation_results.json"
    out.write_text(json.dumps(all_data, indent=2), encoding="utf-8")

    # Copies of the charts where the web app can serve them statically.
    pub = C.FRONTEND_PUBLIC_DIR
    pub.mkdir(parents=True, exist_ok=True)
    for src in (C.REPORTS_DIR / "figures").glob("*.png"):
        (pub / src.name).write_bytes(src.read_bytes())
    (pub / "evaluation_results.json").write_text(
        json.dumps(all_data, indent=2), encoding="utf-8")

    nsl_df = pd.DataFrame([{k: v for k, v in r.items() if k != "per_class"}
                           for r in all_data["nslkdd"]])
    cic_df = pd.DataFrame([{k: v for k, v in r.items() if k != "per_class"}
                           for r in all_data["cicids"]])
    report = generate_report(nsl_df, all_data["nslkdd"], cic_df, all_data["cicids"])
    print("\nReport written:", report)
    return all_data


if __name__ == "__main__":
    run_all()
