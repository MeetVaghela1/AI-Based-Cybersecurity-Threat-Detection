"""schemas.py — the shapes of data the API accepts and returns.

FastAPI uses these Pydantic models to validate requests and to describe the
response format (this is what generates the interactive /docs page).  If a
request does not match the declared shape, the API replies with a clear
validation error before any model is touched.
"""

from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel, Field

# The only valid values (FastAPI rejects anything else at the door).
DatasetName = Literal["nslkdd", "cicids"]
ModelName = Literal["logistic", "decision_tree", "random_forest", "xgboost"]


class PredictRequest(BaseModel):
    """What the client sends to POST /predict.

    Two input modes (exactly one should be provided):
      * features — raw, human-readable features of ONE connection
                    (e.g. {"duration": 0, "protocol_type": "tcp", ...});
                    the server pre-processes them exactly like training data.
      * row_id   — index of a row in the dataset's test set; lets the UI
                    classify real dataset rows without copying features.
    """
    dataset: DatasetName
    model: ModelName
    features: Optional[dict[str, Union[float, int, str]]] = None
    row_id: Optional[int] = None


class SimulateRequest(BaseModel):
    """Request for POST /simulate — replay test-set rows as 'live' traffic."""
    dataset: DatasetName
    model: ModelName
    count: int = Field(default=20, ge=1, le=200,
                       description="how many test rows to replay")


class Prediction(BaseModel):
    """The full answer for a single connection."""
    dataset: str
    model: str
    prediction: str                      # predicted attack category (e.g. "DoS")
    is_attack: bool                      # True unless predicted "Normal"
    confidence: float                    # probability of the predicted class
    probabilities: dict[str, float]      # probability of EVERY class
    true_label: Optional[str] = None     # present when a row_id was used
    matched: Optional[bool] = None       # did the model get it right? (row_id mode)
    latency_ms: float                    # time the model took to answer


class PredictResponse(Prediction):
    pass


class SimulateResponse(BaseModel):
    dataset: str
    model: str
    simulated_replay: bool = Field(
        default=True,
        description="True = this is a replay of recorded dataset traffic, "
                    "NOT a live attack.",
    )
    items: list[Prediction]


class LogEntry(BaseModel):
    """One stored prediction in the server-side log ("database")."""
    seq: int
    time: str
    dataset: str
    model: str
    prediction: str
    is_attack: bool
    confidence: float
    latency_ms: Optional[float] = None
    true_label: Optional[str] = None
    matched: Optional[bool] = None


class PredictionsResponse(BaseModel):
    count: int
    items: list[LogEntry]
