# Master Build Prompt — AI-Based Cybersecurity Threat Detection System

**How to use this file:** Copy everything below the line into your coding AI (Claude Code, Cursor, etc.), in the same project folder where you've placed your NSL-KDD / CICIDS2017 datasets and reference documents. Give it to the AI **one phase at a time** (Phase 1, wait for it to finish, review, then Phase 2, etc.) rather than all at once — this keeps the output manageable and lets you actually learn from each step instead of being handed a wall of code. Each phase already tells the AI to explain itself to a beginner, so read those explanations as you go.

---

## PROMPT TO PASTE INTO YOUR CODING AI

You are acting as a senior ML engineer and full-stack developer pair-programming with a university student who is a **beginner in both cybersecurity and machine learning**. You are helping build a final-year project called **"AI-Based Cybersecurity Threat Detection Using Machine Learning Techniques."**

### Project context (do not deviate from this without telling me)
- **Datasets:** NSL-KDD and CICIDS2017. I will dump ALL files from my dataset folders into `/data/raw/` — including duplicates, alternate formats, readme files, and possibly irrelevant files. **I do not know in advance which files are actually needed.** You must inventory and triage this folder yourself (see Phase 0.5 below) before doing any preprocessing. Treat CICIDS2017 as large — use chunked/sampled loading, don't assume it fits in memory at once.
- **Algorithms to implement and compare:** Logistic Regression, Decision Tree, Random Forest, XGBoost.
- **Feature engineering:** correlation analysis, mutual information, recursive feature elimination (RFE) — implement all three and let me compare their selected feature subsets.
- **Preprocessing:** median imputation, min-max scaling, one-hot encoding for categorical features, SMOTE for class imbalance.
- **Model selection:** grid search + k-fold cross-validation for hyperparameter tuning.
- **Evaluation metrics:** accuracy, precision, recall, F1-score, AUC-ROC, confusion matrix, and training/inference latency (this project explicitly cares about the real-time complexity-vs-latency trade-off).
- **Attack categories to detect and explain:**
  - NSL-KDD: Normal, DoS, Probe, R2L (Remote-to-Local), U2R (User-to-Root)
  - CICIDS2017: Benign, DDoS, PortScan, Brute Force, Web Attack, Botnet, Infiltration, Heartbleed (only include the categories actually present in whatever CICIDS2017 CSVs I provide)
- **Deliverables I need at the end:** a trained-model comparison report, a working local web app (frontend + backend) that demonstrates detection, and a deployment-guidelines document — all matching the milestones below.
- **Audience:** I am a student presenting this as a thesis/dissertation project. Everything must be explainable — assume I don't already know what a confusion matrix, ROC curve, or SYN flood is.

### Ground rules for how you (the coding AI) must work
1. **Work in phases, not all at once.** Wait for me to say "continue" before moving to the next phase.
2. **After every phase, give me a plain-English explanation** (no more than a page) of: what you just built, why it's structured that way, and what a marker/examiner would ask about it.
3. **Comment code heavily** — every non-trivial line or block should have a comment explaining *what* it does and *why*, written for a beginner, not just restating the code.
4. **Never silently invent results.** If a metric can't be computed without me running the code (e.g., actual accuracy numbers), say so clearly instead of making up plausible-looking numbers.
5. **Keep the project structure consistent** with the layout in Phase 0 — don't scatter files.
6. **Flag anything that needs my input** (e.g., "I need to know if your CICIDS2017 CSVs have this column name") instead of guessing silently.
7. **This is a defensive/educational detection project only.** Do not add any code that could be repurposed to actually launch attacks (e.g., real packet-injection or exploit code) — traffic "attacks" shown in the frontend are dataset replays/simulations for visualization only, not live attack tools.

---

## PHASE 0 — Project Setup & File Structure

Create the following folder structure and explain what each folder is for, as if teaching me for the first time:

```
cyber-threat-detection/
├── data/
│   ├── raw/                  # original NSL-KDD & CICIDS2017 files (I provide these)
│   ├── processed/            # cleaned, feature-engineered datasets (auto-generated)
│   └── references/           # papers/notes I drop in for context (not code-read, just for me)
├── notebooks/                # Jupyter notebooks for EDA and experimentation
├── src/
│   ├── data/
│   │   ├── loader.py          # dataset loading + column mapping
│   │   ├── preprocess.py      # cleaning, imputation, scaling, encoding, SMOTE
│   │   └── feature_selection.py  # correlation, mutual info, RFE
│   ├── models/
│   │   ├── train.py           # training + grid search + k-fold CV for all 4 algorithms
│   │   ├── evaluate.py        # metrics computation, confusion matrix, ROC curves
│   │   └── registry/          # saved trained models (.pkl / .json)
│   ├── api/
│   │   ├── main.py            # FastAPI backend serving predictions
│   │   ├── schemas.py         # request/response models
│   │   └── attack_info.py     # static explanations of each attack type (for frontend)
│   └── utils/
│       └── config.py          # paths, constants, feature lists
├── frontend/
│   ├── (React/Vite app — created in Phase 6)
├── reports/
│   ├── eda_report.md
│   ├── model_comparison_report.md
│   └── deployment_guidelines.md
├── tests/
├── requirements.txt
├── README.md                  # explains the whole project, setup steps, how to run everything
└── .gitignore
```

Set up a Python virtual environment and a `requirements.txt` including at minimum: `pandas`, `numpy`, `scikit-learn`, `xgboost`, `imbalanced-learn` (for SMOTE), `matplotlib`, `seaborn`, `fastapi`, `uvicorn`, `joblib`, `pydantic`. Explain what each library is for in one line each.

---

## PHASE 0.5 — Dataset Inventory & Triage

I have three separate dataset download folders and I'm going to copy **everything** from all of them into `data/raw/` — I don't know which files are the ones you actually need, which are duplicates, which are alternate formats of the same data, or which are irrelevant (readmes, license files, arff versions, packet-capture .pcap files, weka files, old KDD Cup 99 leftovers, etc.). Before writing any loading/preprocessing code, do the following:

1. **List every file** in `data/raw/` recursively, with file size and extension, and give me a table of what you found.
2. **Identify and categorize each file** as one of: `NSL-KDD core file` (e.g., `KDDTrain+.txt`, `KDDTest+.txt`, `KDDTrain+_20Percent.txt`), `CICIDS2017 core file` (the per-day/per-attack CSVs, e.g., `Monday-WorkingHours.pcap_ISCX.csv`, `Wednesday-workingHours.pcap_ISCX.csv`, etc.), `duplicate/alternate format` (e.g., `.arff` versions of NSL-KDD, zipped copies, `MachineLearningCVE` vs `GeneratedLabelledFlows` variants of CICIDS2017), `documentation/non-data` (readmes, field-name lists, license files), or `not needed / unclear — ask me`.
3. **For NSL-KDD:** tell me explicitly which files you'll use as train and which as test, and flag if you only have `KDDTrain+_20Percent.txt` instead of the full `KDDTrain+.txt` (this changes dataset size and you should tell me the trade-off).
4. **For CICIDS2017:** this dataset is commonly distributed as either (a) one CSV per day/attack-scenario (~8 files) or (b) a single merged CSV, and sometimes both a "MachineLearningCVE" (already labelled, ML-ready) version and a raw flow-generation version exist. Tell me which version(s) you have, and if both a merged file and the per-day files are present, tell me which one you'll use as the source of truth and why (to avoid double-counting the same traffic).
5. **If anything is ambiguous** (unrecognized filenames, corrupted-looking files, mismatched column counts between files that should match, or files that could be either dataset), **stop and ask me** rather than guessing or silently skipping them.
6. Once triage is complete, write your decisions to `data/raw/DATASET_MANIFEST.md` — a short file listing exactly which files were selected for the project, which were ignored and why, so this is documented for my thesis's data-collection section.
7. Only after I confirm the manifest looks right should you move on to Phase 1.

---

## PHASE 1 — Dataset Loading & Exploratory Data Analysis (EDA)

1. Write `src/data/loader.py` to load NSL-KDD (`KDDTrain+.txt` / `KDDTest+.txt`) and CICIDS2017 CSVs, standardizing column names and label formats between the two datasets into one common schema (e.g., `is_attack`, `attack_category`, `attack_type`).
2. Build an EDA notebook (`notebooks/01_eda.ipynb`) that produces: class distribution plots (show how imbalanced "attack vs normal" is), feature correlation heatmaps, missing-value summary, and basic statistics per dataset.
3. Auto-generate `reports/eda_report.md` summarizing findings in plain language — explain **why** class imbalance matters for this project (i.e., why a model could get 95% accuracy just by always predicting "normal" and why that's a problem here).
4. Explain, in your response, what NSL-KDD and CICIDS2017 actually are, how they were originally collected, and why researchers use them as benchmarks (tie this back to the literature themes in my proposal: Berman et al. 2019, Thakkar & Lohiya 2021).

---

## PHASE 2 — Preprocessing & Feature Engineering

1. In `src/data/preprocess.py`: implement median imputation for missing numeric values, min-max scaling, one-hot encoding for categorical fields (protocol type, service, flag, etc.), and SMOTE oversampling for the minority attack classes — applied **only to the training split**, never to test data (explain why this rule matters, i.e., data leakage).
2. In `src/data/feature_selection.py`: implement all three feature-selection methods separately — Pearson correlation filtering, mutual information ranking, and recursive feature elimination (RFE) with a base estimator — and output a comparison table of which features each method kept/dropped.
3. Save the final processed train/test splits to `data/processed/`.
4. Explain each preprocessing step in plain language as if I've never heard of one-hot encoding or SMOTE before, and explain what "feature" even means in this context (e.g., packet duration, byte count, flag type).

---

## PHASE 3 — Model Training & Hyperparameter Tuning

1. In `src/models/train.py`, train all four models — Logistic Regression, Decision Tree, Random Forest, XGBoost — using grid search + stratified k-fold cross-validation (stratified because of the class imbalance; explain why).
2. Log training time and inference latency per model (needed for the real-time deployment trade-off discussion in my proposal).
3. Save each trained model + its best hyperparameters to `src/models/registry/`.
4. Explain, for each algorithm, in beginner terms: what it fundamentally does (e.g., "Decision Tree asks a series of yes/no questions about the traffic..."), and why it might do better or worse than the others on this kind of tabular network-traffic data.

---

## PHASE 4 — Evaluation & Model Comparison

1. In `src/models/evaluate.py`, compute accuracy, precision, recall, F1-score, AUC-ROC, and confusion matrices for all four models on the held-out test set, for both datasets separately (this is your cross-dataset robustness comparison).
2. Generate comparison charts (bar charts per metric, ROC curves overlaid, confusion matrix heatmaps) and save them as images the frontend can later display.
3. Auto-generate `reports/model_comparison_report.md` with a results table and written interpretation.
4. Explain each metric in plain English with a cybersecurity-specific example (e.g., "recall matters most here because a missed attack — a false negative — is far more dangerous than a false alarm").

---

## PHASE 5 — Backend API

1. Build a FastAPI backend (`src/api/main.py`) exposing endpoints such as:
   - `POST /predict` — accepts traffic-feature input (or a dataset row ID) and returns the prediction from a chosen model, with probability/confidence and predicted attack category.
   - `GET /models` — lists available trained models with their headline metrics.
   - `GET /compare` — returns the full metric comparison data (for frontend charts).
   - `GET /attack-info/{attack_type}` — returns a plain-language explanation of that attack type (definition, how it works, real-world impact) for `src/api/attack_info.py`.
   - `POST /simulate` — replays a batch of rows from the test set (framed clearly in the UI as "simulated traffic replay from dataset," not a live attack) so the frontend can show detection happening "live."
2. Explain what an API is, what a REST endpoint is, and why we separate backend (Python/ML) from frontend (the website) instead of putting everything in one file.

---

## PHASE 6 — Frontend (Interactive, User-Friendly UI)

Build a React + Vite (or Next.js) frontend with a clean, modern, non-templated visual design — not default Bootstrap look. Requirements:

1. **Dashboard/Home:** live-feeling "traffic monitor" view showing simulated packets streaming in, each getting classified in real time (via `/simulate` + `/predict`), with a clear "Normal" vs "Attack Detected" indicator and the specific attack category.
2. **Attack detail panel:** when an attack is flagged, show an expandable card explaining that attack type in plain language (definition, typical indicators, real-world damage potential) pulled from `/attack-info/{attack_type}`.
3. **Model comparison page:** interactive charts (bar/radar charts) comparing all four models across accuracy, precision, recall, F1, AUC-ROC, and latency, with toggles to switch which dataset's results are shown.
4. **"How it works" / education page:** written for a non-technical visitor — explains what ML-based intrusion detection is, walks through the pipeline (data → preprocessing → model → prediction), and briefly explains each of the four algorithms and each attack category, so the site itself teaches the concepts (this doubles as a way to explain your own project to your examiner).
5. **Clean UI requirements:** consistent color palette (suggest a dark "security operations center" theme with clear alert-red for attacks, calm green for normal traffic), responsive layout, readable typography, loading states, and no unstyled default HTML elements.
6. Explain the frontend's file/component structure to me the same way you did for the backend.

---

## PHASE 7 — Documentation & Deployment Guidelines

1. Write a full `README.md`: project overview, folder structure explained, setup instructions (env, dependencies, how to run backend and frontend), how to retrain models, and a troubleshooting section.
2. Write `reports/deployment_guidelines.md` addressing my proposal's objective of "practical guidance on integrating ML into live security infrastructure" — cover things like: where in a real network this would sit (e.g., analyzing traffic at a SPAN/mirror port, not inline at first), retraining cadence, handling concept drift, model monitoring, and the accuracy-vs-latency trade-off findings from Phase 4.
3. Give me a short glossary (in the README or a separate `GLOSSARY.md`) of every technical term used across the project (SMOTE, AUC-ROC, RFE, mutual information, k-fold CV, zero-day, APT, polymorphic malware, etc.) in one or two beginner-friendly sentences each.

---

## Final instruction to the coding AI
At the end of each phase, stop and ask me: *"Do you want me to explain any part of this in more depth, or should I continue to the next phase?"* Do not skip ahead. Do not fabricate performance numbers before I've actually run the training code — describe what the code *will* compute, not invented results.
