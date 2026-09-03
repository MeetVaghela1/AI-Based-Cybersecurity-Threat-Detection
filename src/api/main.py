"""main.py — the FastAPI backend that serves predictions.

What an API is (beginner version):
  An API (Application Programming Interface) is a messenger.  Your website
  (frontend) asks the backend "what is this traffic?" by sending it a request,
  and the backend answers with a structured reply.  The two sides never share
  files or memory — they only exchange messages over HTTP.

What a REST endpoint is:
  An endpoint is a single URL + verb (GET / POST / ...) that performs one
  specific job.  Think of a waiter taking one specific order:
      GET    /models       -> "bring me the menu"          (read only)
      POST   /predict      -> "here is traffic, what is it?" (send data, get answer)
  GET asks for information; POST sends data to be processed and returns a result.

Why separate backend from frontend:
  The backend is Python + machine learning (slow to load, model files, science).
  The frontend is a website in the browser (fast to load, pretty charts).
  If they were one file, every page visit would re-load gigabytes of models and
  no one could update the design without touching the ML code.  Splitting them
  means: the backend is a stable service any client can call, and the frontend
  is just another client.

Run with:
    uvicorn src.api.main:app --reload --port 8000
then open http://127.0.0.1:8000/docs for the interactive documentation.
"""

from __future__ import annotations

import itertools
import json
import time
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.api.attack_info import get_attack_info, list_attack_types
from src.api.schemas import (
    PredictRequest,
    PredictResponse,
    Prediction,
    PredictionsResponse,
    SimulateRequest,
    SimulateResponse,
)
from src.utils import config as C

# ---------------------------------------------------------------------------
# The app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI-Based Cyber Threat Detection API",
    version="1.0.0",
    description=(
        "Backend for the AI-Based Cybersecurity Threat Detection project. "
        "Classifies a network connection (or a dataset row) as Normal or a "
        "specific attack using the models trained in Phase 3. "
        "All detections run on recorded dataset traffic / simulated input."
    ),
)

# Allow the browser-based frontend (running on a different port) to call us.
# In production this should be narrowed to the real frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATASETS = ("nslkdd", "cicids")
MODELS = ("logistic", "decision_tree", "random_forest", "xgboost")


# ---------------------------------------------------------------------------
# Lazy loading — models are big files, so load them only when first needed.
# ---------------------------------------------------------------------------
_ARTIFACT_CACHE: dict = {}
_TEST_CACHE: dict = {}


def _artifacts(dataset: str, model: str):
    """Return (preprocessor, label_encoder, model), loading them once."""
    key = (dataset, model)
    if key not in _ARTIFACT_CACHE:
        proc = C.DATA_PROCESSED_DIR
        pp = joblib.load(proc / f"{dataset}_preprocessor.joblib")
        le = joblib.load(proc / f"{dataset}_label_encoder.joblib")
        clf = joblib.load(C.MODELS_DIR / f"{dataset}_{model}.joblib")
        _ARTIFACT_CACHE[key] = (pp, le, clf)
    return _ARTIFACT_CACHE[key]


def _test_data(dataset: str):
    """Load the held-out test split for a dataset (once)."""
    if dataset not in _TEST_CACHE:
        proc = C.DATA_PROCESSED_DIR
        X = pd.read_pickle(proc / f"{dataset}_test_X.pkl")
        y = pd.read_pickle(proc / f"{dataset}_test_y.pkl").reset_index(drop=True)
        _TEST_CACHE[dataset] = (X, y)
    return _TEST_CACHE[dataset]


# ---------------------------------------------------------------------------
# Prediction log — a tiny server-side "database" of everything the live
# monitor has classified.  Kept in memory AND persisted to a JSON file so it
# survives restarts (demo-friendly, no external DB engine needed).
# ---------------------------------------------------------------------------
PREDICTION_LOG_MAX = 200
_LOG_SEQ = itertools.count(1)
_PREDICTION_LOG: list[dict] = []


def _log_path():
    return C.DATA_PROCESSED_DIR / "prediction_log.json"


def _load_prediction_log() -> None:
    global _PREDICTION_LOG
    try:
        if _log_path().exists():
            data = json.loads(_log_path().read_text(encoding="utf-8"))
            if isinstance(data, list):
                _PREDICTION_LOG = data
    except Exception:
        _PREDICTION_LOG = []


def _record_prediction(item: Prediction) -> None:
    """Append one classified flow to the in-memory log (newest at the end)."""
    global _PREDICTION_LOG
    _PREDICTION_LOG.append({
        "seq": next(_LOG_SEQ),
        "time": datetime.now().strftime("%H:%M:%S"),
        "dataset": item.dataset,
        "model": item.model,
        "prediction": item.prediction,
        "is_attack": item.is_attack,
        "confidence": item.confidence,
        "latency_ms": item.latency_ms,
        "true_label": item.true_label,
        "matched": item.matched,
    })
    if len(_PREDICTION_LOG) > PREDICTION_LOG_MAX:
        _PREDICTION_LOG = _PREDICTION_LOG[-PREDICTION_LOG_MAX:]


def _save_prediction_log() -> None:
    """Persist the log to disk so it survives a server restart."""
    try:
        _log_path().write_text(
            json.dumps(_PREDICTION_LOG, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def _raw_feature_names(dataset: str) -> list[str]:
    """The raw feature column names a request must provide for 'features' mode.

    NSL-KDD's 41 names are fixed in config.  CICIDS2017 has no categorical
    features, so its raw names are the numeric columns the fitted preprocessor
    learned (in the exact order training used).
    """
    if dataset == "nslkdd":
        return list(C.NSL_KDD_FEATURES)
    pp = _artifacts(dataset, "logistic")[0]
    return list(pp.numeric_features_)


def _row_from_features(dataset: str, pp, features: dict) -> pd.DataFrame:
    """Turn a raw feature dict into one correctly-shaped, preprocessed row."""
    names = _raw_feature_names(dataset)
    missing = [c for c in names if c not in features]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing feature(s) for {dataset}: {', '.join(missing[:10])}",
        )
    raw = pd.DataFrame([{c: features[c] for c in names}], columns=names)
    return pp.transform(raw)          # inf -> nan -> median -> scale -> one-hot


def _predict(dataset: str, model: str,
             features: dict | None = None,
             row_id: int | None = None) -> Prediction:
    """Classify one connection and package the full answer."""
    pp, le, clf = _artifacts(dataset, model)

    if row_id is not None:
        X_test, y_test = _test_data(dataset)
        if not (0 <= row_id < len(X_test)):
            raise HTTPException(
                status_code=400,
                detail=f"row_id must be between 0 and {len(X_test) - 1}.",
            )
        X = X_test.iloc[[row_id]]
        true_label = str(y_test.iloc[row_id])
    else:
        X = _row_from_features(dataset, pp, features)
        true_label = None

    t0 = time.perf_counter()
    proba = clf.predict_proba(X)[0]           # one probability per class
    pred_index = int(np.argmax(proba))
    latency_ms = (time.perf_counter() - t0) * 1000.0

    classes = list(le.classes_)               # class order the model uses
    prediction = le.inverse_transform([pred_index])[0]

    return Prediction(
        dataset=dataset,
        model=model,
        prediction=prediction,
        is_attack=prediction != C.NORMAL_CATEGORY,
        confidence=round(float(proba[pred_index]), 4),
        probabilities={c: round(float(p), 4) for c, p in zip(classes, proba)},
        true_label=true_label,
        matched=(true_label == prediction) if true_label is not None else None,
        latency_ms=round(latency_ms, 4),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/models")
def list_models():
    """All trained models with their test-set metrics (for the UI dropdown)."""
    eval_path = C.DATA_PROCESSED_DIR / "evaluation_results.json"
    if not eval_path.exists():
        raise HTTPException(status_code=503,
                            detail="Evaluation results not found — run Phase 4 first.")
    data = json.loads(eval_path.read_text(encoding="utf-8"))
    entries = []
    for ds, results in data.items():
        for r in results:
            entries.append({
                "dataset": ds,
                "model": r["model"],
                "model_label": r["model_label"],
                "accuracy": r["accuracy"],
                "precision_macro": r["precision_macro"],
                "recall_macro": r["recall_macro"],
                "f1_macro": r["f1_macro"],
                "auc_roc_macro": r["auc_roc_macro"],
                "latency_ms_per_row": r["test_latency_ms_per_row"],
                "classes": r["classes"],
            })
    return {"models": entries}


@app.get("/compare")
def compare():
    """The full comparison data — feeds the frontend's chart page."""
    eval_path = C.DATA_PROCESSED_DIR / "evaluation_results.json"
    if not eval_path.exists():
        raise HTTPException(status_code=503,
                            detail="Evaluation results not found — run Phase 4 first.")
    return json.loads(eval_path.read_text(encoding="utf-8"))


@app.get("/tuning-impact")
def tuning_impact():
    """Baseline (default hyperparameters) vs tuned (grid-searched) metrics.

    Produced by the Part 2 light-training script; used by the frontend to show
    how much hyperparameter tuning actually moved each model's test scores.
    """
    path = C.DATA_PROCESSED_DIR / "tuning_impact.json"
    if not path.exists():
        raise HTTPException(status_code=503,
                            detail="Tuning-impact data not found — run the Part 2 "
                                   "baseline-vs-tuned script first.")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/progression")
def progression():
    """The A->E development-progression for Logistic Regression.

    Raw -> preprocessed -> feature-selected -> SMOTE -> tuned, all scored on
    the same held-out test set. Shows which pipeline step matters most.
    """
    path = C.DATA_PROCESSED_DIR / "development_progression.json"
    if not path.exists():
        raise HTTPException(status_code=503,
                            detail="Development-progression data not found — run "
                                   "the Part 2 progression script first.")
    return json.loads(path.read_text(encoding="utf-8"))


# Matches the LogisticRegression(max_iter=...) constant in src/models/train.py.
LOGISTIC_MAX_ITER = 2000


def _saved_configs() -> dict:
    """The actual hyperparameter each saved model uses, per dataset.

    XGBoost -> boosting rounds (n_estimators), Random Forest -> tree count,
    Decision Tree -> max_depth (null = unlimited), Logistic Regression ->
    max_iter.  Used by the frontend to draw a "saved model" reference line on
    each training curve.
    """
    meta_path = C.MODELS_DIR / "models_metadata.json"
    if not meta_path.exists():
        raise HTTPException(status_code=503,
                            detail="models_metadata.json not found — train the "
                                   "models first.")
    out = {d: {} for d in DATASETS}
    for m in json.loads(meta_path.read_text(encoding="utf-8")):
        ds, name = m.get("dataset"), m.get("model")
        bp = m.get("best_params", {})
        if name == "xgboost":
            out[ds][name] = {"rounds": bp.get("n_estimators", 100)}
        elif name == "random_forest":
            out[ds][name] = {"trees": bp.get("n_estimators", 100)}
        elif name == "decision_tree":
            out[ds][name] = {"max_depth": bp.get("max_depth")}
        elif name == "logistic":
            out[ds][name] = {"max_iter": LOGISTIC_MAX_ITER}
    return out


@app.get("/training-curves")
def training_curves():
    """The raw Phase 3 convergence curves plus the saved model configs.

    Returns {"curves": {...training_curves.json}, "saved": {...}} so the
    frontend can render the curves as interactive charts (instead of the old
    static PNGs) with a reference line at the configuration actually used.
    """
    path = C.DATA_PROCESSED_DIR / "training_curves.json"
    if not path.exists():
        raise HTTPException(status_code=503,
                            detail="training_curves.json not found — run the "
                                   "Phase 3 curve script first.")
    return {
        "curves": json.loads(path.read_text(encoding="utf-8")),
        "saved": _saved_configs(),
    }


@app.get("/attack-info/{attack_type}")
def attack_info(attack_type: str):
    """Plain-language explanation of an attack type (for the UI)."""
    info = get_attack_info(attack_type)
    if info is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown attack type '{attack_type}'. "
                   f"Known types: {', '.join(list_attack_types())}",
        )
    return info


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    """Classify one connection: either raw features or a test-set row id."""
    if req.features is None and req.row_id is None:
        raise HTTPException(status_code=400,
                            detail="Provide either 'features' or 'row_id'.")
    if req.features is not None and req.row_id is not None:
        raise HTTPException(status_code=400,
                            detail="Provide only one of 'features' or 'row_id'.")
    return _predict(req.dataset, req.model, req.features, req.row_id)


@app.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest):
    """Replay random test-set rows so the frontend can animate 'live' traffic.

    IMPORTANT: this replays RECORDED dataset traffic.  It is a simulation for
    demonstration, not live network capture and not an attack tool.
    """
    X_test, y_test = _test_data(req.dataset)
    n = min(req.count, len(X_test))
    rng = np.random.default_rng()               # fresh randomness every call
    indices = rng.choice(len(X_test), size=n, replace=False)

    items = [_predict(req.dataset, req.model, row_id=int(i)) for i in indices]

    # Store everything this batch classified in the server-side log.
    for it in items:
        _record_prediction(it)
    _save_prediction_log()

    return SimulateResponse(dataset=req.dataset, model=req.model, items=items)


@app.get("/predictions", response_model=PredictionsResponse)
def predictions():
    """The stored prediction log (newest first).

    Every flow the live monitor classified ends up here, kept in a small
    JSON "database" on the server (max {PREDICTION_LOG_MAX} entries).
    """
    return {
        "count": len(_PREDICTION_LOG),
        "items": list(reversed(_PREDICTION_LOG)),
    }


# ---------------------------------------------------------------------------
# Serve the built React frontend (Phase 6) — optional convenience.
# After `cd frontend && npm run build`, uvicorn serves both the API and the
# website from one origin:  uvicorn src.api.main:app  ->  http://127.0.0.1:8000
# The mount is registered AFTER all API routes, so /models, /predict, etc.
# still win over static files.
# ---------------------------------------------------------------------------
_load_prediction_log()   # restore the persisted prediction log (if any)

FRONTEND_DIST = C.ROOT_DIR / "frontend" / "dist"
if FRONTEND_DIST.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:
    # No built frontend yet — give the browser a small JSON index instead.
    @app.get("/")
    def root():
        return {
            "service": "AI-Based Cyber Threat Detection API",
            "note": "Frontend not built yet. Run: cd frontend && npm install && npm run build",
            "datasets": list(DATASETS),
            "models": list(MODELS),
            "docs": "/docs",
        }
