"""seeder.py — fill the database from the real artifacts copied by setup.py.

Sources of truth (both copied from the main project into artifacts/):
    artifacts/models_metadata.json        per-model CV scores, latency, params
    artifacts/evaluation_results.json     per-model test metrics + per-class

The dataset rows (train sizes, SMOTE sizes) are the real measured numbers from
the main project's notebooks 02/03 — recorded here once, as facts.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import config, db


def _load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing artifact: {path}. Run  scripts/setup.py  first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


# Real measured dataset facts (from the main project's runs).
DATASET_FACTS = {
    "nslkdd": {
        "name": "NSL-KDD",
        "year": 2009,
        "rows_train_raw": 125_973,
        "rows_train_after_smote": 154_926,
        "notes": "Classic benchmark. Its test set deliberately contains attack "
                 "variants never seen in training, so test scores drop there "
                 "on purpose (that is the generalisation measurement).",
    },
    "cicids": {
        "name": "CICIDS2017",
        "year": 2017,
        "rows_train_raw": 62_422,
        "rows_train_after_smote": 108_000,
        "notes": "Modern traffic, heavily imbalanced (Heartbleed has 11 rows in "
                 "the whole dataset). Loader caps big classes at 15,000 and "
                 "SMOTE balances training to 12,000 per class.",
    },
}

PIPELINE_STEPS = [
    ("Phase 0", "Environment & folder setup",
     "Pinned requirements.txt, Python 3.12 venv, config module with random seed 42."),
    ("Phase 0.5", "Data acquisition & manifest",
     "NSL-KDD and CICIDS2017 placed under data/raw with a documented manifest."),
    ("Phase 1", "Exploratory data analysis",
     "Found heavy class imbalance: 67,343 Normal vs 52 U2R (NSL-KDD); ~80% normal in CICIDS2017."),
    ("Phase 2", "Preprocessing & feature selection",
     "Cleaned labels/Infinity values, median imputation, min-max scaling, one-hot "
     "encoding, SMOTE (training only, never the test set), 3 feature-selection methods."),
    ("Phase 3", "Model training & tuning",
     "Grid search + stratified 5-fold CV, SMOTE inside the folds, f1-macro scoring; 8 models saved."),
    ("Phase 4", "Evaluation on the untouched test set",
     "Accuracy, precision, recall, F1, AUC-ROC, latency and per-class recall; "
     "report written to reports/model_comparison_report.md."),
    ("Phase 5", "Backend API",
     "FastAPI app serving the models (/models, /predict, /simulate, ...); 14 tests pass."),
    ("Phase 6", "Frontend dashboard",
     "React dashboard: live monitor, model comparison, attack explainer."),
    ("Phase 7", "Documentation",
     "README, deployment guidelines, glossary, examiner Q&A, setup guide."),
]


def seed_if_empty() -> bool:
    """Seed the DB only if it is empty. Returns True if seeding happened."""
    with db.get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
        if count > 0:
            return False

        meta = _load(config.ARTIFACT_DIR / "models_metadata.json")
        eval_data = _load(config.ARTIFACT_DIR / "evaluation_results.json")

        # --- datasets ----------------------------------------------------
        for key, fact in DATASET_FACTS.items():
            entry = next(e for e in meta if e["dataset"] == key)
            conn.execute(
                """
                INSERT INTO datasets (
                    name, year, rows_train_raw, rows_train_after_smote,
                    rows_test, n_features, n_classes, classes, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact["name"],
                    fact["year"],
                    fact["rows_train_raw"],
                    fact["rows_train_after_smote"],
                    eval_data[key][0]["n_test_rows"],
                    entry["n_features"],
                    len(entry["classes"]),
                    json.dumps(entry["classes"]),
                    fact["notes"],
                ),
            )

        # --- models + test metrics + per-class ---------------------------
        for entry in meta:
            dataset = entry["dataset"]
            model_name = entry["model"]
            conn.execute(
                """
                INSERT INTO models (
                    dataset, model_name, model_label, cv_f1_macro, cv_f1_std,
                    fit_time_s, n_hyperparameter_combinations, cv_folds,
                    latency_ms_per_row, n_train_rows, n_features, classes,
                    best_params, trained_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset,
                    model_name,
                    config.MODEL_LABELS[model_name],
                    entry["cv_score_mean_f1_macro"],
                    entry["cv_score_std_f1_macro"],
                    entry["fit_time_s"],
                    entry["n_hyperparameter_combinations"],
                    entry["cv_folds"],
                    entry["latency_ms_per_row"],
                    entry["n_train_rows"],
                    entry["n_features"],
                    json.dumps(entry["classes"]),
                    json.dumps(entry["best_params"]),
                    entry["trained_at"],
                ),
            )

            ev = next(e for e in eval_data[dataset] if e["model"] == model_name)
            conn.execute(
                """
                INSERT INTO test_metrics (
                    dataset, model_name, n_test_rows, accuracy, precision_macro,
                    recall_macro, f1_macro, auc_roc_macro, test_latency_ms_per_row
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset,
                    model_name,
                    ev["n_test_rows"],
                    ev["accuracy"],
                    ev["precision_macro"],
                    ev["recall_macro"],
                    ev["f1_macro"],
                    ev["auc_roc_macro"],
                    ev["test_latency_ms_per_row"],
                ),
            )

            for class_name, metrics in ev["per_class"].items():
                conn.execute(
                    """
                    INSERT INTO per_class_metrics (
                        dataset, model_name, class_name, precision, recall, f1
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dataset,
                        model_name,
                        class_name,
                        metrics["precision"],
                        metrics["recall"],
                        metrics["f1"],
                    ),
                )

        # --- pipeline steps ----------------------------------------------
        for index, (phase, title, detail) in enumerate(PIPELINE_STEPS):
            conn.execute(
                "INSERT INTO pipeline_steps (phase, title, detail, ord) VALUES (?, ?, ?, ?)",
                (phase, title, detail, index),
            )

        return True
