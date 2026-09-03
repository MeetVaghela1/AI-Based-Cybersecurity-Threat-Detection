"""generate_docs.py — fill the numbers in docs/PHASE_EXPLANATIONS.md dynamically.

Reads the JSON artifacts produced by training/evaluation and replaces the
{{PLACEHOLDER}} tokens in the document with freshly-built markdown tables, so
the prose never drifts from the actual results.

Usage:
    .venv\\Scripts\\python.exe -m src.utils.generate_docs

Run it again after retraining (python -m src.models.train) or after re-running
notebook 04 and the document's numbers update themselves.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.utils import config as C

ROOT = Path(__file__).resolve().parents[2]
EVAL_JSON = ROOT / "data" / "processed" / "evaluation_results.json"
META_JSON = C.MODELS_DIR / "models_metadata.json"
DOC = ROOT / "docs" / "PHASE_EXPLANATIONS.md"
WALKTHROUGH_DOC = ROOT / "docs" / "PROJECT_WALKTHROUGH.md"

MODEL_ORDER = ["logistic", "decision_tree", "random_forest", "xgboost"]
MODEL_LABELS = {
    "logistic": "Logistic Regression",
    "decision_tree": "Decision Tree",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
}


def _fmt(value: float) -> str:
    return f"{value:.4f}"


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact: {path}. Train/evaluate first.")
    return json.loads(path.read_text(encoding="utf-8"))


def cv_table(meta: list[dict]) -> str:
    rows = ["| Dataset | Model | CV F1-macro |", "|---|---|---:|"]
    # group CV scores by dataset/model in canonical order
    by_ds: dict[str, dict[str, float]] = {}
    for entry in meta:
        by_ds.setdefault(entry["dataset"], {})[entry["model"]] = entry[
            "cv_score_mean_f1_macro"
        ]
    for dataset in ["nslkdd", "cicids"]:
        for model in MODEL_ORDER:
            if model in by_ds.get(dataset, {}):
                rows.append(
                    f"| {dataset} | {MODEL_LABELS[model]} | "
                    f"{_fmt(by_ds[dataset][model])} |"
                )
    return "\n".join(rows)


def test_table(eval_data: dict, dataset: str) -> str:
    entries = {e["model"]: e for e in eval_data[dataset]}
    rows = [
        "| Model | Accuracy | Precision | Recall | F1 | AUC-ROC | Latency (ms/row) |",
        "|---|---|---|---|---|---|---:|",
    ]
    for model in MODEL_ORDER:
        e = entries[model]
        rows.append(
            f"| {MODEL_LABELS[model]} | {_fmt(e['accuracy'])} | "
            f"{_fmt(e['precision_macro'])} | {_fmt(e['recall_macro'])} | "
            f"{_fmt(e['f1_macro'])} | {_fmt(e['auc_roc_macro'])} | "
            f"{_fmt(e['test_latency_ms_per_row'])} |"
        )
    return "\n".join(rows)


def per_class_table(eval_data: dict, dataset: str, metric: str = "recall") -> str:
    entries = {e["model"]: e for e in eval_data[dataset]}
    first = entries[MODEL_ORDER[0]]
    classes = first["classes"]
    rows = [f"| Class | {' | '.join(MODEL_LABELS[m] for m in MODEL_ORDER)} |"]
    rows.append("|---|---" * len(MODEL_ORDER) + "|")
    for cls in classes:
        cells = []
        for model in MODEL_ORDER:
            cells.append(_fmt(entries[model]["per_class"][cls][metric]))
        rows.append(f"| {cls} | {' | '.join(cells)} |")
    return "\n".join(rows)


def best_test(eval_data: dict, dataset: str) -> str:
    entries = {e["model"]: e for e in eval_data[dataset]}
    best = max(MODEL_ORDER, key=lambda m: entries[m]["f1_macro"])
    return f"{MODEL_LABELS[best]} ({_fmt(entries[best]['f1_macro'])})"


def best_cv(meta: list[dict], dataset: str) -> str:
    entries = [e for e in meta if e["dataset"] == dataset]
    best = max(entries, key=lambda e: e["cv_score_mean_f1_macro"])
    return f"{MODEL_LABELS[best['model']]} ({_fmt(best['cv_score_mean_f1_macro'])})"


def registry_snapshot(meta: list[dict], eval_data: dict) -> str:
    test_f1: dict[tuple[str, str], float] = {
        (e["dataset"], e["model"]): e["f1_macro"]
        for dataset in eval_data
        for e in eval_data[dataset]
    }
    rows = [
        "| Dataset | Model | CV F1-macro | Test F1 | Latency (ms/row) | Train rows | Trained at |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for entry in sorted(meta, key=lambda e: (e["dataset"], e["model"])):
        key = (entry["dataset"], entry["model"])
        rows.append(
            f"| {entry['dataset']} | {MODEL_LABELS[entry['model']]} | "
            f"{_fmt(entry['cv_score_mean_f1_macro'])} | "
            f"{_fmt(test_f1.get(key, float('nan')))} | "
            f"{_fmt(entry['latency_ms_per_row'])} | "
            f"{entry['n_train_rows']:,} | {entry['trained_at']} |"
        )
    return "\n".join(rows)


def _fill(doc: Path, replacements: dict[str, str]) -> None:
    """Replace {{PLACEHOLDER}} tokens in one markdown document."""
    text = doc.read_text(encoding="utf-8")
    for name, value in replacements.items():
        text = text.replace("{{" + name + "}}", value)

    leftover = re.findall(r"\{\{\w+\}\}", text)
    doc.write_text(text, encoding="utf-8")
    print(f"Wrote {doc}")
    if leftover:
        print("Unfilled placeholders still present:", sorted(set(leftover)))
    else:
        print("All placeholders filled.")


def main() -> None:
    meta = _load_json(META_JSON)
    eval_data = _load_json(EVAL_JSON)

    replacements = {
        "CV_F1_MACRO_TABLE": cv_table(meta),
        "BEST_CV_NSL": best_cv(meta, "nslkdd"),
        "BEST_CV_CICIDS": best_cv(meta, "cicids"),
        "NSL_TEST_TABLE": test_table(eval_data, "nslkdd"),
        "CICIDS_TEST_TABLE": test_table(eval_data, "cicids"),
        "PER_CLASS_NSL": per_class_table(eval_data, "nslkdd"),
        "PER_CLASS_CICIDS": per_class_table(eval_data, "cicids"),
        "N_NSL_TEST": f"{eval_data['nslkdd'][0]['n_test_rows']:,}",
        "N_CICIDS_TEST": f"{eval_data['cicids'][0]['n_test_rows']:,}",
        "BEST_TEST_NSL": best_test(eval_data, "nslkdd"),
        "BEST_TEST_CICIDS": best_test(eval_data, "cicids"),
        "REGISTRY_SNAPSHOT": registry_snapshot(meta, eval_data),
    }

    for doc in (DOC, WALKTHROUGH_DOC):
        if doc.exists():
            _fill(doc, replacements)


if __name__ == "__main__":
    main()
