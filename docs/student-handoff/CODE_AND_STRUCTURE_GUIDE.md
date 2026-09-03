# Student Handoff — Code and Structure Guide

This guide is for the student who will **read, modify, or extend** the project.
It explains how the code is organised, which file does what, how a number
travels from the raw data to the dashboard, and what breaks if you change
something. It assumes the app already runs (see `SETUP_GUIDE.md`).

The two sibling documents cover different ground: `SETUP_GUIDE.md` = commands
to install and run; `PAGE_WALKTHROUGH.md` = what each screen means. This
document = the code itself.

---

## 1. The mental model (read this first)

The project has two halves that only talk over HTTP (the web protocol):

```
 raw data  ──►  Python ML pipeline  ──►  saved models + metrics JSON
               (src/ + notebooks/)        (registry/, data/processed/)

 backend (FastAPI)  ──HTTP──►  frontend (React in the browser)
 src/api/                           frontend/src/
```

- **Python side** (backend + science): loads the raw datasets, cleans them,
  trains the models, measures them, and later serves predictions. Slow to
  start, heavy files, science.
- **JavaScript side** (frontend): the pretty website. It asks the backend
  questions (`GET /compare`, `POST /simulate`, ...) and draws the answers.
  It never touches the datasets or models directly.

**One central fact file:** almost every path, dataset name, label mapping, and
the random seed live in exactly one file — `src/utils/config.py`. That is the
first file to read and the first place to look when you need "where does X
live?".

---

## 2. The real folder tree

Generated from the actual project (heavy/generated folders truncated where
marked). If you see a folder here that is *not* in your copy, run the command
noted next to it to recreate it.

```
Cyber threat Detection/
├── requirements.txt            Python dependencies (pinned versions)
├── README.md                   quick overview
├── SETUP_GUIDE.md              the original setup guide (root level)
├── GLOSSARY.md                 plain-language definitions of every term
├── AI_Coding_Master_Prompt.md  the phase-by-phase build instructions
├── Finalds.md, P2633978.md     thesis reference notes
├── Dataset_Selection_Justification.docx   a submitted .docx report
├── data/
│   ├── raw/                    ORIGINAL datasets (must be present)
│   │   ├── DATASET_MANIFEST.md inventory: every file, USED or IGNORED
│   │   ├── nsl-kdd/            NSL-KDD (KDDTrain+.txt, KDDTest+.txt, ...)
│   │   ├── MachineLearningCSV/MachineLearningCVE/   CICIDS2017, 8 CSVs
│   │   └── GeneratedLabelledFlows/                  ignored duplicate raw
│   ├── processed/              REGENERABLE cleaned data + metrics JSON
│   │   ├── nslkdd_train_X.pkl / _test_X.pkl         preprocessed splits
│   │   ├── nslkdd_train_y.pkl / _test_y.pkl         labels (same for cicids)
│   │   ├── nslkdd_preprocessor.joblib / cicids_preprocessor.joblib
│   │   ├── nslkdd_label_encoder.joblib / cicids_label_encoder.joblib
│   │   ├── nslkdd_feature_selection.csv / cicids_feature_selection.csv
│   │   ├── evaluation_results.json     → /compare, /models
│   │   ├── tuning_impact.json          → /tuning-impact
│   │   ├── development_progression.json → /progression
│   │   ├── training_curves.json        → /training-curves
│   │   └── prediction_log.json         the monitor's stored log (→ /predictions)
│   └── references/             Finalds.md, P2633978.md copies
├── src/
│   ├── __init__.py
│   ├── utils/
│   │   ├── config.py           ★ THE single source of truth (paths, labels, seed)
│   │   └── generate_docs.py    helper that regenerates some docs
│   ├── data/                   the "Phase 1-2" science
│   │   ├── loader.py           reads both datasets into one common schema
│   │   ├── preprocess.py       Preprocessor: impute, scale, one-hot, SMOTE
│   │   └── feature_selection.py Pearson + mutual info + RFE comparisons
│   ├── models/                 the "Phase 3-4" science
│   │   ├── train.py            grid search + stratified 5-fold CV (+SMOTE)
│   │   ├── evaluate.py         test-set metrics, charts, report
│   │   └── registry/           the trained models (regenerable: `python -m src.models.train`)
│   │       ├── <dataset>_<model>.joblib      8 model files
│   │       ├── <dataset>_<model>_meta.json   8 metadata files
│   │       └── models_metadata.json          merged metadata (→ /training-curves "saved")
│   └── api/                    the "Phase 5" backend
│       ├── main.py             the FastAPI app + every endpoint
│       ├── schemas.py          request/response shapes (Pydantic)
│       └── attack_info.py      plain-language attack explanations
├── frontend/                   the "Phase 6" website
│   ├── index.html              the HTML shell Vite loads
│   ├── package.json / package-lock.json   JS dependencies
│   ├── vite.config.js          dev-server config: port 5173, /api proxy → :8000
│   ├── public/                 static charts + data copied here by evaluate.py
│   │   ├── *.png               bar/ROC/confusion figures (also in reports/figures/)
│   │   ├── evaluation_results.json
│   │   └── training_curves/    old static curve PNGs (kept; UI now draws live charts)
│   ├── dist/                   BUILT website (regenerable: `npm run build`) — served by backend
│   └── src/
│       ├── main.jsx            React entry point
│       ├── App.jsx             tab layout + top bar + onboarding tour
│       ├── api.js              tiny fetch wrapper around the backend endpoints
│       ├── styles.css          all styling (the "classic light" theme)
│       ├── components/         AttackCard, DetectionExplain, HelpTip,
│       │                       MonitorContext, OnboardingTour, StatusPill,
│       │                       TrainingCharts
│       └── pages/              Dashboard (Live Monitor), Compare, Database,
│                               HowItWorks
├── notebooks/                  the step-by-step science, as notebooks
│   ├── 01_eda.ipynb            exploratory data analysis
│   ├── 02_preprocessing_feature_selection.ipynb
│   ├── 03_model_training.ipynb
│   └── 04_evaluation.ipynb
├── reports/                    generated reports + figures (regenerable)
│   ├── model_comparison_report.md, eda_report.md, verification_report.md,
│   ├── dataset_selection_justification.md, algorithm_selection_justification.md,
│   ├── development_progression_report.md, tuning_impact_report.md,
│   ├── model_dataset_usage_statistics.md, deployment_guidelines.md,
│   ├── examiner_qa.md
│   └── figures/                PNG charts (copied into frontend/public)
├── docs/                       submission-ready copies of the documentation
│   └── student-handoff/        ← you are reading these three files
├── tests/
│   ├── test_api.py             backend smoke tests (14)
│   └── test_panel_api.py       research-panel backend tests (5)
├── research_panel_project/     SEPARATE small app (see §9) — not part of the
│                               CyberGuard dashboard pipeline
├── nsl-kdd/, MachineLearningCSV/, GeneratedLabelledFlows/
│                               leftover root-level copies of the datasets;
│                               the pipeline does NOT use these (see §4.1)
└── .venv/                      your Python environment (machine-specific, never share)
```

Generated/truncated: `data/processed` is entirely regenerable (notebooks 01–02
or `python -m src.models.train`); `src/models/registry` is regenerable
(`python -m src.models.train`); `frontend/dist` is regenerable (`npm run
build`).

---

## 3. The one config file — `src/utils/config.py`

Everything downstream reads from here, so nothing is hard-coded twice:

- **Paths** — `ROOT_DIR` (computed as `Path(__file__).resolve().parents[2]`,
  i.e. "go up two folders from `src/utils/`"; the project can be moved as long
  as the inner layout is preserved), `DATA_RAW_DIR`, `DATA_PROCESSED_DIR`,
  `REPORTS_DIR`, `MODELS_DIR`, `FRONTEND_PUBLIC_DIR`.
- **Common label schema** — every dataset is converted to the same columns:
  `source`, `is_attack`, `attack_category`, `attack_type`; `NORMAL_CATEGORY =
  "Normal"`.
- **NSL-KDD** — the 41 feature names in file order, the 3 categorical columns
  (`protocol_type`, `service`, `flag`), and the full map from specific attack
  names (`neptune`, `satan`, ...) to the coarse classes DoS / Probe / R2L /
  U2R.
- **CICIDS2017** — the raw-dir path, the `*-WorkingHours*.csv` file pattern,
  the label→category map (BENIGN→Normal, FTP/SSH-Patator→Brute Force, ...),
  and the metadata columns dropped at load time.
- **`RANDOM_STATE = 42`** — the fixed seed that makes every experiment
  reproducible.

Rule of thumb: if a new script needs a path or a label mapping, import it from
`config.py`; do not invent a second copy.

---

## 4. The data layer — `src/data/`

### 4.1 `loader.py` — read the raw files once, into one format

- `load_nsl_kdd("train"/"test")` reads `KDDTrain+.txt` (125,973 rows) or
  `KDDTest+.txt` (22,544 rows). Files actually have 43 columns (41 features +
  attack type + a *difficulty* score); the difficulty column is metadata and is
  dropped so the model cannot peek at it. Raises a clear `FileNotFoundError`
  pointing at the manifest if a file is missing.
- `load_cicids2017_capped(per_class_cap=15_000)` reads the 8 daily CICIDS2017
  CSVs (2,830,743 raw rows) **chunk-by-chunk** to avoid loading a ~1 GB table
  into memory. Because the data is extremely imbalanced (Heartbleed has 11
  rows, BENIGN ~2.2 million), a two-pass method keeps *every* rare-class row
  and downsizes only the huge classes to 15,000 rows each → 62,422 cleaned
  rows. Random sampling would have thrown the rare attacks away entirely.
- Both produce the **common schema** (`source`, `is_attack`,
  `attack_category`, `attack_type` + features). Column names are normalised
  to `snake_case` (e.g. `Flow Bytes/s` → `flow_bytes_s`); the corrupted
  `\ufffd` character in web-attack labels is fixed to `-`.

> **Why the root-level dataset folders exist:** during development the datasets
> were downloaded twice (once at the root, once under `data/raw`). The
> pipeline reads `data/raw` **only** — the root copies are unused leftovers you
> can delete to reclaim ~4 GB.

### 4.2 `preprocess.py` — make messy data usable, honestly

The `Preprocessor` class chains three scikit-learn steps:

1. **Median imputation** — CICIDS2017 contains `Inf` (division by zero, e.g.
   `bytes / duration` with duration 0); `Inf` is replaced with missing and
   filled with the column median.
2. **Min-max scaling** — squashes every numeric feature into [0, 1] so a
   feature measured in microseconds does not dominate one measured in bytes.
3. **One-hot encoding** — turns the 3 text columns into 0/1 columns (41 raw
   features → 122 columns for NSL-KDD).

The headline rule, repeated throughout the code: **fit on train, transform on
test.** The preprocessor learns its medians/min-max from the training set
only, then is *applied* to the test set with those same fitted values. Doing
otherwise is **data leakage** — the model would have seen the exam answers and
its scores would be fiction. SMOTE (which invents synthetic rare-class rows)
is the extreme case: it must never touch test data.

### 4.3 `feature_selection.py` — which features matter?

Three methods, each ranked and written to `data/processed/*_feature_selection.csv`:

1. **Pearson correlation** — linear association between each feature and the
   class.
2. **Mutual information** — non-linear "bits of information about the class".
3. **RFE** (Recursive Feature Elimination) — repeatedly trains a base model
   and chops the least important features.

Run on the preprocessed matrix **before SMOTE** (synthetic rows must not
influence feature choice). The three methods' *consensus* subsets were very
aggressive (15 of 122 for NSL-KDD, 7 of 78 for CICIDS2017) — and they hurt
Logistic Regression, so the final training pipeline keeps the full
preprocessed feature set. See the progression numbers in §11 for the measured
effect.

> **Flagged claim:** the development-progression report says feature selection
> is then applied "as a filter only to the tree-based models" — but no such
> filter step exists in the current `feature_selection.py` module (it may live
> inside notebook 02). If a viva asks, verify this in the notebooks before
> repeating it.

---

## 5. The model layer — `src/models/`

### 5.1 `train.py` — grid search + cross-validation

- `MODELS` defines the four algorithms and their hyperparameter grids:
  - Logistic Regression — `C` ∈ {0.01, 0.1, 1, 10}, `max_iter=2000` (4 combos)
  - Decision Tree — `max_depth` ∈ {None, 10, 20}, `min_samples_leaf` ∈ {1, 5, 20} (9)
  - Random Forest — `n_estimators` ∈ {100, 200}, `max_depth` ∈ {None, 20},
    `min_samples_leaf` ∈ {1, 5} (8)
  - XGBoost — `n_estimators` ∈ {100, 200}, `max_depth` ∈ {3, 6},
    `learning_rate` ∈ {0.1, 0.3} (8)
- `tune_model(...)` runs `GridSearchCV` over a **stratified 5-fold** split with
  **SMOTE inside the pipeline** (so SMOTE is re-fitted on each fold's training
  portion only — the no-leakage design), scoring with **`f1_macro`** (accuracy
  is meaningless with imbalanced classes). `k_neighbors=3` for SMOTE so it
  still works when a class is extremely rare inside a fold. XGBoost needs
  numeric labels, so a `LabelEncoder` translates class names to 0..k-1.
- `measure_latency(...)` times inference in ms/row on the test set after a
  warm-up call.
- `save_model(...)` writes `registry/<dataset>_<model>.joblib` +
  `<dataset>_<model>_meta.json`; `write_registry_metadata()` rebuilds
  `models_metadata.json` from those files (the API reads this one merged
  file).
- `retrain_all()` is the one-command reproducibility path: reload raw data,
  refit preprocessors, save splits + encoders, tune all 8 models, measure
  latency, rebuild metadata. Run with `python -m src.models.train`; ≈30–45
  minutes on 16 cores (see §12 for per-model fit times).

### 5.2 `evaluate.py` — score the models on the unseen test set

- Loads the held-out test splits, loads each saved model, and computes per
  model: accuracy, macro precision/recall/F1, AUC-ROC (macro), latency, plus a
  **per-class** precision/recall/F1 table (so the rare classes are visible)
  and a confusion matrix.
- Writes `data/processed/evaluation_results.json` (read by `/models` and
  `/compare`), copies the charts into `frontend/public/`, and auto-generates
  `reports/model_comparison_report.md`.

### 5.3 `registry/` — the artifacts

8 `.joblib` models + 8 `_meta.json` files + `models_metadata.json`. Naming is
`<dataset>_<model>`, and the whole API is built around that convention.

---

## 6. The API layer — `src/api/`

### 6.1 `schemas.py` — the contract

Pydantic models that validate every request and shape every response.
`DatasetName` only accepts `"nslkdd" | "cicids"` and `ModelName` only
`"logistic" | "decision_tree" | "random_forest" | "xgboost"` — anything else is
rejected at the door. A prediction answer carries the verdict, `is_attack`,
`confidence`, a probability for *every* class, and optional `true_label` /
`matched` when a `row_id` was used.

### 6.2 `main.py` — the FastAPI app

- **Lazy loading:** model files are large, so preprocessors/encoders/models
  are loaded once on first use and cached.
- **Prediction log:** the monitor's classifications are kept in memory and
  persisted to `data/processed/prediction_log.json` (capped at the 200 most
  recent), so the Database tab survives restarts without a database server.
- `_predict(...)` runs a single row through `predict_proba`, returns the
  argmax class, and reports latency.

Endpoints (all implemented here):

| Endpoint | Verb | Purpose | Backing data |
|---|---|---|---|
| `/models` | GET | 8 models + test metrics (drives the monitor dropdown) | `evaluation_results.json` |
| `/compare` | GET | full comparison data for the chart page | `evaluation_results.json` |
| `/tuning-impact` | GET | baseline vs tuned scores | `tuning_impact.json` |
| `/progression` | GET | A→E development progression (LR) | `development_progression.json` |
| `/training-curves` | GET | convergence curves + saved-model configs | `training_curves.json` + `models_metadata.json` |
| `/attack-info/{type}` | GET | plain-language attack explanation | `attack_info.py` |
| `/predictions` | GET | stored prediction log, newest first | in-memory log + `prediction_log.json` |
| `/predict` | POST | classify one connection (raw features or `row_id`) | loaded artifacts |
| `/simulate` | POST | replay `count` random test rows as "live" traffic | test splits |
| `/` (static) | GET | serves the built frontend from `frontend/dist` if present; otherwise a JSON notice | `frontend/dist` |

Each data-driven endpoint raises **503 with a "not found — run ... first"**
message when its JSON is missing; `/predict` raises 400 for bad input. These
strings are used in the Setup Guide's troubleshooting.

### 6.3 `attack_info.py` — the knowledge base

`ATTACK_INFO` is a dictionary of plain-language explanations (what it is, how
it works, indicators, impact, defense, example) for every attack class the
models predict, from both datasets. Lookups are case-insensitive.

---

## 7. The frontend — `frontend/src/`

- **`main.jsx`** — React entry point.
- **`App.jsx`** — the four tabs (Live Monitor / Model Comparison / Database /
  How It Works), the "CyberGuard" brand, the "SIMULATED TRAFFIC" badge, and
  the auto-opening onboarding tour.
- **`api.js`** — one small function per endpoint. `BASE` is `"/api"` in dev
  (the Vite proxy strips it and forwards to :8000) and `""` in production (the
  backend serves both). This is the only place the frontend talks to the
  backend.
- **`pages/Dashboard.jsx`** — the Live Monitor. Runs a timer (~every 1.6 s)
  that calls `POST /simulate`, renders attack cards, and shows the
  explanation box. Dataset/model state comes from `MonitorContext`.
- **`components/MonitorContext.jsx`** — shared state (is monitoring running?
  what's in the log?) so the monitor keeps running while you visit other tabs.
- **`pages/Compare.jsx`** — the science page: headline bar chart, radar,
  latency table, scoreboard (green = best), baseline-vs-tuned panel, and the
  training-insights section. All data comes from four `api.js` calls
  (`compare`, `tuningImpact`, `progression`, `trainingCurves`). Clicking a
  legend entry hides/shows a series; tooltips show exact values.
- **`components/TrainingCharts.jsx`** — five chart components:
  `XgbLossChart`, `RandomForestChart`, `DecisionTreeChart`, `LogisticChart`,
  `ProgressionChart` (plus a `Seg` toggle). The **dashed "saved model" line**
  is drawn from the `saved` object returned by `/training-curves` (rounds /
  trees / max_depth / max_iter), and captions are placed *above* the plot
  using negative pixel offsets (`Y_ROW_1 = -18`, `Y_ROW_2 = -42`,
  `REF_LINE_TOP = 58`) so they never overlap the curves.
- **`pages/Database.jsx`** — polls `GET /predictions` every 2 s, applies the
  dataset/verdict filters and the row limit, shows latency and matched status.
- **`pages/HowItWorks.jsx`** — four plain-language algorithm cards and the
  attack-category list; clicking a category calls `/attack-info`.
- **`components/`** — `AttackCard` (verdict card), `DetectionExplain`
  (attack explanation box), `HelpTip` (the small "?" hints), `StatusPill`
  (state labels), `OnboardingTour` (the guided tour).
- **`styles.css`** — the whole "classic light" theme. All styling lives here.
- **`vite.config.js`** — dev server on :5173 with a proxy: `/api/*` →
  `http://127.0.0.1:8000/*`.

> Remember: the backend serves the **built** frontend (`frontend/dist`). After
> any frontend edit you must `npm run build` (Setup Guide §4.4) — otherwise the
> browser keeps showing the old bundle.

---

## 8. How a number travels from raw data to the dashboard

1. `loader.py` turns raw files into the common schema.
2. `preprocess.py` (fit-on-train/transform-on-test) produces the splits saved
   in `data/processed/*.pkl` + preprocessor/encoder `.joblib` files.
3. `train.py` grid-searches each (dataset, model) pair (SMOTE inside folds,
   `f1_macro`, 5-fold CV), saves the 8 models + metadata, and measures
   latency on the test set.
4. `evaluate.py` scores the saved models on the untouched test set and writes
   `evaluation_results.json` (+ charts + the comparison report).
5. `main.py` exposes `/compare`, `/training-curves`, `/simulate`, `/predict`,
   etc., transforming a live request with the *same* preprocessor and
   encoder used in training.
6. `api.js` → React pages render the numbers as charts/cards/tables.

The chain is deliberately linear: each stage's output is the next stage's
input, and each is regenerable from the stage before.

---

## 9. What `research_panel_project/` is (and is not)

It is a **separate, small Flask/FastAPI-style web app** with its own
`app/`, `db/`, `scripts/`, and a copy of the model artifacts under
`artifacts/`. It powers a research-panel demo (its `/api/trace_predict`
endpoint runs one test row through the pipeline and reports real stage
timings — that is what `tests/test_panel_api.py` asserts). It is **not** the
CyberGuard dashboard: it does not share `src/`, and its artifacts are copies.
Leave it alone unless you are specifically asked about the research panel.

---

## 10. Why these datasets and these algorithms (summaries)

Full write-ups: `reports/dataset_selection_justification.md` and
`reports/algorithm_selection_justification.md`.

**Datasets — a complementary pair.** NSL-KDD (2009; 125,973 train / 22,544
test rows; classes Normal / DoS / Probe / R2L / U2R) is the most-cited IDS
benchmark, but reflects late-1990s traffic. CICIDS2017 (2017; ~2.8 M rows, 14
attack categories, ML-ready 79-column CSVs) is modern and realistic but has
well-known label-inconsistency and imbalance quirks. Testing across both spans
~two decades of traffic and serves the project's cross-dataset
generalisability gap. CICIDS2017 has no official split, so one is created
stratified 80/20; NSL-KDD's split is predefined.

**Algorithms — a deliberate ladder, one design decision at a time.** Logistic
Regression (linear, readable) → Decision Tree (non-linear, white-box) →
Random Forest (bagging ensemble) → XGBoost (boosting ensemble). Excluded with
reasons: SVM and k-NN (scaling/latency on this data size), Naive Bayes
(correlated features violate its independence assumption), deep learning
(compute/interpretability budget; listed as future work). Explainability is a
first-class requirement, so the project keeps both a readable family and a
black-box family — enabling a deployment pairing like "XGBoost to detect,
Decision Tree to explain".

---

## 11. The honest numbers: past vs present, and what tuning bought

These are the real measured values (full detail in
`reports/development_progression_report.md` and `reports/tuning_impact_report.md`).

### Progression (Logistic Regression, held-out test set; accuracy / F1 / AUC)

| Dataset | A: raw | B: +cleaning | C: +feature selection | D: +SMOTE | E: +tuning |
|---|---|---|---|---|---|
| NSL-KDD | 0.609 / 0.274 / 0.638 | 0.751 / 0.529 / 0.927 | 0.692 / 0.433 / 0.899 | 0.763 / 0.557 / 0.906 | 0.763 / 0.557 / 0.906 |
| CICIDS2017 | 0.783 / 0.686 / 0.880 | 0.944 / 0.789 / 0.963 | 0.564 / 0.397 / 0.824 | 0.936 / 0.791 / 0.980 | 0.955 / 0.827 / 0.978 |

Reading: cleaning alone makes the model usable; aggressive feature selection
**hurts** LR (NSL-KDD F1 0.529 → 0.433, CICIDS2017 0.789 → 0.397) — this is why
the final pipeline keeps the full feature set; SMOTE recovers and beats the
loss; tuning adds little for LR specifically.

### Tuning impact (baseline → tuned test F1; ΔF1)

| Model | NSL-KDD | CICIDS2017 |
|---|---|---|
| Logistic Regression | 0.5572 → 0.5572 (+0.0000) | 0.7912 → 0.8267 (+0.0355) |
| Decision Tree | 0.5791 → 0.6170 (+0.0379) | 0.9524 → 0.9505 (−0.0019) |
| Random Forest | 0.5567 → 0.5384 (−0.0183) | 0.9276 → 0.9276 (+0.0000) |
| XGBoost | 0.5942 → 0.6086 (+0.0144) | 0.9789 → 0.9897 (+0.0108) |

Honest takeaway: tuning is a *small* lever; the pipeline steps (cleaning +
SMOTE) do the heavy lifting, and tuning can even hurt (Random Forest on
NSL-KDD). The charts on the Model Comparison tab reproduce this table live.

### Final standings (test F1, macro)

| Dataset | LR | DT | RF | XGB |
|---|---:|---:|---:|---:|
| NSL-KDD | 0.5572 | **0.6170** | 0.5384 | 0.6086 |
| CICIDS2017 | 0.8267 | 0.9505 | 0.9276 | **0.9897** |

XGBoost wins on the modern dataset; the simple Decision Tree generalises best
on the adversarial old benchmark. That difference is the project's key
finding — and it only exists because the four models were chosen to be
comparable in every other respect.

---

## 12. Compute and usage reality check

Measured in `reports/model_dataset_usage_statistics.md`. This is the honest
cost of this project — useful when someone asks "how heavy is this really?"

- **NSL-KDD:** 125,973 train / 22,544 test rows; after SMOTE 154,926 (R2L and
  U2R boosted to 15,000 each); 41 raw features → 122 after one-hot → 15 in the
  consensus subset.
- **CICIDS2017:** 2,830,743 raw rows → 62,422 after capping at 15,000/class →
  split 62,422 / 15,606 → 108,000 after SMOTE (9 classes balanced to 12,000);
  78 raw features → 7 in the consensus subset.
- **Tuning load:** 4 (LR) / 9 (DT) / 8 (RF) / 8 (XGB) hyperparameter combos,
  each with 5-fold CV and SMOTE inside the folds, scored by f1_macro.
- **Fit times** (16-core machine):

| Dataset | DT | LR | RF | XGB |
|---|---:|---:|---:|---:|
| NSL-KDD (CV F1-macro) | 25.2 s (0.8907) | 120.4 s (0.7432) | 204.7 s (0.9333) | 181.3 s (0.9565) |
| CICIDS2017 (CV F1-macro) | 28.0 s (0.9908) | 66.9 s (0.8755) | 112.9 s (0.9765) | 195.1 s (0.9848) |

- **Inference latency** (test set, ms/row): NSL-KDD 0.0004 / 0.0005 / 0.0095 /
  0.0021; CICIDS2017 0.0003 / 0.0003 / 0.0052 / 0.0047 (LR / DT / RF / XGB).
  Every model answers in well under a millisecond — all four are fast enough
  for live deployment; the choice is accuracy vs explainability, not speed.

---

## 13. Ideas for future improvement

Realistic next steps, sized for a student project. None are implemented yet —
they are starting points, so treat them as suggestions rather than promises.

1. **Add a deep-learning comparison.** The algorithm justification report
   explicitly lists DNN/CNN/LSTM as future work (the 16-week classical-ML
   budget is why they were excluded). A small CNN or LSTM compared against the
   four classical models on CICIDS2017 would test the "ensembles ≈ deep at far
   lower cost" claim (Gao et al., 2019) on this project's own data.
2. **Attack the hard classes specifically.** U2R (NSL-KDD) and Heartbleed /
   Infiltration (CICIDS2017) have so few real rows that even SMOTE cannot
   fully compensate. Ideas: per-class sampling strategies, cost-sensitive
   weights, or a second-stage binary detector trained specifically on those
   rare classes.
3. **Try newer datasets.** UNSW-NB15 and CSE-CIC-IDS2018 are already
   documented as backups/alternatives. `loader.py` is written for the current
   two, so a new loader + config block would be the clean way in (see the
   "what breaks" table for the touchpoints).
4. **Live-network validation.** The monitor replays recorded traffic. A
   next step is feeding it real packets (e.g. from a lab VM) and measuring
   latency/throughput on a live link, using `reports/deployment_guidelines.md`
   as the design reference.
5. **More attack categories / granular types.** The models predict coarse
   classes; fine-grained attack types (neptune vs smurf, FTP vs SSH-Patator)
   would be a natural extension of the label maps in `config.py`.

---

## 14. "If you change something, here's what breaks"

| If you change... | What breaks / what you must also do |
|---|---|
| A path in `config.py` | Everything follows it — good. But a wrong path means `FileNotFoundError`/503s everywhere; keep `ROOT_DIR`'s `parents[2]` logic intact (the whole project folder may move, the inner layout may not). |
| A label map in `config.py` (e.g. rename an attack class) | Saved label encoders in `data/processed` were fitted with the old names; API predictions read `le.classes_`, so frontend and backend can disagree. Retrain (or re-encode) after label-map changes. |
| SMOTE strategy / cap in `train.py` | All models change → re-run training, and the reported usage-statistics numbers (§12) no longer match. |
| The hyperparameter grids in `train.py` | Fit times change; the "saved model" dashed line on the training charts comes from `best_params` in `models_metadata.json` — regenerate it (`retrain_all` does). |
| `evaluate.py` metrics | Re-run evaluation so `evaluation_results.json`, the charts and `model_comparison_report.md` update together; the Compare page reads that JSON. |
| Anything in `frontend/src/` | Run `npm run build` — the backend serves the built `dist/`, so without a rebuild the browser shows stale code (symptom: `405` or old UI). |
| The prediction-log file (`data/processed/prediction_log.json`) | Not a problem — it is recreated empty on restart. (Deleting it just resets the Database tab.) |
| The 8-model file naming (`<dataset>_<model>.joblib`) | The API's `_artifacts()` and the registry metadata build depend on that convention. Rename → 503s. |
| Add a new algorithm | Touch all four conventions at once: `MODELS` in `train.py`, `ALGORITHMS` in `evaluate.py`, `MODELS` in `main.py`, the `ModelName` literal in `schemas.py`, and `_saved_configs()` if the chart needs a reference line. |
| The CICIDS2017 file pattern / column names | `loader.py` expects `*-WorkingHours*.csv` with a `Label` column (79 columns) and normalises names to `snake_case`. Other variants → `ValueError: Expected a 'Label' column...` or missing-feature 400s. |
| The raw datasets themselves | The models were trained on *these* files; different data = different numbers. All reported metrics (§11) are tied to the current `data/raw` contents. |

---

## 15. How to verify your changes (the checklist)

1. **Run the tests:** `.venv\Scripts\python.exe -m pytest tests\ -q` — expect
   **19 passed** (14 backend + 5 panel). The backend tests hit every endpoint
   through FastAPI's in-process client, so they fail loudly if the API or its
   data files are broken.
2. **Rebuild + reload the frontend** after any UI change: `cd frontend;
   npm run build; cd ..`, then hard-refresh the browser (`Ctrl+F5`).
3. **Watch the backend log** for errors when you click around — the 503/404
   messages in §6.2 tell you exactly which file/step is missing.
4. **If you touched the science:** regenerate the numbers before trusting the
   dashboard (the pipeline is regenerable end-to-end, §8).
5. **Keep the docs honest:** every number in this handoff and in `reports/`
   was measured; if your changes move them, update the reports too.
