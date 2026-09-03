# AI-Based Cybersecurity Threat Detection Using Machine Learning Techniques

---

*Note to candidate: replace the bracketed placeholders on this page and in
Section 1 with your personal and institutional details before submission.*

**Author name:** [Candidate Name]

**Student number:** [Student Number]

**Institution:** Sheffield Hallam University

**Department / College:** [Department / College]

**Supervisor:** [Supervisor Name]

**Date:** [Date of submission]

**Degree:** [e.g. BSc (Hons) Computer Science / Cybersecurity]

**Citation style:** APA 7th edition (to be confirmed with supervisor)

---

## Table of Contents

*(In the Word version, right-click this field and choose "Update Field" to
refresh the page numbers.)*

1. Introduction
2. Research Question, Aim and Objectives
3. Literature Review
4. Research Design and Methodology
5. Dataset Selection Justification
6. System Implementation
7. Results and Evaluation
8. Discussion
9. Deployment Guidelines
10. Risks, Ethics and Issues
11. Limitations of the Study
12. Conclusion and Future Work
13. References
14. Appendices

---

## Abstract

Cyberattacks continue to evolve faster than signature-based defences can be
maintained, and machine learning (ML) has emerged as a data-driven alternative
capable of detecting novel attack patterns. This study developed, tuned and
evaluated four classical ML classifiers — Logistic Regression, Decision Tree,
Random Forest and XGBoost — for network intrusion detection on two benchmark
datasets: NSL-KDD (2009) and CICIDS2017 (2017). The datasets were selected to be
complementary in age, feature structure and attack diversity, enabling an
examination of cross-dataset robustness. A consistent preprocessing pipeline
(median imputation, min-max scaling, one-hot encoding), SMOTE balancing applied
strictly inside cross-validation folds, three-way feature selection (Pearson
correlation, mutual information, recursive feature elimination), and grid search
with stratified 5-fold cross-validation were applied identically to both
datasets. On CICIDS2017, XGBoost achieved the highest test performance with an
F1-macro of 0.9897, an accuracy of 0.9988 and an AUC-ROC of 1.0000, and was the
only model to reach full recall on the rare Heartbleed class. On the
adversarially-designed NSL-KDD test set, the Decision Tree achieved the best
F1-macro of 0.6170, while XGBoost attained the highest AUC-ROC of 0.9491.
Inference latency for all models was below 0.01 ms per row, indicating that
computational speed is not the deployment bottleneck. The low recall observed on
the rare R2L and U2R classes is consistent with findings reported by Tavallaee
et al. (2009) and reflects both extreme class imbalance and the deliberate
inclusion of unseen attack variants in the test set. The study concludes with
evidence-based deployment guidelines for integrating the best-performing model
into a real network environment, together with a discussion of limitations and
directions for future work, including deep-learning comparison and newer
benchmark evaluation.

---

## 1. Introduction

### 1.1 Statement of the Problem

Sophisticated cyberattacks are increasing in scale and sophistication
globally. Projections indicate that cybercrime damages could exceed USD 10.5
trillion annually by 2025, and modern threat actors employ techniques such as
zero-day exploits, advanced persistent threats (APTs) and polymorphic malware
that are specifically designed to evade static defences. Traditional
signature-based detection systems, which match traffic against a database of
known attack fingerprints, are inherently limited in this environment: they
cannot recognise attacks for which no signature exists, and they require
continuous, labour-intensive signature maintenance.

### 1.2 Background and Rationale

Machine learning offers an alternative paradigm. Rather than being programmed
with explicit rules, an ML model learns the statistical patterns that
distinguish malicious from benign traffic from labelled historical examples.
This enables the detection of novel and evolving threats on the basis of
behaviour rather than signature. This study investigates the practical
effectiveness of four well-established classical ML classifiers — Logistic
Regression, Decision Tree, Random Forest and XGBoost — on two complementary
intrusion-detection benchmark datasets, NSL-KDD and CICIDS2017. The choice of
classical classifiers, rather than deep learning, is deliberate and is
justified by considerations of computational cost, interpretability and
reproducibility within a constrained project timeframe, as discussed in the
literature review (Section 3).

### 1.3 Gaps in Current Knowledge

A review of the literature (Section 3) identified three gaps that this project
directly addresses:

1. **Single-dataset evaluation.** The majority of published studies evaluate
   models on a single benchmark, which limits the generalisability of their
   conclusions. This project evaluates an identical pipeline on two datasets
   spanning roughly two decades of traffic evolution, enabling conclusions
   about cross-dataset robustness.
2. **The accuracy-versus-latency trade-off.** The real-time trade-off between
   model complexity and detection latency is not well studied. This project
   measures per-row inference latency for every model and dataset.
3. **Practical deployment guidance.** Academic ML research frequently stops at
   evaluation results and provides little guidance on integrating models into
   live security infrastructure. This project produces explicit deployment
   guidelines (Section 9).

### 1.4 Possible Applications

The outputs of this project are applicable to:

- real-time network intrusion detection within organisational cybersecurity
  infrastructure;
- automated threat classification and alerting for security operations
  centres (SOCs);
- an evidence-based deployment framework usable by IT security teams and by
  the academic cybersecurity research community.

---

## 2. Research Question, Aim and Objectives

### 2.1 Research Question

*How effective are Logistic Regression, Decision Tree, Random Forest and
XGBoost in detecting cybersecurity threats based on network traffic analysis,
and what factors influence detection performance in different dataset
settings?*

### 2.2 Research Aim

The aim of this study was to develop, evaluate and compare ML-based models for
detecting cybersecurity threats using network traffic analysis, and to provide
a comprehensive, deployable framework for organisational threat detection and
prevention.

### 2.3 Research Objectives

The following objectives were carried forward from the project proposal. Each
is marked as **achieved** or **partially achieved**, with a note on how it was
fulfilled.

**Table 8.** Research objectives and achievement status.

| Objective | Status | Evidence / note |
|---|---|---|
| 1. Download and prepare the NSL-KDD and CICIDS2017 datasets to generate high-quality training and testing data | **Achieved** | Datasets acquired, documented in `data/raw/DATASET_MANIFEST.md`, cleaned (corrupt labels, Infinity values, zero-variance columns) and split into train/test under a no-leakage protocol (Section 4.4). |
| 2. Use correlation analysis, mutual information and recursive feature elimination to engineer optimal feature subsets | **Achieved** | Three complementary feature-selection methods implemented and compared on pre-SMOTE training data (Section 4.5). |
| 3. Systematically tune the four ML classifiers using grid search and k-fold cross-validation | **Achieved** | Grid search with stratified 5-fold cross-validation, scored on F1-macro, with SMOTE inside the folds (Section 4.6). |
| 4. Evaluate and compare models using accuracy, precision, recall, F1-score and AUC-ROC to identify the best-performing algorithm | **Achieved** | Full evaluation on untouched test sets for both datasets, including per-class metrics, confusion matrices and latency (Section 7). |
| 5. Develop practical deployment guidelines for implementing the framework in organisational cybersecurity infrastructure | **Achieved** | Deployment guidelines produced, covering passive SPAN-port placement, retraining cadence and concept-drift monitoring (Section 9). |
| 6. (Added) Build an interactive, demonstrable system (backend API + dashboard) | **Achieved** | FastAPI backend serving the trained models and a React dashboard presenting live classifications and comparison charts (Section 6). |

---

## 3. Literature Review

The literature review is organised around three themes identified in the
project proposal, with the dataset-selection literature integrated into the
final subsection because of its direct relevance to the design decisions made
in this study.

### 3.1 Theme 1: Deep Learning versus Classical Machine Learning

Berman et al. (2019) surveyed deep learning methods for cybersecurity and
reported that deep architectures typically outperform classical approaches on
benchmark accuracy, particularly for complex and evolving attacks. However,
they also noted significant computational complexity and limited practical
deployment focus. Mahdavifar and Ghorbani (2019) reached a similar conclusion,
observing that comprehensive deep models perform well but suffer from
scalability concerns. Both studies contrast with the position of Gao et al.
(2019), who demonstrated that ensemble machine learning techniques achieve
competitive accuracy at substantially lower computational cost.

This contrast directly informed the present study's methodology: the four
selected classifiers represent the accuracy/interpretability/compute frontier
of *classical* ML, and the study treats a deep-learning comparison as an
explicit direction for future work (Section 12) rather than attempting an
incomplete deep-learning experiment within the project's constraints.

### 3.2 Theme 2: Ensemble Methods Performance

Ensemble methods — which combine multiple weaker models into a stronger one —
are consistently among the strongest classical approaches in the intrusion
detection literature. Gao et al. (2019) showed that adaptive ensemble models
achieve high detection accuracy with lower complexity than single deep models.
Ramu (2025) reported that XGBoost, a boosting ensemble, outperformed other
classical classifiers on threat detection tasks, and noted that its sequential
error-correction mechanism handles class imbalance effectively. These findings
motivated the inclusion of Random Forest (a bagging ensemble) and XGBoost (a
boosting ensemble) alongside the two non-ensemble baselines in this project.

### 3.3 Theme 3: Feature Engineering and Dataset Quality

Thakkar and Lohiya (2021) reviewed the advancement of intrusion detection
datasets and reported two findings central to this project: (i) optimal feature
subsets can decrease computational complexity by approximately 40% without
accuracy loss, and (ii) dataset quality — including class imbalance and label
consistency — significantly affects generalisability across heterogeneous
network environments. Ozkan-Ozay et al. (2024) similarly identified gradient
boosting methods as effective and emphasised the impact of class imbalance on
reported results. These findings justify the three-method feature-selection
step (Section 4.5) and the disciplined handling of class imbalance
(Section 4.4) in the present study.

### 3.4 Theme 4: Dataset Selection Literature

The choice of benchmark dataset determines the validity and comparability of an
intrusion-detection study. Tavallaee et al. (2009) provided a detailed analysis
of the KDD Cup 99 dataset, documenting its redundancy and its persistent
difficulty with the rare R2L and U2R classes, and introduced NSL-KDD as a
de-duplicated improvement. Sharafaldin et al. (2018) generated CICIDS2017 from
realistic captured traffic, providing a modern benchmark with contemporary
attack categories and flow-level features. Moustafa and Slay (2015) introduced
UNSW-NB15 as a more recent alternative with nine attack families. Thakkar and
Lohiya (2021) recommended that studies use multiple, complementary datasets to
test robustness. Collectively, this literature establishes the rationale for
the two-dataset design adopted in this project, which is examined in detail in
Section 5.

### 3.5 Summary of Research Gaps

Synthesis of the literature identified the following gaps, which frame the
research question:

- evaluation on a single dataset limits cross-dataset robustness conclusions;
- the real-time accuracy-versus-latency trade-off is under-studied;
- practical guidance on integrating ML detection into live security
  infrastructure is scarce.

---

## 4. Research Design and Methodology

### 4.1 Research Philosophy

The study adopts a **positivist** philosophy: systematic observation and
statistical evaluation of objective, reproducible ML benchmarks. An
interpretivist approach was rejected because the research does not concern
subjective human experience.

### 4.2 Research Approach

The study is **deductive**: established theory in machine learning and
cybersecurity was used to form testable hypotheses, which were validated
through controlled experimentation. An inductive approach was rejected as less
rigorous given the well-established theoretical foundations of the algorithms.

### 4.3 Research Strategy, Methods and Time Horizon

- **Strategy:** an experimental design with comparative analysis. Four
  classifiers were trained under controlled conditions using identical dataset
  splits and evaluation protocols.
- **Methods:** supervised multiclass classification on labelled benchmark
  datasets (NSL-KDD, CICIDS2017). Unsupervised and semi-supervised approaches
  were considered and rejected for their reduced interpretability and greater
  implementation complexity.
- **Time horizon:** cross-sectional — data were collected and models evaluated
  within a fixed 16-week project timeframe.

### 4.4 Implementation: Data Preparation and Preprocessing

Data preparation was implemented in `src/data/loader.py` and
`src/data/preprocess.py` and executed through notebooks 01–04.

**Loading and cleaning.** A common schema (`source`, `is_attack`,
`attack_category`, `attack_type`) was applied to both datasets. For NSL-KDD,
the file's difficulty-score column was identified as metadata rather than
traffic and was dropped at load time to prevent leakage. For CICIDS2017, a
corrupted Unicode character in the "Web Attack" label was repaired, `Infinity`
values produced by division-by-zero rate columns were converted to missing
values, and eight zero-variance columns were dropped. Because CICIDS2017 is
extremely imbalanced, a capped-loading procedure retained every rare-class row
while capping the dominant classes at 15,000 rows, yielding 62,422 training
rows.

**Preprocessing pipeline.** A single pipeline, fitted on the training split
only, performed: (i) conversion of `Inf` to missing values; (ii) median
imputation of missing values; (iii) min-max scaling to [0,1]; and (iv)
one-hot encoding of NSL-KDD's categorical features (expanding it from 41 to
122 columns). The fitted preprocessor and the label encoder were saved to disk
so that inference transforms incoming rows identically to training.

**Class imbalance.** SMOTE (Synthetic Minority Over-sampling Technique) was
applied to the training data only: NSL-KDD rare classes (R2L, U2R) were boosted
to 15,000 rows each, producing 154,926 training rows; CICIDS2017 was balanced
to 12,000 rows per class, producing 108,000 rows. SMOTE was embedded inside the
training pipeline within cross-validation folds (with `k_neighbors=3`) so that
synthetic examples never leaked into validation folds. The EDA findings that
justified this step are shown in Figures 1 and 2 and reported in
`reports/eda_report.md`.

### 4.5 Implementation: Feature Selection

Three complementary methods were compared in `src/data/feature_selection.py`:
Pearson correlation (linear relationships), mutual information (non-linear
relationships) and recursive feature elimination (iterative model-based
elimination). Selection was performed on the pre-SMOTE training data to
preserve honesty. The leading features were consistent with domain
expectations: `src_bytes` for NSL-KDD, and packet/flow size features
(`average_packet_size`, `packet_length_mean`) for CICIDS2017. The comparison is
presented in Figure 5.

### 4.6 Implementation: Model Training and Hyperparameter Tuning

Eight models (four algorithms × two datasets) were trained in
`src/models/train.py` and notebook 03. Each algorithm was tuned by **grid
search** over a small hyperparameter grid (e.g. Random Forest: 100/200 trees ×
depth None/20 × minimum leaf 1/5; XGBoost: learning rate × depth × number of
trees), evaluated by **stratified 5-fold cross-validation** using **F1-macro**
as the selection metric, with SMOTE inside the pipeline. A fixed random seed
(42) was used for all splits, SMOTE sampling and model initialisation to
guarantee reproducibility. Every trained model, together with metadata (best
hyperparameters, CV score, latency, training rows, timestamp), was saved to
`src/models/registry/`.

### 4.7 Evaluation Protocol and Leakage Discipline

The evaluation protocol applied to both datasets was identical:

1. preprocessors and SMOTE fitted on the training split only;
2. SMOTE applied inside cross-validation folds, never before splitting;
3. the test set left untouched until the final evaluation;
4. metrics computed on the untouched test sets: accuracy, precision (macro),
   recall (macro), F1-macro, AUC-ROC, per-class metrics, confusion matrices and
   per-row inference latency.

This protocol follows the no-leakage discipline that the literature (Thakkar
and Lohiya, 2021) identifies as essential for trustworthy results.

---

## 5. Dataset Selection Justification

The two benchmark datasets were selected deliberately rather than by default,
because they are complementary in age, feature structure and attack diversity,
allowing the study to test cross-dataset robustness — one of the core research
gaps identified in Section 3.

### 5.1 Comparison of Public IDS Benchmark Datasets

**Table 1.** Comparison of public IDS benchmark datasets considered in this study.

| Dataset | Year | Size | Attack Coverage | Key Limitation |
|---|---|---|---|---|
| KDD Cup '99 | 1999 | ~4.9M records | DoS, Probe, R2L, U2R | Outdated traffic patterns; heavy redundancy |
| **NSL-KDD (selected)** | 2009 | 148,517 records | DoS, Probe, R2L, U2R | Still reflects late-1990s traffic structure |
| UNSW-NB15 | 2015 | ~2.5M records | 9 attack types | Partly synthetic traffic; smaller benchmarking base |
| **CICIDS2017 (selected)** | 2017 | ~2.8M records | 14 attack categories, 80 features | Known label-inconsistency/class-imbalance issues |
| CSE-CIC-IDS2018 | 2018 | Very large (100GB+) | Similar to CICIDS2017, larger scale | Impractical compute/time for a single dissertation |
| Bot-IoT / TON_IoT | 2019–2020 | Varies | IoT-specific attacks | Domain-specific (IoT), not general enterprise traffic |

### 5.2 Rationale for the Selected Pair

1. **Complementary by design.** NSL-KDD is a refined, widely-benchmarked
   classic (Tavallaee et al., 2009); CICIDS2017 is a modern, high-dimensional
   dataset with contemporary attack traffic (Sharafaldin et al., 2018). Testing
   across both spans roughly two decades of network-traffic evolution.
2. **Comparability with prior work.** NSL-KDD remains one of the most cited IDS
   benchmarks, enabling direct comparison of this study's results against a
   large body of existing literature.
3. **Practical feasibility.** Alternatives such as CSE-CIC-IDS2018 (100GB+) or
   UNSW-NB15 (synthetic attack-tool traffic) introduce compute or
   methodological constraints poorly suited to a 16-week, Google Colab-based
   project. UNSW-NB15 and KDD Cup '99 were retained as documented backup
   datasets in the project risk register.
4. **Directly serves the stated research gap.** Cross-dataset generalisability
   is one of the project's three named gaps in current knowledge, making the
   two-dataset design methodologically necessary rather than incidental.

### 5.3 Dataset Characterisation

**NSL-KDD.** The training file contains 125,973 rows and the test file 22,544
rows, each with 41 features and five classes (Normal, DoS, Probe, R2L, U2R).
The class distribution is imbalanced, with 67,343 Normal, 45,927 DoS, 11,656
Probe, 995 R2L and 52 U2R rows (Figure 2). The test set deliberately includes
attack variants not present in training (Tavallaee et al., 2009).

**CICIDS2017.** The raw data contain approximately 2.83 million flows with 78
numeric features and nine classes (Figure 1). The distribution is heavily
imbalanced: 2,273,097 Normal (80.3%) versus 557,646 attack rows, including only
11 Heartbleed and 36 Infiltration rows. The dataset also contains label
corruption, `Infinity` values and zero-variance columns, which were addressed
in preprocessing (Section 4.4).

---

## 6. System Implementation

### 6.1 System Architecture Overview

The final deliverable is organised into three components that interact over
HTTP:

1. **Research pipeline** — Jupyter notebooks 01–04 and the `src/` package
   (`src/data/`, `src/models/`, `src/api/`, `src/utils/`), which produce the
   processed splits, preprocessors, label encoders, trained models and the
   model registry.
2. **Backend** — a FastAPI application (`src/api/main.py`) that loads the
   saved artifacts and exposes REST endpoints.
3. **Frontend** — a React + Vite + Recharts dashboard that consumes the backend
   endpoints and presents live classifications and comparison charts.

*(Insert diagram here: **Figure 6.** High-level architecture. A diagram should
show notebooks/pipeline → artifacts (data/processed, src/models/registry) →
FastAPI backend → React dashboard, with the SQLite-backed panel companion as a
secondary consumer.)*

### 6.2 Backend Design

The backend exposes the following endpoints:

- `GET /models` — list all eight trained models with their metrics;
- `GET /compare` — comparison data consumed by the dashboard charts;
- `GET /attack-info/{type}` — plain-language explanation of an attack type;
- `POST /predict` — classify a single connection (raw features or a test-set
  row by id);
- `POST /simulate` — replay real test-set rows as a "live" feed for the
  dashboard;
- `GET /docs` — auto-generated interactive API documentation.

Key design decisions: models, preprocessors and test data are loaded lazily
and cached to keep response times low; the *saved* preprocessor is reused for
inference so that live predictions see exactly the same transformation as
training; and, when the frontend build exists, the backend also serves the
dashboard from `/`, allowing a single Uvicorn process to run the whole demo.

### 6.3 Frontend Design

The dashboard contains four tabs: **Live Monitor** (polls `POST /simulate`
every 1.6 seconds, displays up to 28 flows with verdict pills, confidence
bars, correct/wrong markers and a "SIMULATED TRAFFIC" badge to make clear the
data are recorded test rows; below the stream a **Stored prediction log**
panel lists every classified flow, persisted server-side to
`data/processed/prediction_log.json`, maximum 200 entries), **Model
Comparison** (bar and radar charts, scoreboard and latency tables — including
a **live** latency column averaged from the prediction log while monitoring
runs — plus the tuning-impact and training-curve analysis from Section 7.5),
**Database** (the full stored prediction log with dataset/verdict filters and
summary statistics, refreshed every two seconds), and **How It Works** (the
methodology in plain language plus an attack library). The monitoring loop
lives in a React context shared by the tabs, so the stream keeps running
across tab switches and the Database view stays live. For
every user the UI includes a self-guided ten-step spotlight tour that
auto-starts on each page load and highlights every control, inline "?"
help tooltips on every non-obvious input and counter, and an empty state on
the Live Monitor that explains the page before the first batch arrives.

### 6.4 Frontend–Backend Communication

In development, the Vite dev server (port 5173) proxies `/api` requests to the
backend. In production, the built dashboard is served from the backend root and
the frontend's API client selects the appropriate base URL
(`import.meta.env.DEV`). A backend test suite (`tests/test_api.py`) contains
14 passing tests covering every endpoint.

### 6.5 Key Design Decisions and Trade-offs

- **Lazy loading and caching** trade a slightly slower first request for fast
  steady-state behaviour.
- **Single-process demo** (backend serves the frontend) simplifies
  deployment and demonstration at the cost of coupling presentation to the API.
- **A separate panel companion project** (`research_panel_project/`) wraps the
  same models in a DB-backed FastAPI application whose SQLite database logs
  every live detection — providing a verifiable, queryable "under-the-hood"
  view for the research committee.

---

## 7. Results and Evaluation

All results below were computed on the untouched test sets by
`src/models/evaluate.py` (notebook 04) and are stored in
`data/processed/evaluation_results.json`. Metrics are macro-averaged across
classes.

### 7.1 Cross-Validation Results (Model Selection)

**Table 2.** Cross-validation F1-macro (mean over 5 stratified folds), used for
model selection.

| Dataset | Logistic Regression | Decision Tree | Random Forest | XGBoost |
|---|---:|---:|---:|---:|
| NSL-KDD | 0.7432 | 0.8907 | 0.9333 | **0.9565** |
| CICIDS2017 | 0.8755 | **0.9908** | 0.9765 | 0.9848 |

### 7.2 NSL-KDD Test-Set Results

**Table 3.** NSL-KDD test-set results (22,544 rows).

| Model | Accuracy | Precision | Recall | F1-macro | AUC-ROC | Latency (ms/row) |
|---|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 0.7628 | 0.6707 | 0.6295 | 0.5572 | 0.9057 | 0.0008 |
| Decision Tree | 0.8163 | 0.7545 | 0.5836 | **0.6170** | 0.7672 | 0.0006 |
| Random Forest | 0.7488 | 0.7972 | 0.5081 | 0.5384 | 0.9489 | 0.0089 |
| XGBoost | 0.7782 | 0.8281 | 0.5653 | 0.6086 | **0.9491** | 0.0027 |

**Table 4.** NSL-KDD per-class recall (share of each true class correctly
classified).

| Class | Logistic Regression | Decision Tree | Random Forest | XGBoost |
|---|---:|---:|---:|---:|
| DoS | 0.8105 | 0.9005 | 0.7604 | 0.8202 |
| Normal | 0.9233 | 0.9616 | 0.9730 | 0.9731 |
| Probe | 0.7270 | 0.6877 | 0.5915 | 0.6258 |
| R2L | 0.1344 | 0.2338 | 0.1112 | 0.1538 |
| U2R | 0.5522 | 0.1343 | 0.1045 | 0.2537 |

Confusion matrices and ROC curves for NSL-KDD are presented in Figures 3 and 7
(see `reports/figures/confusion_nslkdd.png`, `reports/figures/roc_nslkdd.png`).

### 7.3 CICIDS2017 Test-Set Results

**Table 5.** CICIDS2017 test-set results (15,606 rows).

| Model | Accuracy | Precision | Recall | F1-macro | AUC-ROC | Latency (ms/row) |
|---|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 0.9549 | 0.8391 | 0.8622 | 0.8267 | 0.9784 | 0.0006 |
| Decision Tree | 0.9972 | 0.9951 | 0.9257 | 0.9505 | 0.9629 | 0.0004 |
| Random Forest | 0.9970 | 0.9925 | 0.8944 | 0.9276 | 0.9919 | 0.0063 |
| XGBoost | 0.9988 | 0.9974 | 0.9832 | **0.9897** | **1.0000** | 0.0067 |

**Table 6.** CICIDS2017 per-class recall.

| Class | Logistic Regression | Decision Tree | Random Forest | XGBoost |
|---|---:|---:|---:|---:|
| Botnet | 0.9848 | 0.9949 | 1.0000 | 0.9975 |
| Brute Force | 0.9946 | 1.0000 | 1.0000 | 1.0000 |
| DDoS | 0.9880 | 0.9997 | 0.9997 | 0.9997 |
| DoS | 0.9723 | 0.9983 | 0.9977 | 0.9990 |
| Heartbleed | 0.5000 | 0.5000 | 0.5000 | **1.0000** |
| Infiltration | 0.5714 | 0.8571 | 0.5714 | 0.8571 |
| Normal | 0.8307 | 0.9920 | 0.9910 | 0.9977 |
| PortScan | 0.9937 | 0.9983 | 0.9987 | 0.9980 |
| Web Attack | 0.9243 | 0.9908 | 0.9908 | 1.0000 |

Confusion matrices and ROC curves for CICIDS2017 are presented in Figures 4 and
8 (see `reports/figures/confusion_cicids.png`, `reports/figures/roc_cicids.png`).

### 7.4 Summary of Key Findings

- **XGBoost is the overall best model**, achieving 0.9897 F1-macro and 1.0000
  AUC-ROC on CICIDS2017 and the highest AUC-ROC (0.9491) on NSL-KDD, with
  per-row latency between 0.0021 and 0.0067 ms.
- **The Decision Tree generalises best to the adversarial NSL-KDD test set**
  (F1-macro 0.6170), but produces the weakest probability ranking (AUC 0.7672).
- **Random Forest overfits the training distribution**: its NSL-KDD
  cross-validation F1 (0.9333) collapses to 0.5384 on the test set, which
  contains unseen attack variants.
- **Rare classes dominate the difficulty.** R2L recall is 0.11–0.23 and U2R
  recall 0.10–0.55 across models on NSL-KDD; Heartbleed recall is 0.50 for
  three of the four models on CICIDS2017 (XGBoost achieves 1.0000).
- **Latency is not the deployment bottleneck.** All models classify a row in
  under 0.01 ms.

### 7.5 The Value of Hyperparameter Tuning (Measured)

A baseline-vs-tuned comparison (same preprocessing pipeline, same untouched test
set; see `reports/tuning_impact_report.md`, data in
`data/processed/tuning_impact.json`) quantifies how much grid search contributed:

| Dataset | Model | Baseline F1 | Tuned F1 | Δ F1 |
|---|---:|---:|---:|---:|
| NSL-KDD | Logistic Regression | 0.5572 | 0.5572 | 0.0000 |
| NSL-KDD | Decision Tree | 0.5791 | 0.6170 | +0.0379 |
| NSL-KDD | Random Forest | 0.5567 | 0.5384 | −0.0183 |
| NSL-KDD | XGBoost | 0.5942 | 0.6086 | +0.0144 |
| CICIDS2017 | Logistic Regression | 0.7912 | 0.8267 | +0.0355 |
| CICIDS2017 | Decision Tree | 0.9524 | 0.9505 | −0.0019 |
| CICIDS2017 | Random Forest | 0.9276 | 0.9276 | 0.0000 |
| CICIDS2017 | XGBoost | 0.9789 | 0.9897 | +0.0108 |

Tuning therefore helps most where the defaults are weakest (Logistic
Regression on CICIDS2017, Decision Tree on NSL-KDD) and is neutral or slightly
negative for Random Forest — a Regularised/ensemble model whose strong defaults
leave little for a depth grid to improve. The A→E development-progression for
Logistic Regression (`reports/development_progression_report.md`) reinforces
this: cleaning/encoding (B), class balancing (D) and the correct `C` (E)
together take NSL-KDD F1 from 0.27 to 0.56, while aggressive consensus feature
selection (C) actively harms a linear model. Training behaviour curves
(XGBoost validation loss, Random Forest error vs. tree count, Decision Tree
depth, Logistic Regression convergence) are reproduced in
`reports/figures/training_curves/` and shown on the dashboard's Compare page as
interactive charts redrawn from `data/processed/training_curves.json` — with
hover tooltips, a dashed reference line at the saved model's setting, a true
numeric x-axis, a "Compare Both" NSL-KDD/CICIDS2017 overlay, and a red band
over the depth range where the Decision Tree overfits.
A full ledger of dataset sizes, grid sizes, fit times, CV scores and latencies
is in `reports/model_dataset_usage_statistics.md`.

---

## 8. Discussion

### 8.1 Interpretation of Results

The results demonstrate that classical ensemble models are highly effective at
network intrusion detection on modern, distributionally stable data
(CICIDS2017), with XGBoost achieving near-perfect classification. The near-perfect
results on CICIDS2017 must be interpreted carefully: the test distribution closely
matches the training distribution, so these figures measure how well the models
fit their own data. NSL-KDD, by contrast, measures survival of novelty, and its
lower scores (best F1-macro 0.6170) are the more demanding and realistic
measurement of generalisation.

### 8.2 The R2L and U2R Limitation

The consistently low recall on the rare NSL-KDD classes (R2L 0.11–0.23, U2R
0.10–0.55) is consistent with the benchmark's documented behaviour: Tavallaee et
al. (2009) identified R2L and U2R as the persistent weak points of the KDD
family, because these attacks exhibit few statistically distinct features and
resemble legitimate traffic. Compounding factors in this study are the tiny
training counts (995 R2L, 52 U2R) and the inclusion of unseen attack variants in
the test set. SMOTE improved these classes relative to an unbalanced baseline
but cannot create information that is absent from the available examples.

### 8.3 Cross-Dataset Robustness

The gap between CICIDS2017 (≈0.99 F1) and NSL-KDD (≈0.54–0.62 F1) test scores
is a direct measurement of benchmark design, and it is itself a research
finding: models trained and tested within a single modern dataset can appear
near-perfect while failing to generalise to novel attack variants. This
supports the recommendation, consistent with Thakkar and Lohiya (2021), that
studies evaluate across multiple benchmarks and that deployed models be
evaluated on live traffic before deployment.

### 8.4 The Accuracy-versus-Latency Trade-off

Every model classifies a row in under 0.01 ms; even the slowest model is orders
of magnitude faster than the row-production rate of a high-bandwidth link.
Consequently, in this project the meaningful trade-off is between accuracy and
explainability, not accuracy and speed. XGBoost is recommended for detection,
with a Decision Tree retained alongside for interpretation of individual alerts.
Logistic Regression, the weakest model, is best suited as a prototype baseline.

### 8.5 Comparison with the Literature

The findings are consistent with the reviewed literature: ensembles outperform
single classifiers (Gao et al., 2019; Ramu, 2025); classical models achieve
competitive accuracy at much lower cost than deep learning (Berman et al.,
2019; Mahdavifar and Ghorbani, 2019); and dataset quality and imbalance
strongly influence results (Thakkar and Lohiya, 2021; Ozkan-Ozay et al., 2024).
The study extends this literature by quantifying the accuracy-versus-latency
trade-off and by producing concrete deployment guidance (Section 9).

---

## 9. Deployment Guidelines

*The following section reproduces the content of
`reports/deployment_guidelines.md`, adapted for this document.*

### 9.1 Recommended Placement

For a first deployment the recommended placement is **passive, on a SPAN or
mirror port**: the switch copies every packet to a monitoring port without
touching live traffic. A feature extractor converts packets into the same 78
(CICIDS-style) or 41 (NSL-KDD-style) features used in training; the **saved**
preprocessor transforms them identically; the model returns class
probabilities; and a threshold determines whether an alert reaches the SOC
queue. Passive-first deployment means a model error cannot disrupt live
traffic; inline blocking should only be considered after the false-positive
rate has been judged acceptable, and ultimately remains a human decision.

### 9.2 Production Architecture

The prediction pipeline must remain identical to training:

```
raw packet/flow → feature extraction → saved preprocessor
  (Inf→NaN, median imputation, min-max scaling, one-hot)
  → XGBoost.predict_proba() → threshold → alert / no-alert
```

The most common production failure is feature drift at the boundary between
training and inference; in this repository the fix is structural — the API
loads the saved preprocessor and never re-fits one.

### 9.3 Model Selection for Deployment

**Table 7.** Recommended model choice by deployment goal.

| Goal | Choice | Evidence |
|---|---|---|
| Highest detection accuracy on modern data | **XGBoost** | CICIDS2017 F1 0.9897, accuracy 0.9988, AUC 1.0000, ~0.002–0.007 ms/row |
| Explainability (audit/compliance) | **Decision Tree** | F1 0.9505 on CICIDS2017; every decision is a readable yes/no tree |
| Fast prototype baseline | Logistic Regression | F1 0.8267 on CICIDS2017; weak on NSL-KDD rare classes |

### 9.4 Retraining Cadence

Two triggers are recommended: **scheduled retraining** (monthly or quarterly,
on newly labelled traffic rather than the original benchmark) and **triggered
retraining** in response to concept drift, detected via (i) PSI (Population
Stability Index) on `predict_proba()` exceeding 0.25 against a baseline window;
(ii) alert rate moving more than ±30% from a 30-day rolling baseline for two
consecutive weeks; or (iii) observation of a new attack family. Retraining in
this project is a single command (`python -m src.models.train`), preserving the
no-leakage discipline.

### 9.5 Monitoring

Key monitoring signals are the input features (for drift and data-quality
errors), the `predict_proba` distribution (PSI), the alert rate against its
baseline, sampled analyst-reviewed ground truth, and rolling re-evaluation of
model performance. The backend endpoints return per-class probabilities, which
are the raw material for these monitors and should be logged rather than
discarding the probability vector.

### 9.6 Data-Quality Traps Addressed

The deployment must apply the same data-quality rules that were implemented in
this project: corrupted labels, `Infinity` values, zero-variance columns,
severe class imbalance, and NSL-KDD's difficulty-score leakage were all
identified and handled during data preparation (Section 4.4), consistent with
the warnings of Thakkar and Lohiya (2021).

### 9.7 Operational Checklist

1. Run on a mirror/SPAN port, passive, with analyst review of all alerts.
2. Wire the feature extractor to output the same feature names used in training.
3. Reuse the saved preprocessors — never re-fit.
4. Serve with the FastAPI app behind a reverse proxy with TLS.
5. Log `predict_proba` per row to feed drift monitoring.
6. Set the decision threshold with the SOC using a precision-recall curve.
7. Schedule retraining (quarterly minimum) plus a PSI-based drift trigger.
8. Keep a Decision Tree model for explainability on every alert.
9. Re-run the API test suite after any retraining.
10. Record model version and data version in alert metadata.

---

## 10. Risks, Ethics and Issues

### 10.1 Risks

The risk register from the proposal is carried forward with the outcomes
observed during implementation.

**Table 9.** Risk register and outcomes.

| Risk | Likelihood | Impact | Mitigation | Outcome |
|---|---|---|---|---|
| Dataset unavailable or corrupted | Low | High | Acquire early; backup datasets UNSW-NB15 and KDD Cup 99 | No critical impact; both datasets acquired and validated |
| Model overfitting | Medium | High | k-fold CV, regularisation, ensemble diversity | Mitigated; evidenced by test-set reporting, including the Random Forest train/test gap |
| Computational limitations | Medium | Medium | Google Colab, code optimisation, incremental training | Managed; longest training fit ≈205 s |
| Schedule slippage | Medium | Medium | Phased timeline with buffer weeks in Phases 3 and 4 | Managed within the 16-week plan |

### 10.2 Ethical Issues

- **Data privacy.** The study uses only publicly available, anonymised,
  labelled benchmark datasets containing no personal data. No human
  participants were involved, no personal data were collected, and the research
  is fully compliant with GDPR, requiring no separate ethics board approval. A
  UREC1-style research ethics review form is completed and retained in the
  project records (Finalds.md).
- **Dual-use risk.** The project is limited to *detection* and does not
  document any offensive capability. Dissemination is through academic channels
  with a defensive framing, in line with professional codes of conduct
  (BCS/ACM standards).
- **Research data handling.** Data and code are stored in accordance with
  university policy; raw datasets are large and version-controlled artifacts are
  managed accordingly.

### 10.3 Other Issues

- **Evaluation bias.** A uniform evaluation protocol was applied to every model
  and dataset, and multiple complementary metrics (accuracy, precision, recall,
  F1, AUC-ROC) were reported to avoid over-reliance on any single measure.

---

## 11. Limitations of the Study

1. **Dataset age and synthetic nature.** NSL-KDD (2009) reflects late-1990s
   traffic structure, and CICIDS2017 (2017) is now a decade old; modern traffic
   differs. Neither dataset is a substitute for live organisational traffic.
2. **Algorithm scope.** No deep-learning models were trained or compared. The
   literature (Section 3.1) indicates deep models may outperform classical ones
   on benchmark accuracy, so conclusions about the best possible classifier are
   limited to the four classical algorithms studied.
3. **Cross-dataset transfer untested.** Each model is trained and tested within
   its own dataset; a model trained on CICIDS2017 was not tested on NSL-KDD.
   Mapping the two feature spaces remains future work, so the "cross-dataset
   robustness" contribution is measured by pipeline consistency rather than by
   direct transfer.
4. **Encrypted-traffic features absent.** The flow features used do not
   describe encrypted (TLS) payloads, where a growing share of attacks now
   operate.
5. **Latency measured per row only.** Inference latency was measured for a
   single row; the full feature-extraction-to-alert pipeline latency was not
   measured end-to-end.
6. **Rare-class ceiling.** Despite SMOTE, classes with extremely few real
   examples (52 U2R rows; 11 Heartbleed rows) cannot be fully learned.

---

## 12. Conclusion and Future Work

### 12.1 Conclusion

This study developed, tuned and evaluated four classical machine-learning
classifiers on two complementary intrusion-detection benchmarks. The results
show that XGBoost is the strongest overall model — 0.9897 F1-macro and 1.0000
AUC-ROC on CICIDS2017 with microsecond latency — while the Decision Tree
generalises best to the adversarially-designed NSL-KDD test set. The study
quantified the accuracy-versus-latency trade-off (finding that speed is not the
bottleneck), demonstrated the influence of benchmark design on reported
performance, documented the persistent difficulty of rare attack classes, and
produced actionable deployment guidance. All five stated objectives were
achieved, and a demonstrable, testable system (backend API, dashboard and
panel companion) was delivered alongside the research outputs.

### 12.2 Future Work

1. **Deep-learning comparison.** Train and evaluate CNN/LSTM or transformer
   architectures under the same protocol to quantify the classical-versus-deep
   gap directly.
2. **Newer benchmarks.** Re-run the identical pipeline on newer datasets (e.g.
   CICIDS2019, NF-UNSW) to assess performance on contemporary traffic.
3. **Cross-dataset transfer.** Map the two feature spaces and test
   training-on-one-dataset/test-on-another to measure true cross-dataset
   robustness.
4. **End-to-end feature extraction.** Extend the pipeline to ingest raw packet
   captures (e.g. via Zeek/Suricata flow exporters) so deployment is tested
   end-to-end rather than from pre-extracted features.
5. **Automated feedback loop.** Automate the analyst-correction → retraining
   cycle to keep the deployed model relevant under concept drift.

---

## 13. References

*APA 7th edition. Note: confirm the exact reference style with your supervisor
before final submission.*

- Berman, D. S., Buczak, A. L., Chavis, J. S., & Corbett, C. L. (2019). A
  survey of deep learning methods for cyber security. *Information, 10*(4),
  122. https://doi.org/10.3390/info10040122
- Gao, X., Shan, C., Hu, C., Niu, Z., & Liu, Z. (2019). An adaptive ensemble
  machine learning model for intrusion detection. *IEEE Access, 7*,
  82512–82521.
- Kaur, R., Gabrijelcic, D., & Klobucar, T. (2023). Artificial intelligence
  for cybersecurity: Literature review and future research directions.
  *Information Fusion, 97*, 101804.
- Mahdavifar, S., & Ghorbani, A. A. (2019). Application of deep learning to
  cybersecurity: A survey. *Neurocomputing, 347*, 149–176.
- Moustafa, N., & Slay, J. (2015). UNSW-NB15: A comprehensive data set for
  network intrusion detection systems. In *Military Communications and
  Information Systems Conference (MilCIS)*.
- Ozkan-Ozay, M., Akin, E., Aslan, O., Kosunalp, S., Iliev, T., Stoyanov, I.,
  & Beloev, I. (2024). A comprehensive survey: Evaluating the efficiency of
  artificial intelligence and machine learning techniques on cyber security
  solutions. *IEEE Access, 12*, 22733–22755.
- Ramu, A. (2025). Machine learning for cyber threat detection using historical
  vulnerabilities and security standards. *Journal of Computer and
  Communication Networks, 4*(1), 1–15.
- Salem, A. H., Azzam, S. M., Emam, O. E., & Abohany, A. A. (2024). Advancing
  cybersecurity: A comprehensive review of AI-driven detection techniques.
  *Journal of Big Data, 11*(1), 105. https://doi.org/10.1186/s40537-024-00957-y
- Sharafaldin, I., Lashkari, A. H., & Ghorbani, A. A. (2018). Toward generating
  a new intrusion detection dataset and intrusion traffic characterization. In
  *Proceedings of the International Conference on Information Systems Security
  and Privacy (ICISSP)* (pp. 108–116).
- Tavallaee, M., Bagheri, E., Lu, W., & Ghorbani, A. A. (2009). A detailed
  analysis of the KDD CUP 99 data set. In *IEEE Symposium on Computational
  Intelligence for Security and Defense Applications (CISDA)*.
- Thakkar, A., & Lohiya, R. (2021). A review of the advancement in intrusion
  detection datasets. *Procedia Computer Science, 167*, 636–645.

---

## 14. Appendices

### Appendix A. Glossary

A plain-language glossary of technical terms used in this thesis is provided in
`docs/PROJECT_UNDERSTANDING_GUIDE.md` (Section 9) and in `GLOSSARY.md`. Key
terms: feature, label, class, training set, test set, overfitting,
generalisation, hyperparameter, grid search, k-fold cross-validation,
stratified folds, class imbalance, SMOTE, data leakage, imputation, min-max
scaling, one-hot encoding, feature selection, Logistic Regression, Decision
Tree, Random Forest, XGBoost, bagging, boosting, confusion matrix, accuracy,
precision, recall, F1, AUC-ROC, latency, DoS/DDoS, Probe, R2L, U2R, Brute
Force, Web Attack, Botnet, Heartbleed, signature-based detection, anomaly
detection, zero-day, SPAN/mirror port, SOC, concept drift, PSI, FastAPI,
Uvicorn, React, Vite, Recharts, joblib, scikit-learn, xgboost,
imbalanced-learn, EDA, pipeline, registry, inference, reproducibility.

### Appendix B. Project File and Folder Structure

```
D:\Cyber threat Detection\
├── data/
│   ├── raw/            datasets (NSL-KDD, CICIDS2017) + DATASET_MANIFEST.md
│   └── processed/      cleaned splits, preprocessors, label encoders,
│                       evaluation_results.json
├── src/
│   ├── data/           loader.py, preprocess.py, feature_selection.py
│   ├── models/         train.py, evaluate.py, registry/ (8 models + metadata)
│   ├── api/            main.py, schemas.py (FastAPI backend)
│   └── utils/          config.py, generate_docs.py
├── notebooks/          01_eda, 02_preprocessing, 03_model_training, 04_evaluation
├── reports/            model_comparison_report, deployment_guidelines,
│                       dataset_selection_justification, eda_report,
│                       examiner_qa, figures/
├── tests/              test_api.py (14 tests)
├── frontend/           React + Vite + Recharts dashboard
├── research_panel_project/  DB-backed panel companion (SQLite)
├── docs/               submission-ready documentation
├── README.md, SETUP_GUIDE.md, GLOSSARY.md, P2633978.md (proposal), Finalds.md
└── requirements.txt    pinned package versions
```

### Appendix C. Key Code Snippets

The complete, runnable code is available in the project repository. The most
relevant entry points are:

- Pipeline definition (SMOTE inside the training pipeline):
  `src/models/train.py` (grid search with `StratifiedKFold`, `f1_macro`).
- Preprocessing: `src/data/preprocess.py` (median imputation, min-max scaling,
  one-hot encoding, fitted on training data only).
- Evaluation: `src/models/evaluate.py` (accuracy, precision, recall, F1,
  AUC-ROC, per-class metrics, latency).
- API: `src/api/main.py` (endpoints `/models`, `/compare`, `/attack-info`,
  `/predict`, `/simulate`).

### Appendix D. Repository

The full project repository is hosted on GitHub. Link: [insert GitHub
repository URL here — currently provided on request].

---

*This thesis document was generated from the project's actual code, results and
reports. Tables 2–7 are reproduced from `models_metadata.json` and
`evaluation_results.json`; Section 9 adapts `reports/deployment_guidelines.md`;
Section 5 adapts `reports/dataset_selection_justification.md`.*
