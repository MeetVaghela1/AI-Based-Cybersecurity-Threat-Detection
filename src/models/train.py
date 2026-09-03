"""train.py — grid search + stratified k-fold CV for the four classifiers.

The four algorithms we compare (see the plain-language explanations in
notebooks/03_model_training.ipynb):
    Logistic Regression, Decision Tree, Random Forest, XGBoost.

HOW THIS MODULE WORKS
--------------------
For each (dataset, algorithm) pair it runs a GridSearchCV:
    * an inner stratified k-fold CV (the data is split into k folds, the model
      is trained on k-1 of them and scored on the held-out fold; each fold gets
      its turn as the held-out one, and every fold keeps the SAME class
      proportions as the full data -> "stratified"),
    * across a grid of hyperparameter combinations (e.g. "how deep may the
      trees grow?", "how many trees?", "how strong the regularisation?"),
    * the combination with the best cross-validation score is kept, and the
      winning model is refitted on the WHOLE training set.

WHY SMOTE IS INSIDE THE PIPELINE
--------------------------------
SMOTE is placed *inside* the pipeline that GridSearchCV cross-validates, so it
is re-fitted on each fold's TRAINING portion only.  This avoids a subtle data
leak: if we SMOTE'd the full training set first and then split it into folds,
synthetic rows generated from one fold's data could end up in another fold,
and the model would have literally seen some of its validation data.

WHY f1_macro AS THE SCORING METRIC
----------------------------------
Accuracy is useless with imbalanced classes (a model could score 80% by never
predicting an attack).  f1_macro = the average F1 across classes, giving the
rare classes the same weight as the common ones, so the tuner is forced to
care about detecting every attack type.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import pandas as pd
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

from src.utils import config as C

# ---------------------------------------------------------------------------
# The four algorithms and the hyperparameter grids we search.
# (Hyperparameter = a "dials" the data scientist sets before training, e.g.
#  how deep a tree may grow.  Grid search = try every combination on the dials.)
# ---------------------------------------------------------------------------
MODELS = {
    "logistic": (
        LogisticRegression(max_iter=2000, random_state=C.RANDOM_STATE),
        {"C": [0.01, 0.1, 1.0, 10.0]},        # strength of regularisation
    ),
    "decision_tree": (
        DecisionTreeClassifier(random_state=C.RANDOM_STATE),
        {
            "max_depth": [None, 10, 20],      # how deep the yes/no questions may go
            "min_samples_leaf": [1, 5, 20],   # min rows a leaf must cover
        },
    ),
    "random_forest": (
        RandomForestClassifier(
            n_jobs=4,                         # parallel tree building
            random_state=C.RANDOM_STATE,
        ),
        {
            "n_estimators": [100, 200],       # number of trees
            "max_depth": [None, 20],          # depth limit per tree
            "min_samples_leaf": [1, 5],       # min rows per leaf
        },
    ),
    "xgboost": (
        XGBClassifier(
            n_jobs=4,
            random_state=C.RANDOM_STATE,
            eval_metric="mlogloss",           # multiclass log-loss as XGB's metric
        ),
        {
            "n_estimators": [100, 200],       # number of boosting rounds
            "max_depth": [3, 6],              # depth per tree
            "learning_rate": [0.1, 0.3],      # how hard each tree corrects
        },
    ),
}

# Per-dataset SMOTE strategy (same choice as Phase 2).
#   NSL-KDD: only boost the two truly tiny classes up to 15,000 rows.
#   CICIDS2017: "auto" balances every class up to the majority class.
SMOTE_STRATEGY = {
    "nslkdd": {"R2L": 15_000, "U2R": 15_000},
    "cicids": "auto",
}


def tune_model(
    model_name: str,
    X: pd.DataFrame,
    y: pd.Series,
    smote_strategy: str | dict = "auto",
    cv_folds: int = 5,
    n_jobs: int = 4,
    verbose: int = 1,
) -> dict:
    """Run grid search + stratified k-fold CV for one algorithm on one dataset.

    Args:
        model_name: key into MODELS ("logistic", "decision_tree", ...).
        X, y: preprocessed training features and labels (PRE-SMOTE).
        smote_strategy: how aggressively SMOTE balances (train-only, inside CV).
        cv_folds: number of stratified folds (k).
        n_jobs: how many folds to run in parallel (machine has 16 cores).

    Returns a dictionary with the model, best params, CV score, timings.
    """
    estimator, param_grid = MODELS[model_name]

    # XGBoost (unlike sklearn's other classifiers) demands numeric labels
    # 0..k-1, so we encode once here. LabelEncoder sorts alphabetically, so the
    # mapping is deterministic and matches the label encoders saved in Phase 2.
    label_encoder = LabelEncoder()
    y_num = label_encoder.fit_transform(y)
    y_num = pd.Series(y_num, index=y.index)

    # If the caller gave a per-class SMOTE strategy by class NAME (e.g.
    # {"R2L": 15000}), translate it to the numeric labels we now use.
    if isinstance(smote_strategy, dict):
        smote_strategy = {
            int(label_encoder.transform([key])[0]): value
            for key, value in smote_strategy.items()
        }

    # SMOTE then classifier, as one scikit-learn-compatible pipeline.
    # GridSearchCV will cross-validate THIS pipeline, so SMOTE is re-fitted on
    # each fold's training portion only (no leakage, see module docstring).
    # k_neighbors=3 (not the default 5) so SMOTE still works when a class is
    # extremely rare and a CV fold's training portion has few of its samples.
    pipeline = ImbPipeline([
        ("smote", SMOTE(sampling_strategy=smote_strategy,
                        random_state=C.RANDOM_STATE, k_neighbors=3)),
        ("clf", estimator),
    ])

    # "clf__C" means: the C hyperparameter of the step named "clf".
    tuned_params = {f"clf__{k}": v for k, v in param_grid.items()}

    # Stratified k-fold: each fold mirrors the full data's class proportions.
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=C.RANDOM_STATE)

    grid = GridSearchCV(
        pipeline,
        tuned_params,
        cv=cv,
        scoring="f1_macro",       # class-balanced metric (see docstring)
        n_jobs=n_jobs,            # run folds in parallel
        verbose=verbose,
        refit=True,               # refit the winner on the WHOLE training set
    )

    start = time.perf_counter()
    grid.fit(X, y_num)
    fit_time = time.perf_counter() - start

    return {
        "model": grid.best_estimator_,          # SMOTE + best classifier, refitted
        "model_name": model_name,
        "best_params": {k[5:]: v for k, v in grid.best_params_.items()},  # strip "clf__"
        "cv_score_mean": grid.best_score_,       # mean f1_macro over the k folds
        "cv_score_std": float(grid.cv_results_["std_test_score"][grid.best_index_]),
        "fit_time_s": round(fit_time, 2),        # tuning + final refit
        "n_combinations": len(grid.cv_results_["params"]),
        "cv_folds": cv_folds,
    }


def measure_latency(model, X: pd.DataFrame, n_repeats: int = 5) -> float:
    """Measure inference speed: milliseconds per row.

    We predict on a fixed sample several times and divide by the number of
    rows.  This is the number that decides whether a model can run "live" on
    a busy network link (the complexity-vs-latency trade-off in the thesis).
    """
    sample = X.iloc[:5000]                       # fixed batch for fair timing
    # warm-up: first call includes lazy initialisation / JIT, don't measure it
    model.predict(sample)
    start = time.perf_counter()
    for _ in range(n_repeats):
        model.predict(sample)
    elapsed = (time.perf_counter() - start) / n_repeats
    return round(elapsed / len(sample) * 1000.0, 4)   # ms per row


def save_model(
    dataset: str,
    result: dict,
    extra_meta: dict | None = None,
    registry_dir: Path | None = None,
) -> Path:
    """Save a trained model (joblib) plus its metadata (JSON) to the registry.

    Files are named like  nslkdd_logistic.joblib  /  nslkdd_logistic_meta.json
    so the web API (Phase 5) can find models by dataset + algorithm name.
    """
    registry = registry_dir or C.MODELS_DIR
    registry.mkdir(parents=True, exist_ok=True)

    name = result["model_name"]
    model_path = registry / f"{dataset}_{name}.joblib"
    joblib.dump(result["model"], model_path)

    meta = {
        "dataset": dataset,
        "model": name,
        "best_params": result["best_params"],
        "cv_score_mean_f1_macro": round(result["cv_score_mean"], 4),
        "cv_score_std_f1_macro": round(result["cv_score_std"], 4),
        "fit_time_s": result["fit_time_s"],
        "n_hyperparameter_combinations": result["n_combinations"],
        "cv_folds": result["cv_folds"],
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if extra_meta:
        meta.update(extra_meta)
    meta_path = registry / f"{dataset}_{name}_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return model_path


def write_registry_metadata(registry: Path | None = None) -> Path:
    """Re-generate models_metadata.json from the *_meta.json files in the registry.

    The web API (Phase 5) reads this single file to populate /models, so we
    rebuild it after any retraining run instead of editing it by hand.
    """
    registry = registry or C.MODELS_DIR
    entries = []
    for meta_path in sorted(registry.glob("*_meta.json")):
        entries.append(json.loads(meta_path.read_text(encoding="utf-8")))
    out = registry / "models_metadata.json"
    out.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"Rebuilt {out} with {len(entries)} model entries.")
    return out


def retrain_all(n_jobs: int = 4, cv_folds: int = 5) -> None:
    """Retrain every model from scratch — the one-command reproducibility path.

    Run with:   python -m src.models.train

    What it does (mirrors notebooks 02 + 03 exactly):
      1. reload the RAW datasets (NSL-KDD both splits; CICIDS2017 capped);
      2. rebuild the pre-SMOTE preprocessed splits with a freshly fitted
         Preprocessor (same median imputation + min-max scaling + one-hot),
         and re-save the preprocessor + label encoder to data/processed;
      3. for every (dataset, algorithm) pair run GridSearchCV with stratified
         k-fold CV and SMOTE kept INSIDE the folds (no leakage);
      4. measure inference latency on the untouched test set;
      5. save the models + per-model metadata, then rebuild models_metadata.json.

    This takes roughly 30-45 minutes on a 16-core machine because tuning is
    heavy — which is why the notebooks are the day-to-day path and this command
    is the "prove it reproduces" path for the thesis.
    """
    from sklearn.model_selection import train_test_split

    from src.data import loader as L
    from src.data.preprocess import Preprocessor

    out = C.DATA_PROCESSED_DIR
    out.mkdir(parents=True, exist_ok=True)

    datasets: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # NSL-KDD: reload raw, refit the Preprocessor, keep SMOTE for the
    # tuner (step 3) so we store PRE-SMOTE splits here.
    # ------------------------------------------------------------------
    nsl_train = L.load_nsl_kdd("train")
    nsl_test = L.load_nsl_kdd("test")
    feature_cols = list(C.NSL_KDD_FEATURES)

    pp_nsl = Preprocessor(categorical_features=C.NSL_KDD_CATEGORICAL_FEATURES)
    Xtr_nsl = pp_nsl.fit_transform(nsl_train[feature_cols])
    ytr_nsl = nsl_train[C.CATEGORY_COL].reset_index(drop=True)
    Xte_nsl = pp_nsl.transform(nsl_test[feature_cols])
    yte_nsl = nsl_test[C.CATEGORY_COL].reset_index(drop=True)

    joblib.dump(pp_nsl, out / "nslkdd_preprocessor.joblib")
    joblib.dump(LabelEncoder().fit(ytr_nsl), out / "nslkdd_label_encoder.joblib")
    Xtr_nsl.to_pickle(out / "nslkdd_train_X.pkl")
    ytr_nsl.to_pickle(out / "nslkdd_train_y.pkl")
    Xte_nsl.to_pickle(out / "nslkdd_test_X.pkl")
    yte_nsl.to_pickle(out / "nslkdd_test_y.pkl")

    datasets["nslkdd"] = {
        "Xtr": Xtr_nsl,
        "Xte": Xte_nsl,
        "smote_strategy": SMOTE_STRATEGY["nslkdd"],
    }

    # ------------------------------------------------------------------
    # CICIDS2017: capped load (~62k rows), stratified 80/20 split.
    # ------------------------------------------------------------------
    cic = L.load_cicids2017_capped()
    cic_train, cic_test = train_test_split(
        cic, test_size=0.2,
        stratify=cic[C.CATEGORY_COL], random_state=C.RANDOM_STATE,
    )
    drop_cols = [C.TYPE_COL, C.CATEGORY_COL, C.IS_ATTACK_COL, C.SOURCE_COL]

    pp_cic = Preprocessor(categorical_features=[])
    Xtr_cic = pp_cic.fit_transform(cic_train.drop(columns=drop_cols))
    ytr_cic = cic_train[C.CATEGORY_COL].reset_index(drop=True)
    Xte_cic = pp_cic.transform(cic_test.drop(columns=drop_cols))
    yte_cic = cic_test[C.CATEGORY_COL].reset_index(drop=True)

    joblib.dump(pp_cic, out / "cicids_preprocessor.joblib")
    joblib.dump(LabelEncoder().fit(ytr_cic), out / "cicids_label_encoder.joblib")
    Xtr_cic.to_pickle(out / "cicids_train_X.pkl")
    ytr_cic.to_pickle(out / "cicids_train_y.pkl")
    Xte_cic.to_pickle(out / "cicids_test_X.pkl")
    yte_cic.to_pickle(out / "cicids_test_y.pkl")

    datasets["cicids"] = {
        "Xtr": Xtr_cic,
        "Xte": Xte_cic,
        "smote_strategy": SMOTE_STRATEGY["cicids"],
    }

    # ------------------------------------------------------------------
    # Train + tune every algorithm on every dataset, then measure latency.
    # ------------------------------------------------------------------
    for dataset, d in datasets.items():
        print(f"\n=== Tuning 4 models on {dataset.upper()} ===")
        for name in MODELS:
            result = tune_model(
                name, d["Xtr"], ytr_nsl if dataset == "nslkdd" else ytr_cic,
                smote_strategy=d["smote_strategy"],
                cv_folds=cv_folds, n_jobs=n_jobs, verbose=1,
            )
            result["latency_ms_per_row"] = measure_latency(result["model"], d["Xte"])
            save_model(dataset, result, extra_meta={
                "latency_ms_per_row": result["latency_ms_per_row"],
            })
            print(
                f"  {dataset}/{name}: cv f1_macro = {result['cv_score_mean']:.4f} "
                f"(latency {result['latency_ms_per_row']} ms/row)"
            )

    write_registry_metadata()
    print("\nRetraining complete. Models live in src/models/registry/.")


if __name__ == "__main__":
    # python -m src.models.train   -> retrain + re-tune everything from scratch
    retrain_all()
