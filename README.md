# AI-Based Cybersecurity Threat Detection Using Machine Learning Techniques

Final-year research project: compare four machine-learning algorithms for
network-intrusion detection on two public benchmark datasets, then serve the
trained models through a small web app so traffic can be classified live.

- **Algorithms:** Logistic Regression, Decision Tree, Random Forest, XGBoost
- **Datasets:** NSL-KDD and CICIDS2017
- **Deliverables:** data pipeline, trained model registry, evaluation report,
  FastAPI backend, React dashboard, deployment guidelines, glossary

Headline results (test set, F1 macro):

| Dataset   | Logistic | Decision Tree | Random Forest | XGBoost |
|-----------|---------:|--------------:|--------------:|--------:|
| NSL-KDD   | 0.557    | **0.617**     | 0.538         | 0.609   |
| CICIDS2017| 0.827    | 0.950         | 0.928         | **0.990** |

XGBoost is the accuracy leader on CICIDS2017 (99% F1, 99.88% accuracy) while
still predicting in under ~0.01 ms per row — see
[`reports/model_comparison_report.md`](reports/model_comparison_report.md).

---

## What this project does

Network intrusions (DoS attacks, port scans, brute-force logins, web attacks,
etc.) must be detected fast and reliably. This project:

1. Loads two standard intrusion-detection datasets and cleans them (missing /
   infinite values, corrupted labels, class imbalance).
2. Compares three feature-engineering techniques — Pearson correlation, mutual
   information, and recursive feature elimination — and records which features
   matter most.
3. Trains and tunes the four algorithms with **SMOTE kept inside the
   cross-validation folds** (no data leakage) and an **f1-macro** score so rare
   attacks are weighted as heavily as normal traffic.
4. Evaluates the final models on a completely untouched test split (including
   attack variants the models never saw) and measures inference latency — the
   accuracy-vs-speed trade-off a real security team has to make.
5. Packages the best models behind a REST API and a live dashboard so a network
   packet can be classified in real time during a demo.

All of it is built from scratch with scikit-learn, imbalanced-learn and XGBoost;
nothing is "given away" by a pre-built pipeline.

## Folder structure

```
data/
  raw/               original NSL-KDD & CICIDS2017 files (see data/raw/DATASET_MANIFEST.md)
  processed/         cleaned, feature-engineered splits + fitted preprocessors
                     and label encoders (auto-generated, git-ignored)
  references/        thesis docs & reference notes (not code-read)
notebooks/           01 EDA, 02 preprocessing + feature selection,
                     03 model training, 04 evaluation
src/
  data/              loader.py, preprocess.py, feature_selection.py
  models/            train.py, evaluate.py, registry/ (saved models, git-ignored)
  api/               FastAPI backend: main.py, schemas.py, attack_info.py
  utils/             config.py (paths, constants, seed)
frontend/            React + Vite dashboard (Phase 6)
reports/             EDA, model comparison, deployment guidelines; figures/
docs/                submission-ready export: all markdown docs + merged report
tests/               unit + API tests
GLOSSARY.md          plain-language definitions of every technical term
requirements.txt     pinned Python dependencies
```

## Prerequisites

- **Python 3.12** (the project was built and verified on 3.12.10)
- **Node.js 18+ and npm** (for the frontend; the build was verified on Node 24)

## Setup

### 1. Python environment

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Dataset files

Place the raw datasets under `data/raw/` as described in
[`data/raw/DATASET_MANIFEST.md`](data/raw/DATASET_MANIFEST.md):

- NSL-KDD: `KDDTrain+.txt` and `KDDTest+.txt`
- CICIDS2017: the `MachineLearningCVE/*.csv` files

The pipeline is **reproducible end to end**: run `notebooks/01` → `04` in order
and every `data/processed/` artifact and `src/models/registry/*` file is
regenerated. Already-processed artifacts are git-ignored on purpose.

### 3. Frontend dependencies (only needed for the web app)

```
cd frontend
npm install
```

---

## How to run

### Option A — just the API + notebook results (fastest)

The trained models already exist in `src/models/registry/`:

```
.venv\Scripts\python.exe -m uvicorn src.api.main:app --reload --port 8000
```

Then open http://127.0.0.1:8000/docs for the interactive API reference.
Main endpoints:

| Method | Path                | Purpose                                     |
|--------|---------------------|---------------------------------------------|
| GET    | `/`                 | web app (if built) or service info          |
| GET    | `/models`           | list of trained models + metadata           |
| GET    | `/compare`          | side-by-side metrics across models          |
| GET    | `/attack-info/{type}`| plain-language explanation of an attack     |
| POST   | `/predict`          | classify one packet (raw features or a test-set row) |
| POST   | `/simulate`         | one live-simulated prediction for the dashboard |

### Option B — full web app (backend + dashboard)

```
# terminal 1: backend (serves the API and the built frontend)
.venv\Scripts\python.exe -m uvicorn src.api.main:app --port 8000

# terminal 2: frontend development server (hot reload)
cd frontend
npm run dev            # http://localhost:5173  (proxies /api to the backend)
```

For a production-style single server, build the frontend once and the backend
serves it at `/` automatically:

```
cd frontend
npm run build          # writes frontend/dist/ (served by the API at /)
.venv\Scripts\python.exe -m uvicorn src.api.main:app --port 8000
```

---

## How to retrain

Two equivalent ways — both reproduce the reported numbers exactly.

### Notebook path (day-to-day)

```
.venv\Scripts\python.exe -m jupyter nbconvert --execute --to notebook --output <out>
    notebooks/01_eda.ipynb
    notebooks/02_preprocessing_feature_selection.ipynb
    notebooks/03_model_training.ipynb
    notebooks/04_evaluation.ipynb
```

(run each in order; 03 takes ~10 minutes for all 8 model/dataset pairs).

### One-command path

```
.venv\Scripts\python.exe -m src.models.train
```

`retrain_all()` (in `src/models/train.py`) reloads the raw datasets, rebuilds
the preprocessed splits, re-tunes all four algorithms on both datasets with
SMOTE inside the folds, measures latency and refreshes the registry —
~30–45 minutes on a 16-core machine.

## Running the tests

```
.venv\Scripts\python.exe -m pytest tests\test_api.py -v
```

14 tests cover every API endpoint (models list, comparison, attack info,
prediction by raw features and by test-row id, simulation, and the built
frontend being served at `/`).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` when running `uvicorn ...` | activate the venv first (`\.venv\Scripts\activate`); the global Python won't have the deps |
| API starts but `/models` returns empty list | the registry was deleted/never trained — run `python -m src.models.train` (or notebook 03) |
| `/predict` with `row_id` errors | that dataset's test index is out of range; pass `features` instead |
| Frontend dev server can't reach `/api` | the backend must be running on port 8000 (vite proxies `/api` → `127.0.0.1:8000`) |
| `npm` not found in a new terminal | PATH was set during install; refresh it: `$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")` |
| `npm install` esbuild warning `The postinstall script ... is blocked` | harmless — the build still works |
| Training is slow / OOM | lower `n_jobs` in `tune_model` (e.g. `n_jobs=2`) and set `--workers 1` |
| Jupyter kernel not found | install the kernel into the venv: `python -m ipykernel install --user --name .venv` |

## Ethical note

This project is defensive only: it detects and labels network traffic using
anonymised public datasets. It contains no offensive capability. See
[`reports/deployment_guidelines.md`](reports/deployment_guidelines.md) and the
ethics form in `Finalds.md`.

## Further reading

- [`reports/model_comparison_report.md`](reports/model_comparison_report.md) — full metrics, charts, per-class recall
- [`reports/dataset_selection_justification.md`](reports/dataset_selection_justification.md) — why NSL-KDD and CICIDS2017 were chosen (with benchmark comparison table)
- [`reports/examiner_qa.md`](reports/examiner_qa.md) — viva practice Q&A with model answers
- [`docs/PHASE_EXPLANATIONS.md`](docs/PHASE_EXPLANATIONS.md) — deep phase-by-phase explanation (numbers auto-generated from the JSON artifacts)
- [`docs/PROJECT_WALKTHROUGH.md`](docs/PROJECT_WALKTHROUGH.md) — end-to-end tour: datasets → pipeline → models → API → dashboard, plus how to read every number
- [`SETUP_GUIDE.md`](SETUP_GUIDE.md) — step-by-step setup on another PC
- [`reports/deployment_guidelines.md`](reports/deployment_guidelines.md) — how to integrate this into a real network/SOC
- [`GLOSSARY.md`](GLOSSARY.md) — every technical term explained in plain English
- [`notebooks/01_eda.ipynb`](notebooks/01_eda.ipynb) — the data at a glance
