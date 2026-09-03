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
- [`reports/examiner_qa.md`](reports/examiner_qa.md) — viva practice Q&A with model answers
- [`reports/deployment_guidelines.md`](reports/deployment_guidelines.md) — how to integrate this into a real network/SOC
- [`GLOSSARY.md`](GLOSSARY.md) — every technical term explained in plain English
- [`notebooks/01_eda.ipynb`](notebooks/01_eda.ipynb) — the data at a glance




---



# Model Comparison Report

**Generated automatically by `src/models/evaluate.py` (Phase 4).**

All models were tuned with grid search + stratified 5-fold cross-validation
on the TRAINING set (Phase 3) and scored here on the untouched TEST set.
SMOTE was applied inside the cross-validation folds and never to test data.

## Headline results

| Metric (macro-averaged) | Meaning |
|---|---|
| Accuracy | share of connections classified correctly |
| Precision | of the alarms raised, the share that were real attacks |
| Recall | of the real attacks, the share that were caught |
| F1 | harmonic mean of precision & recall (single balance number) |
| AUC-ROC | chance (0.5) to perfect (1.0) ranking of attacks over normal |

## NSL-KDD (test set: 22,544 rows)

| Model | Accuracy | Precision | Recall | F1 | AUC-ROC | Latency (ms/row) |
|---|---|---|---|---|---|---|
| Logistic Regression | 0.7628 | 0.6707 | 0.6295 | 0.5572 | 0.9057 | 0.0008 |
| Decision Tree | 0.8163 | 0.7545 | 0.5836 | 0.6170 | 0.7672 | 0.0006 |
| Random Forest | 0.7488 | 0.7972 | 0.5081 | 0.5384 | 0.9489 | 0.0089 |
| XGBoost | 0.7782 | 0.8281 | 0.5653 | 0.6086 | 0.9491 | 0.0027 |


Best overall F1 on NSL-KDD: **Decision Tree** (0.6170).

### NSL-KDD — per-class recall (share of each true class caught)

| Class | Logistic Regression | Decision Tree | Random Forest | XGBoost |
|---|---|---|---|---|
| DoS | 0.810 | 0.900 | 0.760 | 0.820 |
| Normal | 0.923 | 0.962 | 0.973 | 0.973 |
| Probe | 0.727 | 0.688 | 0.592 | 0.626 |
| R2L | 0.134 | 0.234 | 0.111 | 0.154 |
| U2R | 0.552 | 0.134 | 0.104 | 0.254 |

## CICIDS2017 (test set: 15,606 rows)

| Model | Accuracy | Precision | Recall | F1 | AUC-ROC | Latency (ms/row) |
|---|---|---|---|---|---|---|
| Logistic Regression | 0.9549 | 0.8391 | 0.8622 | 0.8267 | 0.9784 | 0.0006 |
| Decision Tree | 0.9972 | 0.9951 | 0.9257 | 0.9505 | 0.9629 | 0.0004 |
| Random Forest | 0.9970 | 0.9925 | 0.8944 | 0.9276 | 0.9919 | 0.0063 |
| XGBoost | 0.9988 | 0.9974 | 0.9832 | 0.9897 | 1.0000 | 0.0067 |


Best overall F1 on CICIDS2017: **XGBoost** (0.9897).

### CICIDS2017 — per-class recall (share of each true class caught)

| Class | Logistic Regression | Decision Tree | Random Forest | XGBoost |
|---|---|---|---|---|
| Botnet | 0.985 | 0.995 | 1.000 | 0.998 |
| Brute Force | 0.995 | 1.000 | 1.000 | 1.000 |
| DDoS | 0.988 | 1.000 | 1.000 | 1.000 |
| DoS | 0.972 | 0.998 | 0.998 | 0.999 |
| Heartbleed | 0.500 | 0.500 | 0.500 | 1.000 |
| Infiltration | 0.571 | 0.857 | 0.571 | 0.857 |
| Normal | 0.831 | 0.992 | 0.991 | 0.998 |
| PortScan | 0.994 | 0.998 | 0.999 | 0.998 |
| Web Attack | 0.924 | 0.991 | 0.991 | 1.000 |

## Interpretation notes

* **Recall matters most.** A missed attack (false negative) is far more
  dangerous than a false alarm (false positive) — the attacker gets in.
  The recall column is therefore the "safety" column of this table.
* **Rare classes are the hard part.** Classes with only a handful of real
  rows in training (U2R in NSL-KDD, Heartbleed/Infiltration in CICIDS2017)
  are the hardest to detect.  SMOTE helps, but a model cannot learn from
  data it has almost never seen.
* **Latency.** Every model answers in well under a millisecond per row, so
  all four are fast enough to run on a live network link — the choice
  between them is accuracy vs. interpretability/complexity, not speed.

## Charts

Charts live in `reports/figures/` (and copies in `frontend/public/`):
`bar_metrics_<dataset>.png`, `roc_<dataset>.png`, `confusion_<dataset>.png`.




---



# Deployment Guidelines — AI-Based Cybersecurity Threat Detection

Where the models built in this project would sit in a real network, how to
operate and monitor them, and the trade-offs the evaluation results force us to
make. Written so a reader with no networking background can follow.

> Why this document exists: the literature (e.g. Berman et al. 2019;
> Mahdavifar & Ghorbani 2019) repeatedly notes that academic ML research rarely
> explains *how to deploy* a model. This section closes that gap for this
> project — it is one of the stated research contributions.

---

## 1. Where the detector sits in the network

A machine-learning model cannot watch a network by itself; it classifies rows
of numbers that describe traffic. Those rows have to come from somewhere.

Recommended placement for a first deployment — **passive, on a mirror port**:

```
             ┌─────────────────────────── Internet / LAN ───────────────────────────┐
             │                                                                       │
   switches/router  ──SPAN/mirror port──►  Packet collector (e.g. tcpdump / Zeek)     │
                                                    │                                │
                                                    │ flow/packet features           │
                                                    ▼                                │
                                        Feature extractor  →  our Preprocessor       │
                                                                  │                   │
                                                                  ▼                   │
                                                       Trained model (XGBoost)       │
                                                                  │                   │
                                                                  ▼                   │
                                                          SOC alert queue            │
                                                                  │                   │
                                             ┌────────────────────┴─────────────────┐│
                                             │  Analyst investigates & closes/sups  ││
                                             └──────────────────────────────────────┘│
             └───────────────────────────────────────────────────────────────────────┘
```

Key principle: **start passive, act inline later.** A mirror/SPAN port gets a
*copy* of every packet without touching the traffic itself. If the model makes
mistakes, nothing is blocked. Only after the false-positive rate is judged
acceptable should the detector be given an action (drop, rate-limit) — and
that decision belongs to a human SOC analyst.

Alternatives worth knowing:

| Placement | Pros | Cons |
|---|---|---|
| **SPAN/mirror port (recommended)** | zero risk to live traffic; simple | misses traffic between switches unless mirrored properly; mirror ports drop packets under load |
| **Network TAP** | no drop under load, higher fidelity | needs hardware, an outage window to insert |
| **Inline (between router and LAN)** | can actively block | a bug or false positive can take the whole network down — never the first step |
| **Host-based agent** | sees per-machine detail | deployment cost on every endpoint |

---

## 2. Architecture in production

Whatever the transport, the *prediction pipeline* must be identical to training
or results silently degrade:

```
raw packet/flow  →  feature extraction (78 CICIDS-style features)
                →  PREPROCESSOR (same one saved in data/processed!)
                     • replace Inf with NaN
                     • median imputation
                     • min-max scaling to [0,1]
                     • one-hot encoding of categoricals (NSL-KDD path)
                →  XGBoost.predict_proba()
                →  threshold  →  alert / no-alert  +  class label
```

The single most common production failure is **feature drift at the boundary**:
training and inference preprocessors diverge (different scaling, a new category
one-hot dropped, a NaN left in). In this repo the fix is structural — the API
(`src/api/main.py`) loads the *saved* preprocessor, never re-fits one, and the
`/predict` endpoint transforms incoming rows with it.

**Pick your model from the evaluation, not the leaderboard reflex:**

| Goal | Choice | Why (from `reports/model_comparison_report.md`) |
|---|---|---|
| Highest detection accuracy, modern data | **XGBoost** | CICIDS2017 F1 **0.990**, accuracy 0.9988, AUC 1.0000, yet ~0.002–0.01 ms/row |
| Explainability (audit/compliance) | **Decision Tree** | F1 0.950 on CICIDS; every decision is a readable yes/no tree |
| Baseline / very fast prototype | Logistic Regression | 0.827 F1 on CICIDS — fine for a first pass, weak on NSL-KDD rare classes (R2L recall 0.11–0.23) |

For NSL-KDD (older, harder distribution) the best F1 is Decision Tree (0.617) —
XGBoost trails slightly (0.609) but has the highest AUC (0.949). Recommendation:
**run XGBoost for detection, keep a Decision Tree alongside for explanations.**

---

## 3. Accuracy vs. latency — what the numbers say

Measured on this machine (16 cores, Python 3.12):

| Dataset   | Model          | CV F1 (train) | Test F1 | Test accuracy | Inference |
|-----------|----------------|--------------:|--------:|--------------:|----------:|
| NSL-KDD   | Logistic       | 0.743         | 0.557   | 0.763         | ~0.006 ms/row |
| NSL-KDD   | Decision Tree  | 0.891         | **0.617** | 0.779       | ~0.0003 ms/row |
| NSL-KDD   | Random Forest  | 0.933         | 0.538   | 0.787         | ~0.002 ms/row |
| NSL-KDD   | XGBoost        | 0.956         | 0.609   | 0.799         | ~0.004 ms/row |
| CICIDS2017| Logistic       | 0.876         | 0.827   | 0.985         | ~0.01 ms/row |
| CICIDS2017| Decision Tree  | 0.991         | 0.950   | 0.997         | ~0.0003 ms/row |
| CICIDS2017| Random Forest  | 0.976         | 0.928   | 0.998         | ~0.009 ms/row |
| CICIDS2017| **XGBoost**    | 0.985         | **0.990** | 0.9988     | ~0.002 ms/row |

Interpretation for a deployer:

1. **Latency is not the bottleneck.** Even the slowest model classifies a row
   in ~0.01 ms — orders of magnitude below what a 10 Gbps link produces per
   row. The real bottleneck is *feature extraction* (outside this project's
   scope but standard tooling exists: Zeek/Suricata flow exporters).
2. **Accuracy on NSL-KDD drops sharply from train to test** (XGBoost 0.956 →
   0.609). This is expected: the official NSL-KDD *test* set deliberately
   contains attack variants the training set never showed, and the R2L/U2R
   classes are tiny. It is a feature of the benchmark, not a bug in the models
   — but it means **evaluate on your own live traffic, not just on a benchmark
   test set, before trusting any number.**
3. **Decision Tree is the cheap-and-interpretable option**; XGBoost is the
   best *default*. There is no case here where a bigger model buys accuracy at
   a cost you can feel.

---

## 4. Retraining cadence

Threats evolve; a model frozen at graduation will rot. Two triggers:

**Scheduled retraining.** Monthly or quarterly, whichever the SOC can staff.
Retraining here is a one-liner — `python -m src.models.train` (or notebooks
01–04) — but in production you would retrain on *newly labelled* traffic, not
the same 2017 benchmark. Keep the discipline from Phase 2: split before
preprocessing, **SMOTE only inside the CV folds**, and never touch the test
split while tuning (data leakage is the classic reason a deployed model under-
performs its paper).

**Triggered retraining (concept drift).** Retrain sooner when the model's
live predictions start to look different from training:

- PSI (Population Stability Index) on `predict_proba()` > 0.25 between a
  baseline distribution and a recent 7-day window → the input distribution has
  shifted;
- alert rate more than ±30% from its 30-day rolling baseline for two
  consecutive weeks;
- any new attack family observed in the SOC queue (add it to the training
  labels and retrain).

See §5 for how to monitor these numbers.

---

## 5. Monitoring in production

Run the model, then **monitor the monitor**:

| Signal | What to watch | Action if abnormal |
|---|---|---|
| Input features | min/max drift, new categorical values, NaN/Inf injection | alert: feature extractor bug or a genuinely new traffic pattern |
| `predict_proba` distribution | PSI against baseline (see §4) | investigate traffic change; schedule retraining |
| Alert rate | sharp rise/fall vs. 30-day baseline | false-positive storm (tune threshold down / retrain) or missed attacks (tune threshold up) |
| Ground truth | sample of alerts checked by an analyst (1-in-N), track precision/recall over time | feed corrections back into the next training set — the feedback loop is what keeps the model relevant |
| Model performance vs. test set | re-run `evaluate.py` on a rolling labelled window | below targets → retrain |

The `/predict` endpoint returns per-class probabilities, which is exactly the
raw material these monitors need: log them, don't just log the label.

**Threshold tuning.** The default is `argmax` (always pick the most-likely
class). For an *alerting* system, raise the decision threshold on "attack"
above 0.5 to trade recall for fewer false positives — or lower it if the SOC
prefers catching everything. A precision-recall curve (plot in
`reports/figures/`) shows the options. No fixed number is right; it depends on
how much noise your SOC can absorb.

---

## 6. Data-quality traps this project already solved

These are exactly the traps Thakkar & Lohiya (2021) warn about, and they were
found live during Phase 2:

- **Corrupted labels in CICIDS2017:** the label column contains a broken
  Unicode character (`�`) in "Web Attack"; the loader fixes it before mapping
  to categories, otherwise a whole attack class silently disappears.
- **Infinite values:** CICIDS2017 contains `Infinity` cells (mostly in bulk
  features) — replaced with NaN then median-imputed.
- **Zero-variance features:** eight columns (e.g. `bwd_psh_flags`, the `*_bulk`
  rate fields) are constant in the training data and give a model nothing;
  feature selection drops them.
- **Class imbalance:** Heartbleed has 11 rows in the entire dataset, R2L/U2R
  are ~1% of NSL-KDD. Left unbalanced, the models would learn "predict
  Normal". SMOTE balances training only, inside the CV folds.
- **Difficulty-score leakage (NSL-KDD):** the raw file includes a "difficulty"
  column that is metadata, not traffic — dropped at load, or the model would
  cheat by memorising it.

Any deployment feeding this project new data must apply the same rules.

---

## 7. Operational checklist (deploying this prototype)

1. [ ] Run on a **mirror/SPAN port**, passive, with analyst review of all alerts.
2. [ ] Wire the feature extractor to output the same 78 CICIDS (or 41 NSL-KDD) feature names.
3. [ ] Reuse the saved `cicids_preprocessor.joblib` / `nslkdd_preprocessor.joblib` — never re-fit.
4. [ ] Serve with the FastAPI app: `uvicorn src.api.main:app --workers 1`; put nginx/a reverse proxy in front for TLS.
5. [ ] Log `predict_proba` per row (not just the label) to feed PSI monitoring.
6. [ ] Set a decision threshold with the SOC, using the precision-recall curve.
7. [ ] Schedule retraining (quarterly minimum) + a PSI-based drift trigger.
8. [ ] Keep a Decision Tree model for explainability on every alert.
9. [ ] Re-run `pytest tests\test_api.py` after any retrain to confirm the API still loads the registry.
10. [ ] Document model version + data version in the alert metadata (the `*_meta.json`
    files already record trained-at timestamps and best hyperparameters).

---

## 8. Known limitations & future work

- **Benchmark age:** CICIDS2017 (2017) and NSL-KDD (2009) are old; modern
  traffic looks different. Future work: evaluate on CICIDS2019 or the more
  recent NF-UNSW datasets, and re-run the whole pipeline.
- **No TLS/encrypted-traffic features.** Many current attacks live inside
  encrypted tunnels; the flow features here would need extending.
- **Cross-dataset robustness** (a stated research gap) is only partially
  addressed — each model is trained and tested *within* its own dataset. A
  trained-on-CICIDS model tested on NSL-KDD would likely degrade; mapping the
  two feature spaces is future work.
- **No streaming/latency envelope.** Inference is fast, but the feature-
  extractor latency wasn't measured; end-to-end SLO requires that measurement.
- **Feedback loop is manual.** Automating "analyst corrections → next training
  set" is the natural next step.

## 9. References cited

- Berman, D. S., Buczak, A. L., Chavis, J. S., & Corbett, C. L. (2019). A survey of deep learning methods for cyber security. *Information, 10*(4), 122.
- Gao, X., Shan, C., Hu, C., Niu, Z., & Liu, Z. (2019). An adaptive ensemble machine learning model for intrusion detection. *IEEE Access, 7*, 82512–82521.
- Thakkar, A., & Lohiya, R. (2021). A review of the advancement in intrusion detection datasets. *Procedia Computer Science, 167*, 636–645.
- Mahdavifar, S., & Ghorbani, A. A. (2019). Application of deep learning to cybersecurity: A survey. *Neurocomputing, 347*, 149–176.
- Ramu, A. (2025). Machine learning for cyber threat detection using historical vulnerabilities and security standards. *Journal of Computer and Communication Networks, 4*(1), 1–15.




---



# GLOSSARY

Plain-language definitions of every technical term used in this project.
Organised by theme; each entry is one or two sentences so the thesis can be
read without a dictionary.

> Linked from the README. If you meet a term that is missing here, add it —
> a glossary is only useful if it stays complete.

## Machine learning basics

- **Machine learning (ML):** a program that *learns patterns from example data*
  instead of following rules a human wrote by hand. Given many labelled
  network flows, it works out what malicious traffic "looks like".
- **Supervised learning:** training where every example already has the correct
  answer (label). "Here are 1,000 flows and which are attacks; learn the
  difference." This project is entirely supervised.
- **Classification:** a supervised task where the answer is a *category*.
  Here: "Normal", "DoS", "Probe", … (multiclass classification).
- **Feature:** one measurable property of an example used as input — a column
  in the data, e.g. packet length, flow duration, number of bytes sent.
- **Label:** the correct answer attached to an example — the attack type
  (or "Normal") a flow really is.
- **Class:** one of the categories a label can take. NSL-KDD has five classes
  (Normal, DoS, Probe, R2L, U2R); CICIDS2017 has nine.
- **Training set / test set:** the data is split in two. The model only ever
  *sees* the training set while learning; the test set is kept as a surprise
  "exam" to measure whether it generalises. Never tune on the test set.
- **Overfitting:** the model memorises the training data instead of learning
  the underlying pattern — great scores in training, poor scores on new data.
- **Underfitting:** the model is too simple to capture the pattern at all —
  poor scores everywhere.
- **Generalisation:** the ability to perform well on data the model has never
  seen. The whole point of the test set.
- **Hyperparameter:** a "dial" set *before* training (how deep may a tree grow?
  how many trees? how strong the regularisation?). Contrast with the parameters
  the model learns from data.
- **Grid search:** try every combination of hyperparameter values and keep the
  one with the best cross-validation score.
- **k-fold cross-validation:** split the training data into k chunks (folds);
  train on k−1, score on the remaining one, repeat k times so every chunk gets
  its turn as the "holdout". Gives a more honest score than one single split.
- **Stratified:** folds are made so each one has the *same class proportions*
  as the full data — important when classes are rare, so one fold doesn't end
  up with zero attacks.
- **Class imbalance:** when one class is vastly more common than others (e.g.
  99% normal traffic, 1% attacks). Naive models then learn "always say Normal"
  and look 99% accurate while detecting nothing.
- **SMOTE (Synthetic Minority Over-sampling Technique):** creates *synthetic*
  examples of rare classes by interpolating between neighbouring real ones, so
  the model gets enough examples of rare attacks to learn them. Only applied
  to the training set, never the test set.
- **Data leakage:** information from the test set (or the future) reaching the
  model during training, making results look better than they are. Classic
  examples: preprocessing fitted on the whole dataset, or SMOTE applied before
  splitting. This project avoids leakage deliberately.
- **Imputation:** filling in missing values. Median imputation replaces a
  missing cell with the median of its column — a robust default.
- **Min-max scaling:** rescaling every numeric feature into the range [0,1] by
  subtracting the minimum and dividing by the range. Some algorithms need it.
- **One-hot encoding:** turning a text/categorical feature (e.g. protocol =
  tcp/udp/icmp) into separate 0/1 columns, one per value, because models can't
  use text directly.
- **Categorical vs. numerical feature:** categorical = a small set of named
  values (protocol, service, flag); numerical = a measured quantity (bytes,
  seconds, packets).
- **Zero-variance feature:** a column whose value never changes in the data.
  It carries no information and can be dropped.
- **Correlation (Pearson):** a number in [−1, 1] measuring how two numeric
  features move together linearly. Used to find near-duplicate features.
- **Mutual information:** how much knowing one feature reduces uncertainty
  about the label. Unlike correlation it catches *non-linear* relationships —
  a feature selection method.
- **RFE (Recursive Feature Elimination):** repeatedly trains a model, ranks
  features by importance, removes the weakest, and repeats — a third way to
  choose features.
- **Feature selection:** picking the most informative subset of features to
  reduce noise, speed up training, and improve generalisation. This project
  compares three methods (correlation, mutual information, RFE).
- **Preprocessor:** the fixed pipeline (impute → scale → one-hot) fitted on
  training data and reused on test/inference data. The API loads the *saved*
  preprocessor so a live packet is transformed exactly like training data.

## The algorithms

- **Logistic Regression:** a linear classifier: it learns a set of weights and
  outputs probabilities for each class. Fast and simple, but struggles with
  complex, non-linear attack patterns.
- **Decision Tree:** a model that asks a sequence of yes/no questions
  ("packet length > 800? then …"). Perfectly explainable — every prediction is
  a readable path — but a single tree can overfit.
- **Random Forest:** an *ensemble* of many decision trees, each trained on a
  random slice of the data; the trees vote. Averaging many trees reduces
  overfitting and usually beats a single tree.
- **XGBoost (eXtreme Gradient Boosting):** an ensemble that trains trees *in
  sequence*, each one correcting the mistakes of the previous. Consistently the
  strongest classifier in this project (0.990 F1 on CICIDS2017).
- **Bagging vs. boosting:** bagging (Random Forest) trains trees independently
  and averages; boosting (XGBoost) trains them dependently, each fixing the
  last one's errors. Two different ways to combine weak models into a strong one.
- **Ensemble:** combining many models. Both Random Forest and XGBoost are
  ensembles.
- **Baseline:** the simplest reasonable model to compare everything against.
  Here, Logistic Regression plays that role.

## Metrics (how we judge the models)

- **Confusion matrix:** a table of predictions vs. reality: TP (attack called
  attack), FP (normal called attack — a false alarm), TN (normal called
  normal), FN (attack called normal — a miss).
- **Accuracy:** (TP+TN) ÷ all. Misleading with imbalanced data — a model that
  only says "Normal" is 80%+ "accurate" while detecting nothing.
- **Precision:** of everything the model flagged as an attack, what fraction
  really was one. High precision = few false alarms.
- **Recall (sensitivity):** of all real attacks, what fraction were caught.
  High recall = few missed attacks.
- **F1 score:** the harmonic mean of precision and recall — one number that
  balances them. F1-macro averages F1 across classes so rare classes weigh the
  same as common ones.
- **ROC curve & AUC:** ROC plots recall vs. false-alarm rate at every decision
  threshold; AUC (Area Under the Curve) summarises how well the model *ranks*
  attacks above normal. 1.0 = perfect ranking, 0.5 = random guessing.
- **Latency:** time to classify one row. This project measures it in
  milliseconds per row and reports the accuracy-vs-latency trade-off.
- **False positive / false negative:** a false alarm / a missed attack. Which
  is worse depends on the SOC: FPs waste analyst time, FNs let attacks through.

## Datasets & attacks

- **NSL-KDD:** a cleaned 2009 benchmark derived from the KDD Cup '99 dataset
  (simulated Air Force network traffic). ~126k training rows, 41 features, five
  classes. Its test set deliberately includes attack *variants* the training
  set never showed — hence the train-to-test score drop.
- **CICIDS2017:** a 2017 benchmark built at the Canadian Institute for
  Cybersecurity from real captured traffic, ~2.8M rows, 78 features, nine
  classes. Modern, realistic, but very imbalanced (Heartbleed has 11 rows!).
- **DoS / DDoS:** Denial-of-Service / Distributed DoS — overwhelming a target
  with traffic until it can't serve real users.
- **Probe (port scan):** reconnaissance — systematically scanning ports to map
  a target's weaknesses before the real attack.
- **R2L (Remote-to-Local):** attacker without an account gains local access to
  a machine, e.g. by guessing a password or exploiting a service.
- **U2R (User-to-Root):** a legitimate local user escalates to root/admin
  privileges. Very rare in NSL-KDD (52 training rows).
- **Brute Force:** trying many password/credential combinations until one works.
- **Web Attack:** exploiting a web app — SQL injection, XSS, or brute-forcing
  its login.
- **Botnet:** a network of compromised machines ("bots") remotely controlled,
  often used to launch DDoS attacks.
- **Infiltration:** an attacker who slipped inside through a legitimate channel
  (e.g. a planted file) and is now moving around the internal network.
- **Heartbleed:** exploitation of a 2014 OpenSSL bug that let attackers read
  memory they shouldn't. Nearly absent from CICIDS2017 — a hard class.
- **Signature-based detection:** matching traffic against a database of known
  attack "fingerprints". Excellent for known attacks, blind to new ones.
- **Anomaly detection:** flagging traffic that looks statistically unusual.
  This is where ML shines and where this project's models operate.
- **Zero-day attack:** an attack on a vulnerability nobody knows about yet — no
  signature exists, so only behaviour/anomaly detection can catch it.
- **APT (Advanced Persistent Threat):** a sophisticated attacker who quietly
  lives in a network for months, moving laterally, rather than attacking loudly.
- **Polymorphic malware:** malware that changes its code/signature with every
  copy — defeats signature databases, motivating the ML approach.
- **SPAN/mirror port:** a switch setting that copies every packet to a second
  port for passive monitoring — how a detector watches traffic without
  touching it.
- **SOC (Security Operations Center):** the team/room that watches alerts and
  responds to incidents. The end consumer of this project's output.

## Operations & tooling

- **Concept drift:** the data's statistical pattern changes over time (new
  attacks, new traffic patterns), so a trained model's accuracy silently
  decays. Requires monitoring and retraining.
- **PSI (Population Stability Index):** a number measuring how much a
  distribution (here, of model probabilities) has shifted from a baseline.
  Used to detect concept drift.
- **Model monitoring:** watching the model's inputs, outputs, alert rate and
  ground truth over time — the operational counterpart of training.
- **Threshold:** the probability cutoff above which we call a flow an attack.
  Tuning it trades recall for precision.
- **FastAPI:** a Python web framework for building APIs. Here it serves the
  trained models behind REST endpoints (with automatic `/docs`).
- **REST / API:** a standard way for programs to talk over HTTP; the frontend
  asks the backend `POST /predict` and gets back a JSON answer.
- **CORS (Cross-Origin Resource Sharing):** browser security rules that decide
  whether a page served from one origin may call an API from another. The API
  allows it so the dev server and the dashboard can talk.
- **Uvicorn:** the Python server that runs the FastAPI app.
- **Vite:** the fast build tool / dev server used by the React frontend.
- **React:** the JavaScript library used to build the dashboard UI.
- **Recharts:** the charting library behind the comparison charts.
- **Jupyter notebook:** an interactive document mixing code, text and charts —
  used for EDA and each pipeline stage (notebooks 01–04).
- **Joblib:** the library that saves/loads trained models as `.joblib` files.
- **Pandas / NumPy:** the table and array libraries everything is built on.
- **scikit-learn:** the main ML library (LR, DT, RF, grid search, metrics).
- **xgboost:** the library implementing the XGBoost algorithm.
- **imbalanced-learn:** the library providing SMOTE.
- **EDA (Exploratory Data Analysis):** the first look at the data — shapes,
  class counts, missing values, distributions — before any modelling.
- **Pipeline:** the ordered chain of steps (SMOTE → classifier) applied
  together. Wrapping them in one object prevents leakage and keeps train/serve
  behaviour identical.
- **Registry:** the folder of saved models + metadata the API loads at startup.
- **Inference / prediction:** running a trained model on new data to get an
  answer (the deployment-time step).
- **Reproducibility:** the property that the same steps produce the same
  numbers every run — achieved here by a fixed random seed (42), pinned package
  versions, and one-command retraining.




---



# Examiner Q&A Bank

A practice set of the questions most likely to come up in a project viva, with
short model answers built from the *actual* numbers and decisions in this repo.
Do not read these word-for-word in the viva — use them as anchors and then
speak naturally.

---

## 1. Why did you pick those four algorithms?

"Logistic Regression as the fast, simple baseline; Decision Tree for
explainability — you can literally read its decisions; Random Forest and
XGBoost as the two ensemble methods, which are consistently the strongest in
the intrusion-detection literature (Gao et al. 2019 for ensembles, Ramu 2025
for XGBoost). That gives the comparison a spread from simple/interpretable to
complex/accurate, which is exactly the trade-off I wanted to measure."

## 2. Why NSL-KDD and CICIDS2017, and what's the difference?

"NSL-KDD is the cleaned version of the classic KDD Cup '99 data — it removed
the duplicate rows that made the original unmeasurable, and it's the de-facto
benchmark for IDS research. CICIDS2017 is much more modern — real captured
traffic from 2017, 78 features instead of 41, and attacks that look like
today's (brute force, web attacks, botnet). So NSL-KDD tests the classic
benchmark, CICIDS2017 tests realism. Both are publicly available and
anonymised, which also kept the ethics approval simple."

## 3. How did you handle class imbalance?

"Two complementary steps. In data loading, I used a *capped* load for
CICIDS2017 — keeping every rare-class row (Heartbleed has 11 rows in the whole
dataset!) but randomly capping the huge classes like BENIGN at 15,000. Then,
inside model training, SMOTE synthesises extra examples of the rare classes.
Critically, SMOTE is fitted *inside the cross-validation folds*, only on the
training portion of each fold, so no synthetic row can leak into a validation
fold. And I scored tuning with f1-macro, so rare classes weigh the same as
normal traffic."

## 4. What is data leakage, and how did you prevent it?

"Leakage is when information from the test set — or the future — reaches the
model during training, making results look better than they really are. I
prevented it in three places: preprocessors (median imputation, scaling,
one-hot) are fitted on the training split *only* and then just applied to the
test set; SMOTE is applied inside CV folds, never before the split; and for
NSL-KDD I dropped the 'difficulty' column at load time because it's metadata,
not traffic — the model would have cheated by memorising 'hard rows are
attacks'."

## 5. Explain SMOTE in one sentence for a non-technical person.

"SMOTE creates new, slightly-varied copies of the rare attack examples so the
model sees enough of them to actually learn the pattern, instead of being
drowned out by millions of normal rows."

## 6. Why is your NSL-KDD test score much lower than training?

"That's expected and it's a feature of the benchmark. The official NSL-KDD
test set deliberately contains attack *variants* the training set never
showed — the point is to test robustness to unseen attacks, which is the whole
motivation for the project. XGBoost drops from 0.956 cross-validation f1 to
0.609 test f1, and the rare R2L class recalls only 0.11–0.23. This is the
honest measure of how well the model generalises to new attacks — and it's why
I report test results, not just training scores."

## 7. What does the accuracy vs. latency trade-off look like in your results?

"On CICIDS2017, XGBoost gets 0.990 F1 at about 0.002 ms per row — so in this
project the best model is also fast enough for live traffic. The interesting
finding is that latency isn't the bottleneck here at all: every model is under
~0.01 ms/row. The real cost sits outside the model, in feature extraction. The
Decision Tree is fastest and fully explainable but slightly weaker; Logistic
Regression is the weakest. So the trade-off that matters is accuracy vs.
explainability more than accuracy vs. speed."

## 8. Which model would you actually deploy, and why?

"XGBoost for detection — best accuracy on both datasets and microseconds per
row. But I'd keep a Decision Tree running alongside purely for explainability:
when an alert fires, the analyst can read the tree's path to understand *why*.
Logistic Regression would only be a prototype baseline."

## 9. How does a model like this get deployed in a real network?

"Passively, on a SPAN or mirror port — the switch copies traffic to a port
without touching live traffic. A flow/feature extractor turns packets into the
same 78 features the model was trained on; the saved preprocessor transforms
them identically; the model returns probabilities; a threshold decides whether
an alert goes to the SOC queue. Passive-first means a model mistake can't take
the network down. Inline blocking only comes later, after the false-positive
rate has been judged acceptable."

## 10. How would you detect and respond to concept drift?

"Monitor the model's probability outputs: PSI (Population Stability Index)
compares the current distribution of probabilities against a baseline; if it
crosses ~0.25, the input distribution has shifted. Also watch the alert rate
against a rolling 30-day baseline and any new attack family in the SOC queue.
Response: schedule retraining — quarterly minimum — and trigger retraining
early when drift is detected. Retraining here is a single command,
`python -m src.models.train`."

## 11. Why f1-macro rather than accuracy?

"Accuracy is meaningless with imbalanced data. CICIDS2017 is ~80% normal
traffic; a model that always says 'Normal' is ~80% accurate while detecting
nothing. F1-macro averages F1 over all classes equally, so detecting 11
Heartbleed rows counts the same as classifying a million normal rows. The
tuner is forced to care about rare attacks."

## 12. How did you choose the features?

"I compared three methods — Pearson correlation, mutual information, and
recursive feature elimination — each ranking the features independently, and
took the union/agreement. Mutual information matters because it catches
non-linear relationships that correlation misses. This agreed with the domain:
packet/flow sizes like average_packet_size and packet_length_mean dominate
CICIDS2017, and src_bytes dominates NSL-KDD. Feature selection was done on the
pre-SMOTE training data only, to keep it honest."

## 13. What are the limitations of your work?

"First, both datasets are old — CICIDS is 2017, NSL-KDD is 2009 — so modern
traffic looks different. Second, cross-dataset robustness is only partially
addressed: each model is trained and tested within its own dataset; mapping
the two feature spaces so one model works on both is future work. Third, the
features don't cover encrypted traffic, where many attacks now hide. And the
evaluation measures per-row latency, not the full feature-extraction-to-alert
pipeline."

## 14. Why is CICIDS2017 so much 'easier' than NSL-KDD for these models?

"CICIDS2017's test distribution closely matches its training distribution, so
a well-trained model hits ~0.99 F1. NSL-KDD's test set is adversarial — unseen
attack variants — so 0.61 is the realistic, honest number. The datasets
therefore measure two different things: how well the model fits its own data,
and how well it survives novelty. Both are worth reporting, and the gap itself
is the research finding about benchmark design."

## 15. How do you know your results are reproducible?

"Fixed random seed (42) everywhere — splits, SMOTE, model initialisation;
pinned package versions in requirements.txt; the full pipeline is either
notebooks 01–04 or the one-command `python -m src.models.train`, which
reloads raw data, rebuilds the preprocessed splits, re-tunes every model and
refreshes the registry. The preprocessors and label encoders are saved, so
inference is forced to match training."

## 16. What did the ethics form have to cover?

"This project uses only public, anonymised, labelled datasets — no human
participants, no personal data, no offensive capability. The ethics form
(UREC1-style, in Finalds.md) documents that: secondary data in the public
domain, defensive detection only, and research data handled according to
university policy. The deployment guidelines repeat the same boundary — a
passive detector with human SOC review, never an inline blocker as a first
step."

## 17. What would you do differently with more time?

"Retrain and evaluate on a newer benchmark (e.g. NF-UNSW or CICIDS2019), build
the cross-dataset transfer test I describe as a limitation, add feature
extraction so the pipeline ingests raw packets end-to-end rather than starting
at pre-extracted features, and automate the analyst-feedback → retraining
loop."

## 18. Walk me through the architecture of the final deliverable.

"Notebooks 01–04 are the research pipeline: EDA, preprocessing + feature
selection, training/tuning, evaluation. The artifacts — processed splits,
preprocessors, label encoders, the 8 trained models and their metadata — live
in data/processed and src/models/registry. A FastAPI backend (`src/api`)
loads those artifacts and exposes /models, /compare, /attack-info,
/predict and /simulate. A React + Vite dashboard polls /simulate to display
live-looking classifications, compare charts, and an attack library. The
backend serves the built frontend from /, so one uvicorn process runs the whole
demo. 14 API tests cover every endpoint."

