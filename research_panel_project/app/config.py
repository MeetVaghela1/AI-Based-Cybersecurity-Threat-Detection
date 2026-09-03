"""config.py — paths and constants for the research panel project."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]            # research_panel_project/
ARTIFACT_DIR = ROOT / "artifacts"
MODELS_DIR = ARTIFACT_DIR / "models"
ENCODERS_DIR = ARTIFACT_DIR / "encoders"
PREPROCESSOR_DIR = ARTIFACT_DIR / "preprocessors"
TEST_DATA_DIR = ARTIFACT_DIR / "test_data"
DB_DIR = ROOT / "db"
DB_PATH = DB_DIR / "research_panel.db"
STATIC_DIR = ROOT / "static"

PARENT_PROJECT = ROOT.parent                          # the main project folder
PARENT_MODELS_REGISTRY = PARENT_PROJECT / "src" / "models" / "registry"
PARENT_PROCESSED = PARENT_PROJECT / "data" / "processed"

# Which model / dataset files exist, so the setup script and the detector
# agree on the canonical names.
DATASETS = ["nslkdd", "cicids"]
MODELS = ["logistic", "decision_tree", "random_forest", "xgboost"]
MODEL_LABELS = {
    "logistic": "Logistic Regression",
    "decision_tree": "Decision Tree",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
}
NORMAL_CLASSES = {
    "nslkdd": "Normal",
    "cicids": "Normal",
}
RANDOM_STATE = 42
