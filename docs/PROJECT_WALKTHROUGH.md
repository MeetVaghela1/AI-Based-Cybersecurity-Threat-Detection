# Project Walkthrough — From Datasets to Dashboard

A plain-language tour of the whole project, start to finish: what every piece
does, how the data flows through it, how the models work, and exactly what you
are looking at on the dashboard — so a non-technical reader can follow a single
packet from raw dataset row to the screen.

> **Tables with numbers** are auto-generated from
> `data/processed/evaluation_results.json` and
> `src/models/registry/models_metadata.json`. Keep them fresh after retraining:
>
> ```
> .venv\Scripts\python.exe -m src.utils.generate_docs
> ```

---

## 1. The big picture

The project is a **traffic-classification system**. It takes network
connections, decides whether each one is normal or an attack (and which
attack), and shows those decisions on a live-looking dashboard.

Everything hangs together in one flow:

```
dataset files  →  cleaning  →  features  →  train models  →  save models
     ↑                                                          ↓
   NSL-KDD                                          FastAPI backend
   CICIDS2017                                             ↓
                                                React dashboard
                                          (live monitor, charts, explainers)
```

The roles:

| Piece | Where it lives | What it does |
|---|---|---|
| **Datasets** | `data/raw/` | the "textbook" each model learns from |
| **Cleaning + features** | `src/data/` | turns messy files into clean numeric tables |
| **Training** | `src/models/`, notebooks 01–04 | builds and tunes 8 models (4 algorithms × 2 datasets) |
| **Model registry** | `src/models/registry/` | the finished models, saved to disk |
| **Backend** | `src/api/` | loads the models and answers questions over HTTP |
| **Dashboard** | `frontend/` | the visual interface the user clicks |

---

## 2. The datasets — what they are and how they work in the project

A machine-learning model learns from **examples**. Each example is one network
connection described by numbers, plus a label saying what it really was. The
two datasets provide those examples.

### NSL-KDD (2009)
- The classic academic benchmark, derived from the old KDD Cup '99 data.
- **41 features** per connection (packet length, protocol, bytes sent, …).
- **5 classes:** Normal, DoS, Probe, R2L, U2R.
- Train file: 125,973 rows · Test file: 22,544 rows.
- Famous catch: its **test set deliberately contains attack variants never seen
  in training** — so scores drop there on purpose. That drop is the project's
  honest measure of "can the model catch something new?"

### CICIDS2017 (2017)
- Modern, realistic traffic captured at the Canadian Institute for
  Cybersecurity.
- **78 features** per connection (flow durations, packet-size statistics, …).
- **9 classes:** Normal, Botnet, Brute Force, DDoS, DoS, Heartbleed,
  Infiltration, PortScan, Web Attack.
- ~2.8M rows in the raw files, heavily imbalanced (Heartbleed has just 11 rows
  in the whole dataset).

### How the project makes them comparable
Both are converted into one **common schema** — every row carries
`source`, `is_attack`, `attack_category`, `attack_type` — so the same code
pipeline and the same dashboard handle both. The choice of these two datasets
(and why alternatives were rejected) is justified in
`reports/dataset_selection_justification.md`.

---

## 3. How the data is prepared (the pipeline)

Raw files are never fed to a model directly. The pipeline
(`src/data/loader.py` + `src/data/preprocess.py`) makes them learnable:

1. **Load & clean**
   - NSL-KDD: the file's "difficulty" column is metadata, not traffic — dropped
     so the model can't cheat.
   - CICIDS2017: corrupt labels fixed (a broken character in "Web Attack"),
     `Infinity` cells converted to missing, constant ("zero-variance") columns
     dropped.
   - CICIDS2017 is so skewed that the loader **caps** big classes at 15,000
     rows while keeping every rare-class row (62,422 rows total).
2. **Preprocess** (fitted on training data only)
   - missing values → median imputation
   - every number → scaled to [0, 1]
   - NSL-KDD text features → one-hot encoded (41 → 122 columns)
3. **Label-encode** the attack names into numbers (and save the encoder so
   predictions can be decoded back to names).
4. **Balance with SMOTE** (training only): creates synthetic examples of rare
   classes so the model actually learns them — NSL-KDD trains grow to 154,926
   rows; CICIDS2017 grows to 108,000 (all 9 classes equal).
5. **Feature selection:** three methods (Pearson correlation, mutual
   information, RFE) rank which features matter most. Big winners: `src_bytes`
   (NSL-KDD), `average_packet_size` / `packet_length_mean` (CICIDS2017).

**The no-leakage rule** (why the numbers are honest): preprocessing and SMOTE
are fitted on the training split only; SMOTE happens *inside* the
cross-validation folds; the test set is never touched until the very end.

---

## 4. The models — what each one does

Four algorithms are compared on both datasets (8 trained models):

- **Logistic Regression** — the simple baseline. Learns straight-line
  boundaries between classes. Fast, explainable, but limited.
- **Decision Tree** — a chain of yes/no questions ("is packet length > 800?").
  Every prediction is a readable path.
- **Random Forest** — a crowd of many decision trees that vote. Robust and
  accurate.
- **XGBoost** — a sequence of trees where each one corrects the previous one's
  mistakes. The accuracy leader.

Training tunes each one with **grid search + stratified 5-fold cross-validation**
and scores them with **f1-macro** (so rare attacks count as much as normal
traffic), with SMOTE inside the folds.

### Cross-validation scores (how they looked while tuning)

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

### How they did on the unseen test data

**NSL-KDD test set (22,544 rows)**

| Model | Accuracy | Precision | Recall | F1 | AUC-ROC | Latency (ms/row) |
|---|---|---|---|---|---|---:|
| Logistic Regression | 0.7628 | 0.6707 | 0.6295 | 0.5572 | 0.9057 | 0.0008 |
| Decision Tree | 0.8163 | 0.7545 | 0.5836 | 0.6170 | 0.7672 | 0.0006 |
| Random Forest | 0.7488 | 0.7972 | 0.5081 | 0.5384 | 0.9489 | 0.0089 |
| XGBoost | 0.7782 | 0.8281 | 0.5653 | 0.6086 | 0.9491 | 0.0027 |

Best overall F1 on NSL-KDD test: **Decision Tree (0.6170)**.

Per-class recall (of all real attacks of each type, how many were caught):

| Class | Logistic Regression | Decision Tree | Random Forest | XGBoost |
|---|---|---|---|---|---|---|---|
| DoS | 0.8105 | 0.9005 | 0.7604 | 0.8202 |
| Normal | 0.9233 | 0.9616 | 0.9730 | 0.9731 |
| Probe | 0.7270 | 0.6877 | 0.5915 | 0.6258 |
| R2L | 0.1344 | 0.2338 | 0.1112 | 0.1538 |
| U2R | 0.5522 | 0.1343 | 0.1045 | 0.2537 |

**CICIDS2017 test set (15,606 rows)**

| Model | Accuracy | Precision | Recall | F1 | AUC-ROC | Latency (ms/row) |
|---|---|---|---|---|---|---:|
| Logistic Regression | 0.9549 | 0.8391 | 0.8622 | 0.8267 | 0.9784 | 0.0006 |
| Decision Tree | 0.9972 | 0.9951 | 0.9257 | 0.9505 | 0.9629 | 0.0004 |
| Random Forest | 0.9970 | 0.9925 | 0.8944 | 0.9276 | 0.9919 | 0.0063 |
| XGBoost | 0.9988 | 0.9974 | 0.9832 | 0.9897 | 1.0000 | 0.0067 |

Best overall F1 on CICIDS2017 test: **XGBoost (0.9897)**.

Per-class recall:

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

In short: **XGBoost is the star on CICIDS2017** (F1 0.990), and the Decision
Tree is the best balance on the intentionally-hard NSL-KDD test set.

---

## 5. The backend — the brain behind the screen

`src/api/main.py` is a **FastAPI** server. It loads the saved models and
answers HTTP requests the dashboard makes. Endpoints:

| Endpoint | What it does |
|---|---|
| `GET /models` | lists all 8 trained models + their metrics |
| `GET /compare` | the data the Comparison charts draw |
| `GET /attack-info/{type}` | a plain-language explanation of one attack type |
| `POST /predict` | classify **one** connection (raw features, or pick a test row by id) |
| `POST /simulate` | replay real test-set rows and classify them — the "live" feed |
| `GET /docs` | interactive documentation for every endpoint |

Key design points:
- Models, test data and preprocessors are **loaded lazily and cached** — the
  first request is slower, everything after is fast.
- The **same saved preprocessor** used in training transforms every incoming
  row, so live predictions see exactly what training saw.
- When `frontend/dist/` exists, the backend also **serves the dashboard**
  itself — one process runs the whole demo.

---

## 6. The dashboard — what the user sees

The React app (`frontend/`) has four tabs.

### Tab 1 — Live Monitor (the demo screen)

1. **Controls (left panel):** pick a **Dataset** (NSL-KDD / CICIDS2017) and a
   **Model** (XGBoost / Random Forest / Decision Tree / Logistic Regression),
   then press **▶ Start monitoring**.
2. **Status banner (top right):** "ALL CLEAR — traffic looks normal" or
   "ATTACK DETECTED — {type}" for the most recent connection, colour-coded
   green/red.
3. **Counters:** three big numbers —
   - **normal** — how many shown flows the model called Normal;
   - **attacks caught** — how many it flagged as an attack;
   - **flows shown** — the visible window (last 28).
4. **Packet list:** each row is one connection: time, sequence number, the
   model's verdict pill, a **confidence bar** (how sure), and a *correct/wrong*
   marker comparing the prediction to the dataset's own label.
5. **Click any row** → the "Why the model made this call" card shows, in plain words,
   what the model saw, its **top 3 guesses with percentages**, and whether it
   was right — plus a full description of the attack when it's an attack.
6. **"How to read this monitor"** panel at the bottom explains all of this on
   the page itself for non-technical viewers.

Everything updates every **1.6 seconds** by calling `POST /simulate`. A clear
label — **"SIMULATED TRAFFIC"** — keeps it honest: this replays recorded
dataset rows, it is not capturing your real network. The stream lives in a
React context shared by every tab, so it keeps running while you switch pages.

### Tab 2 — Model Comparison

- A **dataset toggle** (NSL-KDD / CICIDS2017).
- **Bar chart** of the macro metrics (accuracy, precision, recall, F1, AUC)
  across all four models.
- **Radar chart** comparing the models' strengths.
- **Scoreboard + latency tables** showing every number, including inference
  speed in ms per row — the accuracy-vs-speed trade-off the project studies.
  While monitoring runs, the latency table also shows a **live** column
  (averaged from the prediction log) with a green "LIVE" badge.
- **Training insights + development progression** — the Phase 3 convergence
  curves (XGBoost loss, Random Forest error vs trees, Decision Tree depth,
  Logistic Regression iterations) and the A→E pipeline progression, redrawn
  as **interactive charts** instead of static images: hover any point for the
  exact values, click a legend entry to hide a series, a dashed line marks the
  saved model's actual setting, and the Decision Tree chart shades the depth
  range where it starts overfitting. A **NSL-KDD / CICIDS2017 / Compare both**
  toggle overlays the two datasets (solid vs dashed).

### Tab 3 — Database

- The **full stored prediction log** — every flow the monitor has classified,
  newest first (time, sequence, dataset, model, verdict, confidence, latency,
  true label, correct/wrong).
- **Filters** by dataset and verdict, and **summary statistics** (total
  records, attacks flagged, average confidence, average live latency).
- The page polls `GET /predictions` every 2 seconds, so it stays live while
  monitoring runs on any tab. Data is persisted server-side to
  `data/processed/prediction_log.json` (max 200 records).

### Tab 4 — How It Works

- The methodology in plain language: datasets, cleaning, imbalance, SMOTE,
  training, evaluation.
- An **attack library** — each of the attack categories with what it is, how
  it works, what to look for, impact, and defence (served by
  `/attack-info/{type}`).

---

## 7. One packet, end to end (a story)

Follow one connection through the whole system:

1. You press **Start monitoring**.
2. The dashboard calls `POST /simulate` asking for a batch (e.g. 15 flows).
3. The backend picks real rows from the chosen dataset's **test set** (the
   part of the data the models were never trained on).
4. Each row's raw features go through the **saved preprocessor** (impute →
   scale → one-hot), exactly like training.
5. The chosen model (say XGBoost) computes a score for every class and picks
   the highest.
6. The backend replies with JSON: prediction, confidence, all class
   probabilities, the dataset's true label, and whether they match.
7. The dashboard stamps each row with a time and sequence number, prepends it
   to the packet list, updates the counters, and flashes the status banner.
8. If it's an attack, the banner turns red; clicking the row opens the
   explainer with the story and the top-3 probabilities.
9. Repeat every 1.6 s. Stop stops the stream.

---

## 8. How to read the numbers

| Metric | Plain meaning |
|---|---|
| **Accuracy** | share of connections classified correctly |
| **Precision** | of the alarms raised, the share that were real attacks |
| **Recall** | of the real attacks, the share that were caught |
| **F1** | one balanced score combining precision & recall |
| **AUC-ROC** | how well the model ranks attacks above normal (0.5 = coin flip, 1.0 = perfect) |
| **Latency** | time to classify one row (ms/row) — how fast it could run live |

Two things that look odd but are correct:
- **NSL-KDD test scores are lower than training.** That's the benchmark's
  design — it hides never-seen attack variants in the test set. It measures
  generalisation to new attacks.
- **The dataset's "answer key".** Every shown flow carries its original label,
  so the dashboard can say *correct/wrong*. No model is perfect — some rows are
  misclassified, which is exactly why the evaluation numbers are reported.

---

## 9. Where everything lives & the commands that matter

```
data/raw/            datasets (input)                     — must be present
data/processed/      cleaned splits, preprocessors         — regenerable
src/models/registry/ 8 trained models + metadata           — regenerable
notebooks/01..04     EDA → processing → training → evaluation
src/api/             FastAPI backend
frontend/            React dashboard (npm run build → dist/)
reports/ + docs/     all write-ups, charts, this document
```

| Command | Meaning |
|---|---|
| `.venv\Scripts\python.exe -m uvicorn src.api.main:app --port 8000` | start backend + dashboard |
| `.venv\Scripts\python.exe -m src.models.train` | retrain all 8 models from scratch |
| `.venv\Scripts\python.exe -m src.utils.generate_docs` | refresh the numbers in this document and the phase explanations |
| `.venv\Scripts\python.exe -m pytest tests\test_api.py -v` | run the 14 API tests |
| `cd frontend && npm run build` | rebuild the dashboard |

---

## 10. Related documents

- `reports/dataset_selection_justification.md` — why these two datasets
- `reports/model_comparison_report.md` — the full evaluation write-up
- `reports/deployment_guidelines.md` — how this fits a real network
- `docs/PHASE_EXPLANATIONS.md` — how the project was built, phase by phase
- `SETUP_GUIDE.md` — running it on another PC
- `GLOSSARY.md` — every technical term explained
