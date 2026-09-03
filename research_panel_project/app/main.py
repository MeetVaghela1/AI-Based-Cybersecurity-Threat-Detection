"""main.py — FastAPI app for the research panel project.

The API is DB-backed: every endpoint reads from the SQLite database, and every
live detection (POST /api/predict) is written into the `predictions` table
before it is returned to the panel.

Run:  python run.py            (http://127.0.0.1:8100)
      python -m uvicorn app.main:app --port 8100
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, db, seeder
from .detector import Detector

app = FastAPI(
    title="Research Panel — AI-Based Cybersecurity Threat Detection",
    description="DB-backed presentation of the trained models, evaluation "
                "results and live detections. All data is read from (and "
                "logged to) the SQLite database.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

detector = Detector()


@app.on_event("startup")
def bootstrap() -> None:
    db.init_db()
    try:
        if seeder.seed_if_empty():
            print("[panel] Database seeded from real artifacts.")
    except FileNotFoundError as exc:
        print(f"[panel] WARNING: {exc}")


# ---------------------------------------------------------------------------
# request/response models
# ---------------------------------------------------------------------------

class PredictRequest(BaseModel):
    dataset: str = Field(..., description="nslkdd | cicids")
    model: str = Field(..., description="logistic | decision_tree | random_forest | xgboost")
    count: int = Field(10, ge=1, le=100)
    random_state: int | None = Field(None, description="optional seed for reproducible picks")


class CustomPredictRequest(BaseModel):
    dataset: str = Field(..., description="nslkdd | cicids")
    model: str = Field(..., description="logistic | decision_tree | random_forest | xgboost")
    features: dict[str, float] = Field(
        ..., description="feature name -> value for the features the user set"
    )


class TracePredictRequest(BaseModel):
    dataset: str = Field(..., description="nslkdd | cicids")
    model: str = Field(..., description="logistic | decision_tree | random_forest | xgboost")
    row_index: int | None = Field(None, description="optional specific test row")
    random_state: int | None = Field(None, description="optional seed for reproducible random picks")


# ---------------------------------------------------------------------------
# read-only endpoints (all backed by the database)
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "db": str(config.DB_PATH)}


@app.get("/api/overview")
def overview() -> dict:
    """Headline numbers straight from the database."""
    with db.get_conn() as conn:
        n_models = conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
        n_datasets = conn.execute("SELECT COUNT(*) FROM datasets").fetchone()[0]
        n_preds = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        n_attacks = conn.execute(
            "SELECT COUNT(*) FROM predictions WHERE is_attack = 1"
        ).fetchone()[0]
        n_matched = conn.execute(
            "SELECT COUNT(*) FROM predictions WHERE matched = 1"
        ).fetchone()[0]
        last = conn.execute(
            "SELECT timestamp FROM predictions ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return {
        "models": n_models,
        "datasets": n_datasets,
        "predictions_logged": n_preds,
        "attacks_logged": n_attacks,
        "matches_logged": n_matched,
        "last_prediction": last["timestamp"] if last else None,
        "db_file": config.DB_PATH.name,
    }


@app.get("/api/datasets")
def datasets() -> list[dict]:
    with db.get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM datasets ORDER BY year"
        )]


@app.get("/api/models")
def models(dataset: str | None = Query(None)) -> list[dict]:
    with db.get_conn() as conn:
        if dataset:
            rows = conn.execute(
                "SELECT * FROM models WHERE dataset = ? ORDER BY dataset, model_name",
                (dataset,),
            )
        else:
            rows = conn.execute("SELECT * FROM models ORDER BY dataset, model_name")
        return [dict(r) for r in rows]


@app.get("/api/test_metrics")
def test_metrics(dataset: str | None = Query(None)) -> list[dict]:
    with db.get_conn() as conn:
        if dataset:
            rows = conn.execute(
                "SELECT * FROM test_metrics WHERE dataset = ? ORDER BY dataset, model_name",
                (dataset,),
            )
        else:
            rows = conn.execute("SELECT * FROM test_metrics ORDER BY dataset, model_name")
        return [dict(r) for r in rows]


@app.get("/api/per_class")
def per_class(dataset: str, model: str) -> list[dict]:
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM per_class_metrics WHERE dataset = ? AND model_name = ?",
            (dataset, model),
        )
        return [dict(r) for r in rows]


@app.get("/api/predictions")
def predictions(limit: int = Query(50, ge=1, le=500)) -> list[dict]:
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM predictions ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in rows]


@app.get("/api/pipeline")
def pipeline() -> list[dict]:
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT phase, title, detail FROM pipeline_steps ORDER BY ord"
        )
        return [dict(r) for r in rows]


@app.get("/api/db_info")
def db_info() -> list[dict]:
    """Every table, its columns and its row count — the 'under the hood' view."""
    return db.table_counts()


# ---------------------------------------------------------------------------
# model-backed endpoints
# ---------------------------------------------------------------------------

@app.get("/api/row_features")
def row_features(dataset: str, row_index: int, top_n: int = Query(12, ge=1, le=30)):
    try:
        return detector.row_features(dataset, row_index, top_n)
    except (IndexError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/feature_input")
def feature_input(dataset: str, model: str, n: int = Query(10, ge=3, le=30)):
    """The most important features to fill in for user-defined input,
    with real per-column stats (mean/std/min/max) from the test data."""
    try:
        return detector.feature_stats(dataset, model, n)
    except (ValueError, IndexError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/predict_custom")
def predict_custom(req: CustomPredictRequest) -> dict:
    """Classify a user-supplied feature vector (remaining features are set to
    the dataset mean), LOG the detection to the database, and return it."""
    try:
        items = detector.predict_custom(req.dataset, req.model, req.features)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    log_rows = [
        {
            "timestamp": it["timestamp"],
            "dataset": it["dataset"],
            "model_name": it["model_name"],
            "source": it["source"],
            "row_index": it["row_index"],
            "predicted_label": it["predicted_label"],
            "true_label": it["true_label"],
            "is_attack": it["is_attack"],
            "confidence": it["confidence"],
            "matched": it["matched"],
            "latency_ms": it["latency_ms"],
        }
        for it in items
    ]
    inserted = db.insert_predictions(log_rows)

    return {
        "inserted_into_db": inserted,
        "table": "predictions",
        "count": len(items),
        "items": items,
    }


@app.post("/api/trace_predict")
def trace_predict(req: TracePredictRequest) -> dict:
    """Run ONE real test row through the whole pipeline step by step, with the
    actual timing of each stage measured live (time.perf_counter). The
    detection is logged to the database like every other one."""
    try:
        trace = detector.trace_predict(
            req.dataset, req.model, row_index=req.row_index, random_state=req.random_state
        )
    except (ValueError, IndexError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    inserted = db.insert_predictions([
        {
            "timestamp": trace["timestamp"],
            "dataset": trace["dataset"],
            "model_name": trace["model"],
            "source": trace["source"],
            "row_index": trace["row_index"],
            "predicted_label": trace["predicted_label"],
            "true_label": trace["true_label"],
            "is_attack": trace["is_attack"],
            "confidence": trace["confidence"],
            "matched": trace["matched"],
            "latency_ms": trace["timings"]["latency_ms"],
        }
    ])
    return {**trace, "inserted_into_db": inserted}


@app.post("/api/predict")
def predict(req: PredictRequest) -> dict:
    """Classify random test-set rows, LOG every detection to the database,
    and return both the detections and their database ids."""
    try:
        items = detector.predict(
            req.dataset, req.model, count=req.count, random_state=req.random_state
        )
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    log_rows = [
        {
            "timestamp": it["timestamp"],
            "dataset": it["dataset"],
            "model_name": it["model_name"],
            "source": it["source"],
            "row_index": it["row_index"],
            "predicted_label": it["predicted_label"],
            "true_label": it["true_label"],
            "is_attack": it["is_attack"],
            "confidence": it["confidence"],
            "matched": it["matched"],
            "latency_ms": it["latency_ms"],
        }
        for it in items
    ]
    inserted = db.insert_predictions(log_rows)

    return {
        "inserted_into_db": inserted,
        "table": "predictions",
        "count": len(items),
        "items": items,
    }


# ---------------------------------------------------------------------------
# the panel UI (mounted last so the /api routes win)
# ---------------------------------------------------------------------------

if config.STATIC_DIR.exists():
    app.mount(
        "/", StaticFiles(directory=config.STATIC_DIR, html=True), name="panel-ui"
    )
