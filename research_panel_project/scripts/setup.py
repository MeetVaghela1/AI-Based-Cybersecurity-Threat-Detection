"""setup.py — one-time setup for the research panel project.

Copies the trained models, label encoders, test sets and the JSON artifacts
from the MAIN project into this folder (artifacts/), then creates and seeds
the SQLite database.

Run from the research_panel_project folder:
    python scripts/setup.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config, db, seeder


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        print(f"  MISSING (skipped): {src}")
        return
    shutil.copy2(src, dst)
    print(f"  copied {src.name} -> {dst}")


def main() -> None:
    print("Research panel project — setup")
    print("-------------------------------")

    # 1. trained models
    print("[1/7] Models")
    for dataset in config.DATASETS:
        for model in config.MODELS:
            _copy(
                config.PARENT_MODELS_REGISTRY / f"{dataset}_{model}.joblib",
                config.MODELS_DIR / f"{dataset}_{model}.joblib",
            )

    # 2. label encoders
    print("[2/7] Label encoders")
    for dataset in config.DATASETS:
        _copy(
            config.PARENT_PROCESSED / f"{dataset}_label_encoder.joblib",
            config.ENCODERS_DIR / f"{dataset}_label_encoder.joblib",
        )

    # 3. preprocessors (needed by the step-by-step trace to show a real
    #    preprocessing pass with measured timing)
    print("[3/7] Preprocessors")
    for dataset in config.DATASETS:
        _copy(
            config.PARENT_PROCESSED / f"{dataset}_preprocessor.joblib",
            config.PREPROCESSOR_DIR / f"{dataset}_preprocessor.joblib",
        )

    # 4. test sets
    print("[4/7] Test sets (real rows the models were never trained on)")
    for dataset in config.DATASETS:
        for suffix in ("test_X", "test_y"):
            _copy(
                config.PARENT_PROCESSED / f"{dataset}_{suffix}.pkl",
                config.TEST_DATA_DIR / f"{dataset}_{suffix}.pkl",
            )

    # 5. JSON artifacts (the source of every number in the database)
    print("[5/7] JSON artifacts")
    _copy(
        config.PARENT_MODELS_REGISTRY / "models_metadata.json",
        config.ARTIFACT_DIR / "models_metadata.json",
    )
    _copy(
        config.PARENT_PROCESSED / "evaluation_results.json",
        config.ARTIFACT_DIR / "evaluation_results.json",
    )

    # 6. create + seed the database
    print("[6/7] Database")
    db.init_db()
    try:
        if seeder.seed_if_empty():
            print(f"  seeded {config.DB_PATH}")
        else:
            print(f"  already seeded: {config.DB_PATH}")
    except FileNotFoundError as exc:
        print(f"  WARNING: {exc}")
        print("  The panel will start, but the DB will be empty until the")
        print("  artifacts are present.")

    # 7. sanity check
    print("[7/7] Check")
    missing = [
        f"{d}_{m}" for d in config.DATASETS for m in config.MODELS
        if not (config.MODELS_DIR / f"{d}_{m}.joblib").exists()
    ]
    if missing:
        print("  Models NOT found (check the main project path):")
        for name in missing:
            print(f"    - {name}")
    else:
        print("  All 8 models present.")

    print("\nDone. Start the panel with:  python run.py   (http://127.0.0.1:8100)")


if __name__ == "__main__":
    main()
