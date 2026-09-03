# Phase Explanations — AI-Based Cybersecurity Threat Detection

How the project was built, phase by phase, with the reasoning behind every
decision. Written so a reader with no machine-learning background can follow.

> **All tables with numbers below are auto-generated** from
> `data/processed/evaluation_results.json` and
> `src/models/registry/models_metadata.json` by:
>
> ```
> .venv\Scripts\python.exe -m src.utils.generate_docs
> ```
>
> Re-run that command after retraining and the numbers here update themselves.
> Placeholders that still look like `{{...}}` mean the script hasn't been run.

---

# Phase 0 — Environment & Folder Setup

**Goal:** a reproducible workspace so every later phase runs identically on any machine.

What was done:
- Created the folder skeleton: `data/raw/`, `data/processed/`, `notebooks/`, `src/` (data, models, api, utils), `reports/`, `tests/`, `frontend/`.
- Created `requirements.txt` with **pinned versions** (pandas 3.0.5, numpy 2.5.2, scikit-learn 1.9.0, xgboost 3.4.0, etc.) — pinning matters because a library update can silently change results. The thesis numbers must be reproducible.
- Created a Python virtual environment (`.venv`) and installed everything.
- Created `src/utils/config.py` — one file holding all paths, constants, and **`RANDOM_STATE = 42`**.

**Key decision — the fixed seed:** every split, SMOTE sampling, and model initialisation uses seed 42. Without it, two runs on the same data give slightly different models and an examiner cannot reproduce the report. With it, the whole pipeline is deterministic.

# Phase 0.5 — Data Acquisition & Manifest

**Goal:** know exactly where every dataset came from, and keep it in `data/raw/`.

- Documented sources in `data/raw/DATASET_MANIFEST.md` (origin, URL, size).
- Placed **NSL-KDD**: `KDDTrain+.txt` (125,973 rows) and `KDDTest+.txt` (22,544 rows) — 41 features, 4 attack categories + Normal.
- Placed **CICIDS2017**: the `MachineLearningCVE/` folder of CSVs (~2.8M rows, 78 features).
- Added `.gitignore` so huge raw files and regenerable artifacts are never committed.

**Why two datasets?** NSL-KDD is the classic academic benchmark (2009); CICIDS2017 is modern and realistic (2017). Using both shows the work is not tuned to a single dataset — the "cross-dataset robustness" theme from the research gaps. The full justification (including the comparison of alternative IDS benchmarks and why they were rejected) is documented in [`reports/dataset_selection_justification.md`](../reports/dataset_selection_justification.md).

# Phase 1 — Exploratory Data Analysis (EDA)

**Goal:** understand the data *before* touching any model (`notebooks/01_eda.ipynb`).

- Counted rows, columns, missing values, and data types per dataset.
- **Found the class imbalance:** NSL-KDD train has 67,343 Normal but only 52 U2R and 995 R2L; CICIDS2017 is worse (~80% normal, and **Heartbleed has 11 rows in the entire dataset**).
- Plotted class distributions and feature distributions.

**Why this matters:** the imbalance *is* the research problem. A naive model would say "Normal" every time and score ~80% accuracy while detecting nothing. This justifies the later choices: f1-macro scoring, SMOTE, and stratified folds.

# Phase 2 — Preprocessing & Feature Selection

**Goal:** turn raw files into clean, model-ready tables.

### Loading (`src/data/loader.py`)
- **Common schema:** every row gets `source`, `is_attack`, `attack_category`, `attack_type`, so both datasets share one interface.
- **NSL-KDD cleaning:** the file's 43rd column is a `difficulty` score — metadata, not traffic. **Dropped at load**, otherwise the model would cheat by learning "high difficulty = attack".
- **CICIDS2017 cleaning:** found a corrupted label (a broken Unicode character in "Web Attack", fixed with a `startswith` check) and **Infinity cells** (mostly in bulk features), converted to NaN. Also found 8 **zero-variance** features (e.g. `bwd_psh_flags`, the `*_bulk` rate fields) — constant columns carry zero information.
- **Capped loading:** CICIDS2017 is so skewed that random sampling would destroy rare classes, so the loader keeps *every* rare-class row but caps big classes (BENIGN, DoS) at 15,000 → 62,422 rows.

### Preprocessor (`src/data/preprocess.py`)
One pipeline fitted **on the training set only**, then reused on the test set and later on live rows:
1. `Inf → NaN`
2. **median imputation** (robust to outliers)
3. **min-max scaling** to [0,1]
4. **one-hot encoding** for NSL-KDD's categoricals (`protocol_type`, `service`, `flag`) — this grew NSL-KDD from 41 to **122 columns**.

### Label encoding
`LabelEncoder` maps attack names to numbers (alphabetical: DoS, Normal, Probe, R2L, U2R for NSL-KDD; 9 classes for CICIDS2017). The encoder is **saved**, so the API decodes predictions back to names identically.

### SMOTE (in `notebooks/02`)
- NSL-KDD: boost only R2L and U2R to 15,000 each (other classes stay real) → 154,926 rows.
- CICIDS2017: `"auto"` balances all 9 classes to 12,000 each → 108,000 rows.
- **Rule enforced: SMOTE on training only. The test set is never touched.**

### Feature selection (three methods compared — `src/data/feature_selection.py`)
1. **Pearson correlation** — linear relationships with the label
2. **Mutual information** — catches *non-linear* relationships correlation misses
3. **RFE** (recursive feature elimination) — repeatedly trains, drops the weakest feature

Results: NSL-KDD top features include `src_bytes`; CICIDS2017 top features are packet/flow sizes (`average_packet_size`, `packet_length_mean`). Selection ran on **pre-SMOTE training data** to stay honest.

# Phase 3 — Model Training & Tuning

**Goal:** train 8 models (4 algorithms × 2 datasets) with honest scores (`notebooks/03_model_training.ipynb`, `src/models/train.py`).

- **Algorithms:** Logistic Regression (fast baseline), Decision Tree (explainable), Random Forest (bagging ensemble), XGBoost (boosting ensemble).
- **Grid search:** each algorithm tried a grid of hyperparameters (e.g. Random Forest: 100/200 trees × depth None/20 × min leaf 1/5).
- **Stratified 5-fold CV:** folds keep the same class proportions as the full data — vital for rare classes.
- **SMOTE inside the pipeline, inside the folds.** `ImbPipeline([SMOTE, classifier])` is what gets cross-validated, so SMOTE is refitted on each fold's training portion only. SMOTE-ing before splitting would let synthetic rows leak into validation folds and inflate scores.
- **Scored on `f1_macro`** so rare classes weigh the same as Normal.
- `k_neighbors=3` for SMOTE (not the default 5) so it still works when a class is tiny inside a fold.
- Latency measured (ms per row) for the accuracy-vs-speed trade-off.

### Cross-validation F1-macro (mean over the 5 folds)

| Dataset | Model | CV F1-macro |
|---|---|---:|
| nslkdd | Logistic Regression | 0.7432 |
| nslkdd | Decision Tree | 0.8907 |
| nslkdd | Random Forest | 0.9333 |
| nslkdd | XGBoost | 0.9565 |
| cicids | Logistic Regression | 0.8755 |
| cicids | Decision Tree | 0.9908 |
| cicids | Random Forest | 0.9765 |
| cicids | XGBoost | 0.9848 |

Best cross-validation F1 on NSL-KDD: **XGBoost (0.9565)**.
Best cross-validation F1 on CICIDS2017: **Decision Tree (0.9908)**.

All 8 models + per-model metadata JSONs are saved to `src/models/registry/`, plus a combined `models_metadata.json` the API reads.

# Phase 4 — Evaluation on the Untouched Test Set

**Goal:** the real exam — scores on data the models never saw (`notebooks/04_evaluation.ipynb`, `src/models/evaluate.py`).

Computed accuracy, precision, recall, F1 (macro), **AUC-ROC**, per-class recall, and latency on the test splits. Charts went to `reports/figures/` (mirrored to `frontend/public/`), and the full write-up is `reports/model_comparison_report.md`.

### NSL-KDD test set (22,544 rows)

| Model | Accuracy | Precision | Recall | F1 | AUC-ROC | Latency (ms/row) |
|---|---|---|---|---|---|---:|
| Logistic Regression | 0.7628 | 0.6707 | 0.6295 | 0.5572 | 0.9057 | 0.0008 |
| Decision Tree | 0.8163 | 0.7545 | 0.5836 | 0.6170 | 0.7672 | 0.0006 |
| Random Forest | 0.7488 | 0.7972 | 0.5081 | 0.5384 | 0.9489 | 0.0089 |
| XGBoost | 0.7782 | 0.8281 | 0.5653 | 0.6086 | 0.9491 | 0.0027 |

Best overall F1 on NSL-KDD test: **Decision Tree (0.6170)**.

Per-class recall (share of each true class caught):

| Class | Logistic Regression | Decision Tree | Random Forest | XGBoost |
|---|---|---|---|---|---|---|---|
| DoS | 0.8105 | 0.9005 | 0.7604 | 0.8202 |
| Normal | 0.9233 | 0.9616 | 0.9730 | 0.9731 |
| Probe | 0.7270 | 0.6877 | 0.5915 | 0.6258 |
| R2L | 0.1344 | 0.2338 | 0.1112 | 0.1538 |
| U2R | 0.5522 | 0.1343 | 0.1045 | 0.2537 |

### CICIDS2017 test set (15,606 rows)

| Model | Accuracy | Precision | Recall | F1 | AUC-ROC | Latency (ms/row) |
|---|---|---|---|---|---|---:|
| Logistic Regression | 0.9549 | 0.8391 | 0.8622 | 0.8267 | 0.9784 | 0.0006 |
| Decision Tree | 0.9972 | 0.9951 | 0.9257 | 0.9505 | 0.9629 | 0.0004 |
| Random Forest | 0.9970 | 0.9925 | 0.8944 | 0.9276 | 0.9919 | 0.0063 |
| XGBoost | 0.9988 | 0.9974 | 0.9832 | 0.9897 | 1.0000 | 0.0067 |

Best overall F1 on CICIDS2017 test: **XGBoost (0.9897)**.

Per-class recall (share of each true class caught):

| Class | Logistic Regression | Decision Tree | Random Forest | XGBoost |
|---|---|---|---|---|---|---|---|
| Botnet | 0.9848 | 0.9949 | 1.0000 | 0.9975 |
| Brute Force | 0.9946 | 1.0000 | 1.0000 | 1.0000 |
| DDoS | 0.9880 | 0.9997 | 0.9997 | 0.9997 |
| DoS | 0.9723 | 0.9983 | 0.9977 | 0.9990 |
| Heartbleed | 0.5000 | 0.5000 | 0.5000 | 1.0000 |
| Infiltration | 0.5714 | 0.8571 | 0.5714 | 0.8571 |
| Normal | 0.8307 | 0.9920 | 0.9910 | 0.9977 |
| PortScan | 0.9937 | 0.9983 | 0.9987 | 0.9980 |
| Web Attack | 0.9243 | 0.9908 | 0.9908 | 1.0000 |

**The key finding:** the NSL-KDD train→test drop is *deliberate* — the official NSL-KDD test set contains attack variants never seen in training. That gap is evidence about **generalisation to unseen attacks**, the core motivation of the project. CICIDS2017's high F1 is realistic for a distribution that matches training.

# Phase 5 — Backend API

**Goal:** serve the trained models so traffic can be classified on demand (`src/api/`).

- `main.py` — FastAPI app with endpoints:
  - `GET /models` — list of models + metrics from the registry
  - `GET /compare` — comparison data for the charts
  - `GET /attack-info/{type}` — plain-language explanation of an attack (case-insensitive lookup; a bug where `str.title()` corrupted "DoS" into "Dos" was fixed)
  - `POST /predict` — classify one packet by raw features or by a test-set `row_id`
  - `POST /simulate` — replay real test rows as "live" traffic for the dashboard
  - `GET /docs` — auto-generated interactive API documentation
- Lazy loading: artifacts (models, test data) load on first use and are cached in memory.
- CORS enabled; the built frontend is served from `/` when `frontend/dist/` exists.
- `schemas.py` — Pydantic models validating every request/response.
- `tests/test_api.py` — **14 tests, all passing**.

# Phase 6 — Frontend Dashboard

**Goal:** a visual demo for non-technical viewers (React + Vite + Recharts in `frontend/`).

- **Live Monitor tab:** polls `POST /simulate` every 1.6 s, shows up to 28 packets with predicted attack, confidence, true label and a "SIMULATED TRAFFIC" badge; clicking an attack opens its `/attack-info` explanation.
- **Model Comparison tab:** dataset toggle, bar + radar charts, latency and scoreboard tables from `/compare`.
- **How It Works tab:** methodology in plain language + the attack category library.
- Dark "SOC" theme in `styles.css`.
- `vite.config.js`: dev server on :5173 proxies `/api` to the backend, stripping the prefix.
- **Known fix:** the production bundle must call same-origin routes. `src/api.js` selects `/api` in dev and the root path in production (`import.meta.env.DEV`); after any change, rebuild with `npm run build`.

# Phase 7 — Documentation

**Goal:** make the project understandable and reproducible.

- `README.md` — overview, folder map, setup, run options, retraining, troubleshooting.
- `reports/deployment_guidelines.md` — how the system fits a real network (SPAN port, passive-first, retraining cadence, concept-drift monitoring, limitations).
- `GLOSSARY.md` — every technical term in plain English.
- `reports/examiner_qa.md` — viva practice questions with model answers.
- `SETUP_GUIDE.md` — step-by-step setup on another PC.
- `docs/` — submission-ready copies + merged `PROJECT_REPORT_combined.md`.
- Added `python -m src.models.train` to `train.py` so retraining is one command.

---

# Appendix — Live model registry snapshot

| Dataset | Model | CV F1-macro | Test F1 | Latency (ms/row) | Train rows | Trained at |
|---|---|---:|---:|---:|---:|---|
| cicids | Decision Tree | 0.9908 | 0.9505 | 0.0003 | 62,422 | 2026-08-14 11:49:32 |
| cicids | Logistic Regression | 0.8755 | 0.8267 | 0.0003 | 62,422 | 2026-08-14 11:49:04 |
| cicids | Random Forest | 0.9765 | 0.9276 | 0.0052 | 62,422 | 2026-08-14 11:51:25 |
| cicids | XGBoost | 0.9848 | 0.9897 | 0.0047 | 62,422 | 2026-08-14 11:54:41 |
| nslkdd | Decision Tree | 0.8907 | 0.6170 | 0.0004 | 125,973 | 2026-08-14 11:41:31 |
| nslkdd | Logistic Regression | 0.7432 | 0.5572 | 0.0005 | 125,973 | 2026-08-14 11:41:06 |
| nslkdd | Random Forest | 0.9333 | 0.5384 | 0.0095 | 125,973 | 2026-08-14 11:44:56 |
| nslkdd | XGBoost | 0.9565 | 0.6086 | 0.0021 | 125,973 | 2026-08-14 11:47:57 |

*Rows come from `src/models/registry/models_metadata.json` (CV score, latency,
training rows, trained-at).*
