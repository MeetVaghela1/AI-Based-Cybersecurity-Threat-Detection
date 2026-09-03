"""tests/test_api.py — smoke tests for the FastAPI backend (Phase 5).

These tests hit every endpoint through FastAPI's in-process TestClient (no
server needs to be running).  They require the Phase 3 models and Phase 4
evaluation results to exist (they do — both phases have been run).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Read-only endpoints
# ---------------------------------------------------------------------------
def test_root_is_service_or_frontend():
    r = client.get("/")
    assert r.status_code == 200
    if "application/json" in r.headers.get("content-type", ""):
        # Frontend not built -> the API's JSON index is shown.
        assert r.json()["service"] == "AI-Based Cyber Threat Detection API"
    else:
        # Frontend built and served by FastAPI -> the SPA shell is shown.
        assert "root" in r.text


def test_list_models_has_all_eight():
    r = client.get("/models")
    assert r.status_code == 200
    models = r.json()["models"]
    keys = {(m["dataset"], m["model"]) for m in models}
    expected = {
        (ds, md)
        for ds in ("nslkdd", "cicids")
        for md in ("logistic", "decision_tree", "random_forest", "xgboost")
    }
    assert keys == expected
    assert all("f1_macro" in m and "auc_roc_macro" in m for m in models)


def test_compare_has_both_datasets():
    r = client.get("/compare")
    assert r.status_code == 200
    assert set(r.json().keys()) == {"nslkdd", "cicids"}
    for ds in r.json().values():
        assert len(ds) == 4                      # four models per dataset
        assert "per_class" in ds[0]


# ---------------------------------------------------------------------------
# Attack-info endpoint
# ---------------------------------------------------------------------------
def test_attack_info_known_type():
    r = client.get("/attack-info/DoS")
    assert r.status_code == 200
    info = r.json()
    assert info["category"] == "DoS"
    assert all(k in info for k in
               ("description", "how_it_works", "indicators", "impact", "defense"))


def test_attack_info_case_insensitive():
    assert client.get("/attack-info/ddos").status_code == 200
    assert client.get("/attack-info/PortScan").status_code == 200


def test_attack_info_unknown_type_404():
    r = client.get("/attack-info/not-a-real-attack")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Training-curves endpoint
# ---------------------------------------------------------------------------
def test_training_curves_has_curves_and_saved_configs():
    r = client.get("/training-curves")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"curves", "saved"}
    assert set(body["curves"].keys()) == {"nslkdd", "cicids"}
    # Every dataset has all four curve families.
    for ds in ("nslkdd", "cicids"):
        assert set(body["curves"][ds].keys()) == {
            "xgb_loss", "rf_error", "dt_depth", "lr_convergence"
        }
        assert len(body["curves"][ds]["xgb_loss"]["round"]) > 50
        assert len(body["curves"][ds]["rf_error"]["trees"]) >= 10
    # Saved-model reference configs exist for every (dataset, model) pair.
    for ds in ("nslkdd", "cicids"):
        s = body["saved"][ds]
        assert set(s.keys()) == {"logistic", "decision_tree", "random_forest", "xgboost"}
        assert s["xgboost"]["rounds"] > 0
        assert s["random_forest"]["trees"] > 0
        assert s["logistic"]["max_iter"] >= 1000


# ---------------------------------------------------------------------------
# Prediction endpoint
# ---------------------------------------------------------------------------
def test_predict_nslkdd_row_id():
    r = client.post("/predict", json={
        "dataset": "nslkdd", "model": "xgboost", "row_id": 0,
    })
    assert r.status_code == 200
    p = r.json()
    assert p["prediction"] in ("Normal", "DoS", "Probe", "R2L", "U2R")
    assert isinstance(p["is_attack"], bool)
    assert 0.0 <= p["confidence"] <= 1.0
    assert len(p["probabilities"]) == 5
    assert p["true_label"] is not None and p["matched"] is not None


def test_predict_cicids_row_id():
    r = client.post("/predict", json={
        "dataset": "cicids", "model": "xgboost", "row_id": 5,
    })
    assert r.status_code == 200
    p = r.json()
    assert len(p["probabilities"]) == 9
    assert p["matched"] is True                     # XGBoost is near-perfect


def test_predict_nslkdd_features():
    from src.data import loader as L
    from src.utils import config as C

    row = L.load_nsl_kdd("train").iloc[0][list(C.NSL_KDD_FEATURES)].to_dict()
    r = client.post("/predict", json={
        "dataset": "nslkdd", "model": "random_forest", "features": row,
    })
    assert r.status_code == 200
    assert r.json()["prediction"] in ("Normal", "DoS", "Probe", "R2L", "U2R")


def test_predict_requires_an_input():
    r = client.post("/predict", json={"dataset": "nslkdd", "model": "xgboost"})
    assert r.status_code == 400


def test_predict_rejects_both_inputs():
    r = client.post("/predict", json={
        "dataset": "nslkdd", "model": "xgboost",
        "row_id": 0, "features": {"duration": 0},
    })
    assert r.status_code == 400


def test_predict_rejects_bad_dataset():
    r = client.post("/predict", json={
        "dataset": "banana", "model": "xgboost", "row_id": 0,
    })
    assert r.status_code == 422                     # Pydantic validation


def test_predict_out_of_range_row():
    r = client.post("/predict", json={
        "dataset": "nslkdd", "model": "xgboost", "row_id": 999999999,
    })
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Simulation endpoint
# ---------------------------------------------------------------------------
def test_simulate_replays_rows():
    r = client.post("/simulate", json={
        "dataset": "nslkdd", "model": "xgboost", "count": 10,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["simulated_replay"] is True
    assert len(body["items"]) == 10
    assert all(i["true_label"] is not None for i in body["items"])


# ---------------------------------------------------------------------------
# Prediction-log endpoint (the stored "database" of classified flows)
# ---------------------------------------------------------------------------
def test_predictions_log_records_simulated_rows():
    client.post("/simulate", json={
        "dataset": "cicids", "model": "decision_tree", "count": 4,
    })
    r = client.get("/predictions")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 4
    assert len(body["items"]) == body["count"]
    newest = body["items"][0]                    # newest first
    assert {"seq", "time", "dataset", "model", "prediction", "is_attack",
            "confidence", "true_label", "matched"} <= set(newest.keys())
    assert newest["dataset"] == "cicids"
    assert newest["model"] == "decision_tree"
    assert newest["is_attack"] in (True, False)
    assert 0.0 <= newest["confidence"] <= 1.0
    assert newest["latency_ms"] is not None and newest["latency_ms"] >= 0.0
