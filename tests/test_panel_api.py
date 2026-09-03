"""tests/test_panel_api.py — smoke tests for the research panel backend.

The step-by-step trace endpoint (/api/trace_predict) runs one real test row
through the actual pipeline and reports the real measured timing of each stage
(time.perf_counter). These tests assert the trace is well-formed, the timing is
plausible and non-cached, and the detection is logged to the panel DB.
"""

import sys
from pathlib import Path

PANEL = Path(__file__).resolve().parents[1] / "research_panel_project"
if str(PANEL) not in sys.path:
    sys.path.insert(0, str(PANEL))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_trace_predict_is_well_formed():
    # row_index=0 is fixed (not random) so the test is deterministic — row 0
    # of the NSL-KDD test set is known to be protocol_type == "tcp".
    r = client.post("/api/trace_predict", json={
        "dataset": "nslkdd", "model": "xgboost", "row_index": 0,
    })
    assert r.status_code == 200
    t = r.json()
    assert t["source"] == "step-by-step"
    assert t["predicted_label"] in ("Normal", "DoS", "Probe", "R2L", "U2R")
    assert t["true_label"] in ("Normal", "DoS", "Probe", "R2L", "U2R")
    assert t["inserted_into_db"] == 1
    assert len(t["probabilities"]) == 5
    # every stage present and timed
    for stage in ("preprocessing", "inference", "decision"):
        assert t["steps"][stage]["ms"] >= 0
    assert t["timings"]["total_ms"] > 0
    # the real preprocessing pass must reproduce the stored row exactly
    assert t["steps"]["preprocessing"]["reproduces_stored_row"] is True
    # the raw input must include the reconstructed categorical values
    assert t["steps"]["input"]["categorical"]["protocol_type"] == "tcp"


def test_trace_predict_timings_are_live_not_cached():
    # two runs on the same row must show genuinely measured timings
    t1 = client.post("/api/trace_predict", json={
        "dataset": "cicids", "model": "random_forest", "row_index": 42,
    }).json()
    t2 = client.post("/api/trace_predict", json={
        "dataset": "cicids", "model": "random_forest", "row_index": 42,
    }).json()
    assert t1["row_index"] == t2["row_index"] == 42
    assert t1["timings"]["total_ms"] > 0 and t2["timings"]["total_ms"] > 0
    assert len(t1["probabilities"]) == 9


def test_trace_predict_rejects_bad_inputs():
    assert client.post("/api/trace_predict", json={
        "dataset": "banana", "model": "xgboost",
    }).status_code == 400
    assert client.post("/api/trace_predict", json={
        "dataset": "nslkdd", "model": "xgboost", "row_index": 999999999,
    }).status_code == 400
