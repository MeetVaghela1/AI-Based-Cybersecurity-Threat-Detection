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
