# Research Panel Project — AI-Based Cybersecurity Threat Detection

A companion to the main project, built for the **research panel presentation**.
It keeps the same trained models and results but adds a **real SQLite database**
that records everything that happens "under the hood": the datasets, the trained
models, their evaluation metrics, the pipeline steps, and — most importantly —
**every live detection is written to the database** and can be inspected.

The goal is transparency: a panel member can see the exact numbers, the exact
database rows, and the exact flow from dataset to detection — with nothing
hidden behind a polished dashboard.

---

## 1. What this project is (and is not)

| | |
|---|---|
| **It is** | a lightweight, DB-backed research presentation of the models and results produced by the main project (`src/models`, notebooks 01–04) |
| **It is not** | a re-training of the models, and it does not duplicate the demo dashboard — the main project keeps doing that |

The model files and evaluation results are **copied from the main project** by
`scripts/setup.py`, so the panel project is self-contained and can be zipped and
run on any machine without the parent folder.

## 2. Folder structure

```
research_panel_project/
├── requirements.txt        Python dependencies
├── README.md               this file
├── run.py                  starts the server (python run.py)
├── scripts/
│   └── setup.py            copies models/data from the main project, seeds DB
├── app/
│   ├── config.py           paths and constants
│   ├── db.py               SQLite schema + helpers
│   ├── seeder.py           fills the database from real artifacts
│   ├── detector.py         loads models + test data, classifies rows
│   └── main.py             FastAPI app (API + serves the panel UI)
├── static/                 the panel interface (plain HTML/CSS/JS)
├── artifacts/              (created by setup.py) models, encoders, test data
└── db/                     (created at runtime) research_panel.db
```

## 3. What the database records

Created by `app/db.py` (SQLite, zero configuration — open `db/research_panel.db`
with any SQLite viewer):

| Table | Contents |
|---|---|
| `datasets` | the two datasets and their real sizes (train/test rows, features, classes) |
| `models` | every trained model: CV F1-macro, latency, training rows, hyperparameters, trained-at |
| `test_metrics` | each model's accuracy / precision / recall / F1 / AUC on the untouched test set |
| `per_class_metrics` | recall/precision/F1 for every class of every model |
| `predictions` | **every live detection** — timestamp, dataset, model, prediction, true label, confidence, matched, latency |
| `pipeline_steps` | the real phases of the project (Phase 0 → Phase 7), stored as rows |

The panel UI's "Under the Hood" tab shows the schema and live row counts, and
the "Prediction Log" tab shows the `predictions` table as it grows.

## 4. Setup (one time)

From this folder, with the Python environment of the main project (it has all
needed libraries — fastapi, uvicorn, joblib, pandas, numpy, scikit-learn,
xgboost):

```
.venv\..\..\\.venv\Scripts\python.exe scripts\setup.py
```

Or, if the `.venv` is already activated:

```
python scripts/setup.py
```

What it does:
1. copies the 8 trained models → `artifacts/models/`
2. copies the 2 label encoders → `artifacts/encoders/`
3. copies the 4 test-set files → `artifacts/test_data/`
4. copies `models_metadata.json` and `evaluation_results.json` → `artifacts/`
5. creates the database and seeds it from those real artifacts

## 5. Run

```
python run.py            # → http://127.0.0.1:8100
```

(or `python -m uvicorn app.main:app --port 8100`.)

The panel opens in the browser. The API reference is at `/docs`.

## 6. The panel tabs

- **Overview** — headline numbers straight from the database.
- **Under the Hood** — the pipeline phases and the database schema/row counts.
- **Models & Evaluation** — every model's metrics (from the DB), per-class
  breakdown.
- **Live Detection** — classify random rows from the real test set; **every
  prediction is written to the `predictions` table** and appears in the log.
- **Prediction Log** — the database rows, newest first, with a refresh button.

## 7. Verifying it is really using the database

1. Run a few Live Detection batches.
2. Open the Prediction Log — rows appear with timestamps.
3. (Optional) open `db/research_panel.db` in a SQLite viewer and run
   `SELECT COUNT(*) FROM predictions;` — the same number.

## 8. Honesty note

- The models were trained on NSL-KDD and CICIDS2017 in the **main project**.
  This project does not retrain; it presents and logs those models.
- Live Detection replays **real rows from the test sets** (the data the models
  were never trained on). It is not capturing live network traffic.
- All numbers shown come from `models_metadata.json` and
  `evaluation_results.json` — no figure in this project is fabricated.
