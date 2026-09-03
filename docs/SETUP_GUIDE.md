# SETUP GUIDE — AI-Based Cybersecurity Threat Detection

How to set up and run this project on **any other PC**, step by step. This guide
exists so you can zip the project folder, send it (plus this file), and the
recipient can go from zero to a working dashboard.

Covers: what's in the folder, prerequisites, environment setup, dependencies
(what each one is for), running the app, retraining, tests, troubleshooting.

---

## 1. What's in the project folder

```
AI-Based-Cyber-Threat-Detection/
│
├── AI_Coding_Master_Prompt.md      the phase-by-phase build instructions
├── README.md                       quick overview + links to all docs
├── SETUP_GUIDE.md                  ← this file
├── requirements.txt                Python dependencies (pinned versions)
├── GLOSSARY.md                     plain-language definitions of every term
│
├── data/
│   ├── raw/                        the datasets (MUST be present — see §4)
│   │   ├── DATASET_MANIFEST.md     where the datasets come from
│   │   ├── KDDTrain+.txt           NSL-KDD training set
│   │   ├── KDDTest+.txt            NSL-KDD test set
│   │   └── MachineLearningCSV/     CICIDS2017 CSV files (2 folders: MachineLearningCVE)
│   ├── processed/                  cleaned splits + preprocessors (regenerable)
│   └── references/                 thesis docs & reference notes
│
├── notebooks/
│   ├── 01_eda.ipynb                       exploratory data analysis
│   ├── 02_preprocessing_feature_selection.ipynb   cleaning + feature selection
│   ├── 03_model_training.ipynb             grid search + SMOTE + k-fold CV
│   └── 04_evaluation.ipynb                 test-set evaluation + reports
│
├── src/
│   ├── data/       loader.py, preprocess.py, feature_selection.py
│   ├── models/     train.py, evaluate.py, registry/ (trained models)
│   ├── api/        main.py, schemas.py, attack_info.py (FastAPI backend)
│   └── utils/      config.py (paths, constants, random seed)
│
├── frontend/       React + Vite dashboard (see §7)
├── reports/        generated reports + figures
├── docs/           submission-ready copies of all documentation
└── tests/          test_api.py — 14 tests
```

Two large, regenerable things are normally **excluded** from a git commit, so
whether they're in your zip depends on the option you pick in §9:

| Folder | Content | Can it be regenerated? |
|---|---|---|
| `data/raw/` | the raw datasets | No — must be downloaded or included in the zip |
| `data/processed/` | cleaned splits, preprocessors | Yes — run notebooks 01–02 |
| `src/models/registry/` | 8 trained models + metadata | Yes — run notebook 03 (or one command) |
| `frontend/dist/` | built web app | Yes — `npm run build` |
| `frontend/node_modules/` | JS packages | Yes — `npm install` |
| `.venv/` | Python environment | Never share — recreate on each machine |

---

## 2. Prerequisites (what to install on the new PC)

| Requirement | Version tested | Why |
|---|---|---|
| **Python** | 3.12 (3.12.10 tested) | the language everything is written in |
| **Node.js + npm** | Node 24 / npm 11 (18+ also fine) | only needed for the frontend |
| **Git** | any recent | optional, only if cloning |

Check what's installed:

```
python --version
node --version
npm --version
```

> Windows note: if `python` isn't found, try `py --version` and use `py -3.12`
> in place of `python` below.

---

## 3. Python environment setup (first step on any new machine)

Open a terminal in the project folder and run:

```
python -m venv .venv
```

Activate it:

- Windows (PowerShell): `.venv\Scripts\activate`
- Windows (Command Prompt): `.venv\Scripts\activate.bat`
- macOS / Linux: `source .venv/bin/activate`

Install all Python dependencies:

```
pip install -r requirements.txt
```

You'll see the terminal prompt prefixed with `(.venv)` — that's how you know
you're inside the environment. **Every command below assumes the venv is
active** (or you call `.venv\Scripts\python.exe` directly, which also works).

Verify the install:

```
python -c "import pandas, numpy, sklearn, xgboost, imblearn, joblib, fastapi, uvicorn, pydantic, pytest; print('all imports OK')"
```

---

## 4. The datasets (important!)

The pipeline loads raw files from `data/raw/`. They are **not downloaded by
code** — they must be present. Either:

- **(a) they're already in the zip** under `data/raw/`, or
- **(b) download them** — see `data/raw/DATASET_MANIFEST.md` for the exact
  source URLs. You need:
  - `KDDTrain+.txt` and `KDDTest+.txt` (NSL-KDD)
  - the `MachineLearningCVE/` CSV folder (CICIDS2017, ~2 GB)

If `data/raw` is missing/empty, the loaders raise a clear
`FileNotFoundError` telling you exactly which file is missing.

---

## 5. How the project was built (so you can explain it)

The build followed the phases in `AI_Coding_Master_Prompt.md`:

1. **Phase 0–0.5 — Setup & data.** Python environment, `requirements.txt`,
   `data/raw/DATASET_MANIFEST.md`, folder skeleton, config module
   (`src/utils/config.py`) holding paths, constants and the fixed random seed.
2. **Phase 1 — EDA.** `notebooks/01_eda.ipynb`: class counts, missing values,
   imbalance analysis.
3. **Phase 2 — Processing & feature selection.** `notebooks/02_...ipynb`:
   load both datasets into one common schema; fix corrupted labels; Inf→NaN→
   median imputation; min-max scaling; one-hot encoding (NSL-KDD categoricals);
   SMOTE (training only); three feature-selection methods compared (Pearson
   correlation, mutual information, RFE).
4. **Phase 3 — Training.** `notebooks/03_...ipynb` + `src/models/train.py`:
   grid search + stratified 5-fold CV, SMOTE *inside* the folds (no leakage),
   f1-macro scoring, for all 4 algorithms × 2 datasets = 8 models, saved to
   `src/models/registry/`.
5. **Phase 4 — Evaluation.** `notebooks/04_...ipynb` + `src/models/evaluate.py`:
   metrics on the untouched test set, per-class recall, ROC curves, latency,
   `reports/model_comparison_report.md`.
6. **Phase 5 — API.** `src/api/`: FastAPI backend serving the models
   (`/models`, `/compare`, `/attack-info`, `/predict`, `/simulate`) + 14 tests.
7. **Phase 6 — Frontend.** `frontend/`: React + Vite dashboard with live
   monitor, model comparison charts, and an attack explainer.
8. **Phase 7 — Docs.** README, deployment guidelines, glossary, Q&A bank.

The single most important design decision to remember: **SMOTE is applied
inside the cross-validation folds, never to the test set** — this is what
keeps the reported numbers honest.

---

## 6. Dependencies — what each one does

### Python (`requirements.txt`)

| Package | Version | Role in this project |
|---|---|---|
| `pandas` | 3.0.5 | reading/cleaning the CSV+txt datasets, tables |
| `numpy` | 2.5.2 | fast numeric arrays under everything |
| `joblib` | 1.5.3 | saving/loading the trained models (`.joblib`) |
| `scikit-learn` | 1.9.0 | Logistic Regression, Decision Tree, Random Forest, grid search, k-fold CV, metrics, feature selection |
| `xgboost` | 3.4.0 | the 4th algorithm (XGBoost) |
| `imbalanced-learn` | latest | SMOTE (oversamples rare attack classes) |
| `matplotlib` | 3.11.1 | confusion matrices, ROC curves |
| `seaborn` | latest | prettier charts on top of matplotlib |
| `fastapi` | latest | the backend web framework |
| `uvicorn` | latest | the server that runs the FastAPI app |
| `pydantic` | latest | automatic request/response validation |
| `pytest` | latest | runs the unit tests |
| `jupyter` / `nbconvert` / `ipykernel` | latest | running the notebooks headlessly |

### JavaScript (`frontend/package.json`)

| Package | Version | Role |
|---|---|---|
| `react` / `react-dom` | ^18.3.1 | the UI library |
| `recharts` | ^2.15.0 | comparison charts (bar + radar) |
| `vite` | ^5.4.11 | build tool + dev server |
| `@vitejs/plugin-react` | ^4.3.4 | React support in Vite |

Frontend setup (only if you want the web app):

```
cd frontend
npm install
```

---

## 7. Running the project (3 options)

### Option A — full web app, one server (recommended for the demo)

The backend serves the built dashboard at the same address:

```
# 1. build the frontend once (output goes to frontend/dist/)
cd frontend
npm run build
cd ..

# 2. start the backend (it serves the API AND the dashboard)
.venv\Scripts\python.exe -m uvicorn src.api.main:app --port 8000
```

Then open **http://127.0.0.1:8000** in a browser and press **Start Monitoring**.

> If the button says "Cannot reach the backend", the server isn't running —
> start it first. (A stale built frontend can also cause a `405 Method
> Not Allowed`; rebuild with `npm run build` after any change to `src/api.js`.)

### Option B — development mode (hot reload, two processes)

```
# terminal 1: backend
.venv\Scripts\python.exe -m uvicorn src.api.main:app --port 8000

# terminal 2: frontend dev server (auto-reloads on save)
cd frontend
npm run dev
```

Open **http://localhost:5173** — Vite proxies `/api` requests to the backend.

### Option C — API only (no browser)

```
.venv\Scripts\python.exe -m uvicorn src.api.main:app --port 8000
```

Interactive API documentation: **http://127.0.0.1:8000/docs**

Try a prediction:

```
curl -X POST http://127.0.0.1:8000/predict -H "Content-Type: application/json" ^
  -d "{\"dataset\":\"cicids\",\"model\":\"xgboost\",\"row_id\":0}"
```

---

## 8. Retraining and tests

### Retrain everything (regenerates the 8 models)

```
.venv\Scripts\python.exe -m src.models.train
```

Runs grid search + SMOTE + CV on both datasets (~30–45 min on a 16-core PC;
fewer cores → longer). Alternatively run the notebooks in order:

```
.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute notebooks\01_eda.ipynb --output /dev/null
# ... repeat for 02, 03, 04
```

### Tests

```
.venv\Scripts\python.exe -m pytest tests\test_api.py -v
```

Expect **14 passed**. The warnings printed are harmless deprecation notices.

---

## 9. Zipping for another PC — two options

### Option 1 — "Instant run" zip (bigger, ~2–3 GB)

Include **everything except** `.venv/` and `frontend/node_modules/`:

```
data/raw/          ← the datasets (otherwise Option 1 becomes Option 2)
data/processed/    ← already-cleaned splits (skip loading work)
src/models/registry/  ← the 8 trained models (skip 30-min retraining)
frontend/dist/     ← already-built dashboard (skip npm run build)
```

Recipient only does: venv → `pip install -r requirements.txt` → start uvicorn.

### Option 2 — "Source only" zip (small, but needs steps)

Include the code + docs + notebooks, **exclude** `data/raw/`, `data/processed/`,
`src/models/registry/`, `frontend/dist/`, `.venv/`, `frontend/node_modules/`.
Recipient must:

1. add the datasets to `data/raw/` (§4),
2. run `python -m src.models.train` (or notebooks 01–04) to regenerate the
   processed data and models,
3. `npm install` + `npm run build` for the frontend,
4. start uvicorn (§7).

Both options: never zip `.venv/` (machine-specific) and never zip
`frontend/node_modules/` (recreated by `npm install`).

---

## 10. Troubleshooting on a new machine

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: pandas` | venv not activated / `pip install -r requirements.txt` not run |
| `FileNotFoundError ... KDDTrain+.txt` | datasets missing — see §4 |
| uvicorn runs but `/models` is empty | registry was excluded from the zip — retrain (§8) |
| `405 Method Not Allowed` in the dashboard | rebuild the frontend (`npm run build`) — the served bundle was stale |
| `npm` not recognised | install Node; refresh the PATH: `$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")` |
| `python` not recognised on Windows | try `py -3.12` instead |
| slow training / memory errors | lower `n_jobs` in `src/models/train.py` (`n_jobs=2`) |
| port 8000 already in use | pick another port: `--port 8001` and open that URL |
| Jupyter kernel missing | `python -m ipykernel install --user --name .venv` |

---

## 11. Quick start cheat-sheet (Windows)

```
# one-time setup
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd frontend ; npm install ; npm run build ; cd ..

# run the demo
.venv\Scripts\python.exe -m uvicorn src.api.main:app --port 8000
# open http://127.0.0.1:8000
```

See also: `README.md` (overview), `reports/deployment_guidelines.md` (how the
system fits a real network), `GLOSSARY.md` (every term explained),
`reports/examiner_qa.md` (viva practice questions).
