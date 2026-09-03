# Project Understanding Guide

A document written to teach you, from zero background, exactly how your own
project works — so you can explain and defend it in front of a research
committee without reading from a script.

Every number in this guide is real: it comes from `evaluation_results.json`,
`models_metadata.json`, the reports in `reports/`, and the project walkthrough.
Nothing here was invented to look better.

Read it in order. Section 1 is the one-paragraph answer; sections 2–4 build the
knowledge to understand sections 5–6; section 7 is the software; section 8 is
for the committee itself.

---

## 1. The 60-second version

Imagine a security guard whose job is to look at every conversation that
happens on a company's network and decide: "is this person doing something
normal, or are they attacking us?" That guard has to do it for millions of
conversations, in a split second each.

This project trains **computer programs** to be that guard. We give each
program thousands of examples of network conversations that are already labelled
"normal" or "attack type X", let it learn the patterns by itself, and then test
it on conversations it has never seen before. We trained four different kinds of
program ("algorithms") on two different sources of traffic data, and measured
which one catches attacks best and how fast it can decide.

Why it matters: attacks change constantly, and the old way of defending
networks — matching traffic against a list of known attack "fingerprints" —
is blind to anything new. A program that learns patterns from data can, in
principle, flag things it has never seen. This project works out how well four
practical, cheap-to-run machine-learning programs actually do at that job on
two benchmark datasets, and what it would take to put one of them inside a real
company's network.

**The honest headline:** on modern, realistic traffic (CICIDS2017), the best
model — XGBoost — correctly classifies 99.88% of the test conversations it had
never seen. On the old, deliberately-hard benchmark (NSL-KDD), the best test
score is lower (a 0.617 F1 for Decision Tree) — and that drop is partly a
feature of the benchmark, which hides attack variants it never showed the
models. Both results are reported honestly, because both tell you something true
about how well these models generalise.

---

## 2. Core concepts first (the beginner layer)

Before we touch your project, you need five ideas. Each is explained with a
small concrete example, not a definition.

### 2.1 What "machine learning classification" means

A "classifier" is a program that takes something described by numbers and
assigns it to one of a set of named categories ("classes").

Concrete example: an email spam filter. It reads an email's features — how many
links, how many capital letters, which words appear — and outputs either
"spam" or "not spam". Nobody writes down every spam rule by hand; instead the
program **learns the pattern from labelled examples**. That is machine learning:
instead of being told the rules, the program figures out the rules from data.

Your project is exactly this, with the categories being **traffic classes**
("Normal", "DoS", "Probe", "R2L", "U2R" on one dataset; nine classes on the
other) and the input being a network connection described by numbers.

### 2.2 What "network intrusion detection" means

A **network** is computers talking to each other. Each "conversation" — a
connection, or a **flow** — can be measured: how many packets went back and
forth, how many bytes, how long it lasted, what protocol was used.

**Intrusion detection** is the job of watching that traffic and spotting the
connections that are an attack: someone flooding a server with traffic (DoS),
probing for weaknesses (Probe), stealing a login (R2L / Brute Force), or
exploiting a website (Web Attack).

The old approach — **signature-based detection** — checks every connection
against a database of known attack fingerprints. It's like a bouncer checking
IDs against a list of known criminals: great if the criminal is on the list,
useless if they aren't. New attacks (zero-days, modified malware) have no
signature yet. Machine-learning detection instead asks "does this look like the
patterns of attack I've learned?", which is why it's the modern answer.

### 2.3 What a dataset, a feature, and a label are

- **Dataset** = a big table of examples. Each row is one network connection.
- **Feature** = one measurable column of that table — one thing we know about
  the connection (duration, bytes sent, number of TCP flags, ...).
- **Label** = the correct answer attached to each row — what that connection
  *really* was ("Normal", "DoS", ...). Labels come from the people who built the
  dataset.

Real example, from your NSL-KDD test set (row 0, true label **DoS**). The model
sees 122 numbers like these:

| Feature | Value | What it means |
|---|---|---|
| `rerror_rate` | 1.0 | fraction of connections to the same service with "REJ" (rejected) errors = 100% |
| `srv_rerror_rate` | 1.0 | same, for connections to same service+host |
| `dst_host_count` | 1.0 | how many connections went to the same host |
| `dst_host_rerror_rate` | 1.0 | reject-error rate at the destination host |
| `protocol_type_tcp` | 1.0 | this connection used TCP |
| `flag_REJ` | 1.0 | the connection was rejected |
| `service_private` | 1.0 | it was a connection to a "private" service |

A human reads this instantly: *everything is being rejected, everywhere*. That
is the fingerprint of a flood attack. A machine-learning model learns that same
connection the statistical way — it sees "rows where `rerror_rate` is high
tend to be DoS" thousands of times and memorises the pattern in the numbers.

Real example, from your CICIDS2017 test set (row 0, true label **DDoS**):

| Feature | Value | What it means |
|---|---|---|
| `ack_flag_count` | 1.0 | count of packets with the ACK flag set |
| `min_seg_size_forward` | 0.3846 | smallest packet size sent forward |
| `flow_duration` | 0.0419 | how long the flow lasted |
| `fwd_iat_total` | 0.0419 | total time between forward packets |
| `flow_iat_max` | 0.0419 | maximum time between any two packets |

(The values are scaled to 0–1, which is why they're small decimals — see §5.)

### 2.4 What "training vs testing" means

You split the data into two piles:

- **Training set** — the pile the model is *allowed to look at* while learning.
  It reads these examples over and over to figure out the pattern.
- **Test set** — the pile locked away in a drawer. The model never sees it
  during training. Only at the very end do you open the drawer and ask: "OK,
  you've learned from the training pile — how well do you do on these ones you
  have never seen?"

Why the test set matters: any model can score 100% on data it already memorised
— that proves nothing. The test set is the honest "exam". If a model scores well
on the exam, it has genuinely **generalised** (learned the pattern), not just
memorised.

One crucial rule you followed throughout: **never let information from the test
set reach the model during training.** That would be "data leakage" and would
make your results fake-good. You were disciplined about this in three places
(§5).

### 2.5 How you judge a classifier (the four numbers)

Given a pile of predictions, you compare them to the true labels:

- **Accuracy** = how many answers were right, out of all answers.
- **Precision** = of the things the model *called* an attack, how many really
  were. (How much to trust an alarm.)
- **Recall** = of the attacks that *really happened*, how many it caught. (How
  few it missed.)
- **F1** = one balanced number combining precision and recall. F1-**macro**
  averages F1 over every class equally, so a rare attack class counts as much
  as the huge "Normal" class.

Accuracy alone is a trap on imbalanced data (§2.6). That's why your whole
project is scored with F1-macro as the headline number.

### 2.6 The trap: class imbalance

Your datasets are mostly "Normal" traffic with a tiny slice of attacks. Real
numbers from your EDA:

- CICIDS2017: **2,273,097 Normal** flows vs **11 Heartbleed** rows. *Eleven.*
- NSL-KDD: 67,343 Normal vs **52 U2R** and 995 R2L.

A lazy model that answers "Normal" to everything would score **80.3% accuracy
on CICIDS2017** while catching *zero* attacks. That is why you report precision,
recall, F1 and AUC as well, balance the training data with SMOTE (§5), and use
stratified cross-validation. This imbalance *is* part of the research problem,
not a side-note.

---

## 3. The four algorithms

For each: plain English, then a bit more rigour, then **why it behaved the way
it did on your actual numbers**.

### 3.1 Logistic Regression

**Plain:** the simplest classifier. It learns a set of weights — "how much does
each feature push the answer toward 'attack'?" — and combines them into a
probability for each class. Think of it drawing straight lines through the
data and putting each point on whichever side of the lines it falls.

**Rigorous:** a linear model. For each class it computes a weighted sum of the
features (`w₁·x₁ + w₂·x₂ + ...`) and passes it through a softmax/sigmoid to get
a probability. Because the decision boundary is a hyperplane, it can only
separate classes that are roughly linearly separable. It's fast to train and
fully explainable (you can read the weights), which is why it's your baseline.

**On your results:** it's the honest baseline everywhere.
- CICIDS2017: F1 **0.8267** — respectable, because CICIDS classes are fairly
  separable after scaling, and it ranks well (AUC 0.9784).
- NSL-KDD: F1 **0.5572**, and R2L recall is only **0.1344**. R2L attacks are
  remote logins that look superficially *like normal traffic*; a straight-line
  boundary cannot separate them from Normal. This is the classic linear-model
  ceiling, and it's exactly why you needed the non-linear models.

### 3.2 Decision Tree

**Plain:** a flowchart of yes/no questions. "Is `rerror_rate` > 0.5? If yes, is
`flag_REJ` = 1? If yes → DoS." Every prediction is a readable path, so you can
open it up and see exactly *why* it decided what it decided.

**Rigorous:** greedy recursive partitioning. At each node it picks the feature
and threshold that best splits the training data into purer class groups (using
Gini impurity or entropy). It repeats down the tree, stopping when a node is
pure enough or when depth/leaf limits are hit. A single tree is powerful but
can **overfit** — it can memorise the training data's quirks.

**On your results:** the surprise winner on the hard benchmark. On the NSL-KDD
test set it has the **best F1 (0.6170)** and the best accuracy (0.8163), with
the highest R2L recall of any model (**0.2338**). Its boundaries are
axis-aligned "if this feature, then that class" rules, which happen to match
how NSL-KDD attack variants differ from training. But its AUC is the *lowest*
(0.7672) — trees don't produce well-calibrated probabilities, so they rank
poorly even when their argmax decision is right. On CICIDS2017 it's also strong
(F1 0.9505) and it's the fastest model (0.0004 ms/row) and the most explainable
— that's why it's your "explainability companion" model for deployment.

### 3.3 Random Forest

**Plain:** a crowd of many decision trees. Each tree is trained on a random
slice of the data and a random subset of features, then they all vote. One tree
might overfit; a crowd averaging out each other's mistakes is much more robust.

**Rigorous:** a bagging ensemble. It builds N trees, each on a bootstrap sample
of the training data, each split considering only a random subset of features.
The prediction is the majority vote (or mean probability). This variance
reduction is what usually makes it beat a single tree.

**On your results:** great in cross-validation, but it trips on the adversarial
test set. On NSL-KDD CV it scores **0.9333** (second only to XGBoost), yet on
the *test* set its F1 collapses to **0.5384** with the worst R2L recall
(**0.1112**). Why: it memorised the training distribution's attack *variants*
extremely well, and the test set deliberately contains new variants — so its
extra capacity hurt rather than helped. On CICIDS2017, where the test
distribution matches training, it's excellent (F1 0.9276, recall 1.0 on
Botnet). The message: Random Forest is a fantastic model when the world doesn't
change, and the NSL-KDD test set is a world that *does* change.

### 3.4 XGBoost

**Plain:** a team of trees where each new tree's job is to fix the mistakes the
previous trees made. Like a class where each teacher focuses on what the
students got wrong last time. It also builds in safeguards against overfitting.

**Rigorous:** a gradient-boosted ensemble. Trees are trained *in sequence*;
each one fits the "residual" error of the current combined model (gradient
descent in function space). Regularisation terms (on tree complexity and leaf
scores) tame overfitting, and it natively handles class imbalance well via
sample weighting and its sequential error-correction. In practice it is one of
the strongest classical classifiers in the literature — e.g. Ramu (2025)
reports XGBoost outperforming other classical ML on threat detection.

**On your results:** the best *all-round* model. Highest AUC on both datasets
(0.9491 NSL-KDD, **1.0000** CICIDS2017) and the best CICIDS2017 test F1
(**0.9897**, accuracy 0.9988). On the rare classes it is the most balanced:
NSL-KDD U2R recall **0.2537** and R2L **0.1538** are the highest among the
ensemble family. On NSL-KDD test F1 it is a close second (0.6086 vs the tree's
0.6170) — but its AUC and rare-class handling make it the model you'd actually
deploy, with the Decision Tree kept alongside for explanations.

**One-line summary of the results story:** *simple model = simple ceiling
(Logistic), single tree = interpretable but shaky probabilities (best F1 on the
hard set), bagged crowd = strong but brittle to novelty (Random Forest), boosted
crowd = strongest and most robust (XGBoost).*

---

## 4. My datasets, explained

### 4.1 NSL-KDD (2009)

- **What it is:** the cleaned, de-duplicated successor to the famous **KDD Cup
  '99** dataset — 1990s-era simulated traffic on a US Air Force network. The
  KDD Cup '99 data had so many duplicate rows that models could "cheat"; NSL-KDD
  (Tavallaee et al., 2009) removed the duplicates so scores became meaningful.
- **Shape:** 41 features, 5 classes (Normal, DoS, Probe, R2L, U2R). Your train
  file has 125,973 rows; your test file has 22,544 rows.
- **Its famous quirk:** the official test set deliberately contains attack
  *variants* that never appeared in training. The test is an adversarial exam
  on purpose. Your train→test score drop (e.g. XGBoost 0.9565 CV → 0.6086 test)
  is *the benchmark doing its job*: measuring survival against unseen attacks.
- **Imbalance:** 67,343 Normal, 45,927 DoS, 11,656 Probe, 995 R2L, **52 U2R**.

### 4.2 CICIDS2017 (2017)

- **What it is:** real traffic captured at the Canadian Institute for
  Cybersecurity over five days in 2017, using realistic network topology and
  modern attack tools (brute force, DDoS, web attacks, botnets, heartbleed).
  Built and documented by Sharafaldin et al. (2018).
- **Shape:** 78 numeric flow features, 9 classes (Normal, Botnet, Brute Force,
  DDoS, DoS, Heartbleed, Infiltration, PortScan, Web Attack). ~2.83M raw flows.
- **Imbalance, extreme:** 2,273,097 Normal (80.3%) vs **11 Heartbleed** and 36
  Infiltration rows.
- **Real-world messiness:** corrupt labels (a broken Unicode character in
  "Web Attack"), `Infinity` values from division-by-zero rate columns, 8
  constant ("zero-variance") columns, and near-duplicate correlated features.

### 4.3 Why these two — and not the others

From `reports/dataset_selection_justification.md`:

- **Complementary by design.** NSL-KDD (2009) is the classic, widely-cited
  academic benchmark; CICIDS2017 (2017) is modern and realistic. Together they
  span roughly two decades of traffic evolution, and — crucially — let you test
  the same pipeline on two very different distributions, which is exactly the
  "cross-dataset robustness" gap in your literature review.
- **Comparability.** NSL-KDD is one of the most-benchmarked IDS datasets, so
  your results can be compared directly against a huge body of prior work.
- **Feasibility.** Alternatives were rejected for concrete reasons: KDD Cup '99
  is outdated and redundant; UNSW-NB15 is partly synthetic; CSE-CIC-IDS2018 is
  100GB+ and impractical for a 16-week Google Colab project; Bot-IoT/TON_IoT are
  IoT-specific, not general enterprise traffic.
- Both are **public, anonymised, labelled** — which also keeps the ethics
  approval simple (see §8, question 13).

### 4.4 What's inside one row — real examples

The model does not see raw packets; it sees one row of numbers per connection.
Two genuine rows from your test sets (the model was never trained on these):

**NSL-KDD row 0 — true label: DoS** (122 features; these are the 8 with the
largest values):

| Feature | Value | Meaning |
|---|---|---|
| `rerror_rate` | 1.0 | 100% of connections to this service returned "rejected" |
| `srv_rerror_rate` | 1.0 | same, measured on service+host |
| `dst_host_count` | 1.0 | many connections to the same destination host |
| `dst_host_rerror_rate` | 1.0 | 100% rejected at the destination |
| `dst_host_srv_rerror_rate` | 1.0 | 100% rejected, same service |
| `protocol_type_tcp` | 1.0 | TCP protocol |
| `service_private` | 1.0 | connection to a "private" service |
| `flag_REJ` | 1.0 | the connection was rejected |

*Reading it like a human:* everything is rejected everywhere → a flood attack.

**CICIDS2017 row 0 — true label: DDoS** (78 features; largest values):

| Feature | Value | Meaning |
|---|---|---|
| `ack_flag_count` | 1.0 | many ACK-flagged packets (a DDoS technique) |
| `min_seg_size_forward` | 0.3846 | smallest forward packet size |
| `flow_duration` | 0.0419 | short flow duration |
| `fwd_iat_total` | 0.0419 | tight spacing of forward packets |
| `flow_iat_max` | 0.0419 | tiny maximum inter-packet gap |

*Reading it:* a very short, very regular burst of ACK packets — the shape of an
automated flood, not a human browsing.

---

## 5. My pipeline, walked through like a story

Follow one real data point from raw file to the dashboard. In square brackets
is the "why" behind each step — the reasoning you'd give in a committee.

**Step 1 — Raw file.**
NSL-KDD arrives as a text file of comma-separated values; CICIDS2017 as a
folder of CSVs, ~2.83M rows. *[Why two datasets: cross-dataset robustness is a
named research gap — one dataset could flatter one algorithm.]*

**Step 2 — Load and clean** (`src/data/loader.py`).
- NSL-KDD: the file has a 43rd column, a "difficulty score". It is metadata,
  not traffic — **dropped**. *[Why: if kept, the model would "cheat" by learning
  "hard rows are attacks". A classic leakage trap.]*
- CICIDS2017: a corrupted label character in "Web Attack" is fixed (otherwise
  an entire attack class silently disappears), `Infinity` cells become missing
  values, and 8 constant columns are dropped. *[Why: garbage in → garbage out.
  A single broken character destroyed a class; constant columns carry zero
  information.]*
- CICIDS2017 is so imbalanced that random sampling would delete the rare
  classes, so the loader **caps** big classes at 15,000 rows while keeping
  every rare-class row → 62,422 rows. *[Why: you can't learn Heartbleed from 0
  examples, but you don't need 2.27M Normal rows to learn Normal.]*

**Step 3 — Preprocess** (`src/data/preprocess.py`).
One fixed pipeline, **fitted on the training set only**: `Inf → NaN`, median
imputation, min-max scaling to [0,1], and one-hot encoding of NSL-KDD's text
columns (which grows it from 41 to **122** columns). The fitted preprocessor is
**saved to disk**. *[Why fitted on training only: scaling/encoding must not peek
at the test set. Why saved: the live API must transform a real packet with the
exact same maths as training — otherwise results silently degrade. Why one-hot:
models can't read "tcp" as text.]*

**Step 4 — Label-encode.**
`LabelEncoder` turns attack names into numbers; the encoder is saved so the API
can decode predictions back to names. *[Why saved: the API must decode
identically to training.]*

**Step 5 — Balance with SMOTE (training only).**
SMOTE creates synthetic examples of rare classes by interpolating between
neighbouring real ones. NSL-KDD: R2L and U2R boosted to 15,000 each →
154,926 rows. CICIDS2017: all 9 classes balanced to 12,000 each → 108,000
rows. SMOTE is built *inside* the training pipeline, **inside the CV folds**
(with `k_neighbors=3`), so it is refitted on each fold's training portion and
never sees a validation fold. *[Why: unbalanced data makes models learn
"everything is Normal". Why inside folds: SMOTE-ing before splitting would let
synthetic rows leak into validation and inflate scores — the single most
common IDS evaluation mistake.]*

**Step 6 — Feature selection** (`src/data/feature_selection.py`).
Three independent methods rank the features — Pearson correlation, mutual
information, recursive feature elimination — on the **pre-SMOTE training data**.
The winners make domain sense: `src_bytes` dominates NSL-KDD; packet/flow-size
features (`average_packet_size`, `packet_length_mean`) dominate CICIDS2017.
*[Why three methods: mutual information catches non-linear relationships that
correlation misses; agreement across methods = confidence. Why pre-SMOTE:
selecting features on synthetic data would be dishonest.]*

**Step 7 — Train and tune** (`src/models/train.py`, notebooks 01–04).
Eight models (4 algorithms × 2 datasets) are tuned with **grid search +
stratified 5-fold cross-validation**, scored on **F1-macro**, with SMOTE inside
the folds. Fixed random seed **42** everywhere. Every model is saved to
`src/models/registry/` with its metadata (CV score, latency, best
hyperparameters, trained-at timestamp). *[Why stratified: folds keep the same
class proportions as the full data, vital when a class has 52 rows. Why
F1-macro: rare classes must weigh as much as Normal. Why seed 42: reproducible
science — an examiner can rerun and get the same numbers.]*

**Step 8 — Predict (inference).**
The API loads the saved models and preprocessor. A test row (or a live packet)
goes through the same preprocessor → the model outputs a probability for every
class → the highest wins. *[Why lazy loading + caching: first request is slow,
all later ones are fast.]*

**Step 9 — The dashboard.**
The React dashboard calls `POST /simulate` every 1.6 s; the backend picks real
rows from the *test set*, classifies them, and sends back JSON with the
prediction, confidence, all class probabilities, the dataset's true label, and
whether they match. The UI shows a live-monitor feed, comparison charts, and an
attack library. It carries a clear **"SIMULATED TRAFFIC"** badge. *[Why the
badge: the demo replays recorded test rows — it is not capturing your real
network. Honesty matters in demos as much as in evaluation.]*

**The no-leakage discipline, in one sentence:** *preprocessors and SMOTE are
fitted on training data only; SMOTE lives inside CV folds; the test set is
touched only once, at the very end, for the final exam.*

---

## 6. My actual results, explained and interpreted

All numbers below are from `evaluation_results.json`. "Test" always means the
untouched test set the models never trained on.

### 6.1 Cross-validation (during tuning)

Mean F1-macro over 5 stratified folds:

| Dataset | Logistic | Decision Tree | Random Forest | XGBoost |
|---|---:|---:|---:|---:|
| NSL-KDD | 0.7432 | 0.8907 | 0.9333 | **0.9565** |
| CICIDS2017 | 0.8755 | **0.9908** | 0.9765 | 0.9848 |

*What this tells you:* all models can learn the *training* distribution well —
even Logistic gets ~0.74–0.88. The CV numbers are the models at their most
flattering; the test set is the reality check.

### 6.2 NSL-KDD test set (22,544 rows)

| Model | Accuracy | Precision | Recall | F1 | AUC | Latency (ms/row) |
|---|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 0.7628 | 0.6707 | 0.6295 | 0.5572 | 0.9057 | 0.0008 |
| Decision Tree | 0.8163 | 0.7545 | 0.5836 | **0.6170** | 0.7672 | 0.0006 |
| Random Forest | 0.7488 | 0.7972 | 0.5081 | 0.5384 | 0.9489 | 0.0089 |
| XGBoost | 0.7782 | 0.8281 | 0.5653 | 0.6086 | **0.9491** | 0.0027 |

Per-class recall (share of each true class that was caught):

| Class | Logistic | Decision Tree | Random Forest | XGBoost |
|---|---:|---:|---:|---:|
| DoS | 0.8105 | 0.9005 | 0.7604 | 0.8202 |
| Normal | 0.9233 | 0.9616 | 0.9730 | 0.9731 |
| Probe | 0.7270 | 0.6877 | 0.5915 | 0.6258 |
| **R2L** | 0.1344 | 0.2338 | 0.1112 | 0.1538 |
| **U2R** | 0.5522 | 0.1343 | 0.1045 | 0.2537 |

*Plain-language reading, number by number:*

- **Decision Tree wins F1 (0.6170)** — on this adversarial test set, its simple
  axis-aligned rules generalise better than the more powerful ensembles. But its
  **AUC is lowest (0.7672)**: a tree is confident about its single answer and
  bad at *ranking* — AUC and F1 are measuring different things here.
- **XGBoost's AUC (0.9491) is nearly Random Forest's (0.9489)** and far above
  the tree's. If you need a *probability* you can threshold, boosted models win.
- **Random Forest collapses on test (0.5384)** despite 0.9333 CV. That's the
  unseen-variant effect — its memorised patterns don't transfer to new attack
  variants. This is the single most instructive number in the whole project.
- **R2L recall is 0.11–0.23 everywhere.** R2L is a *remote login* that looks
  nearly identical to normal traffic (R2L has only 995 training rows and its
  test variants are new). A model can barely separate it from Normal — this is
  the honest hard limit, and Tavallaee et al. (2009) documented exactly this
  class as the benchmark's persistent weak point.
- **U2R is interesting:** Logistic's U2R *recall* (0.5522) is highest, but its
  U2R *precision* is only 0.0862 — it cries wolf, flagging lots of Normal as
  U2R. The tree/XGBoost are precise but miss more (recall 0.13–0.25). Rare
  classes force this trade-off.

### 6.3 CICIDS2017 test set (15,606 rows)

| Model | Accuracy | Precision | Recall | F1 | AUC | Latency (ms/row) |
|---|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 0.9549 | 0.8391 | 0.8622 | 0.8267 | 0.9784 | 0.0006 |
| Decision Tree | 0.9972 | 0.9951 | 0.9257 | 0.9505 | 0.9629 | 0.0004 |
| Random Forest | 0.9970 | 0.9925 | 0.8944 | 0.9276 | 0.9919 | 0.0063 |
| XGBoost | 0.9988 | 0.9974 | 0.9832 | **0.9897** | **1.0000** | 0.0067 |

*Plain-language reading:*

- **XGBoost wins outright** — 0.9988 accuracy, **0.9897 F1**, AUC **1.0000**,
  and it's the *only* model to get Heartbleed recall to **1.0000** (the others
  all hit 0.5000). Its sequential error-correction handles the tiny classes.
- **Why is CICIDS2017 "easy" while NSL-KDD is "hard"?** Because CICIDS2017's
  test distribution closely matches its training distribution. A model well
  fitted to CICIDS training stays well fitted on CICIDS test. NSL-KDD's test is
  adversarial by design. The two datasets measure different things — fit to your
  own data vs survival of novelty — and *the gap itself is a research finding
  about benchmark design*.
- **Rare classes still wobble:** Heartbleed recall is 0.50 for three of the
  four models (11 rows in the whole dataset), and Infiltration recall 0.57–0.86.
  SMOTE helps, but a model cannot fully learn a class it has almost never seen.

### 6.4 The accuracy-vs-latency finding (the project's own research gap)

Every model classifies a row in well under **0.01 ms** (0.0003–0.0089 ms/row).
Even the slowest model is orders of magnitude faster than a 10 Gbps link
produces rows. So *latency is not the bottleneck* — the bottleneck in a real
deployment is feature extraction, which lives outside the model. **The
trade-off that actually matters in your data is accuracy vs explainability, not
accuracy vs speed.** Logistic Regression is the weakest model; there is no case
where a bigger model buys accuracy at a cost you can feel. That is a clean,
defensible conclusion for a committee.

### 6.5 Which one would you deploy?

**XGBoost for detection** (best accuracy + near-zero latency + best rare-class
handling), **with a Decision Tree running alongside purely for explainability**
— when an alert fires, an analyst can read the tree's path and understand the
"why". Logistic Regression remains a prototype baseline.

### 6.6 How much did tuning actually help? (bonus analysis)

`reports/tuning_impact_report.md` compares each model at default hyperparameters
vs. the grid-searched saved model, on the same test set. Honest findings:

- **XGBoost and Logistic Regression clearly benefit** (CICIDS2017 LR F1
  0.791 → 0.827 via `C=10`; XGBoost 0.979 → 0.990).
- **Random Forest is indifferent** — its defaults (100 trees, no depth limit)
  are already strong; on NSL-KDD tuning *hurt* test F1 slightly (0.557 → 0.538),
  a classic sign the tree budget was better spent on `n_estimators` than on the
  depth grid.

`reports/development_progression_report.md` shows the same pipeline grown
step-by-step for Logistic Regression (raw → cleaned → feature-selected → SMOTE
→ tuned): cleaning + class-balancing deliver the lift, aggressive consensus
feature selection hurts LR (too few features), and tuning is the smallest step.
`reports/model_dataset_usage_statistics.md` tabulates every dataset/model size,
grid size, fit time, CV score and latency used in the experiment.

---

## 7. My system architecture, explained

Think of it as three rooms connected by pipes.

**Room 1 — the research pipeline (notebooks + `src/`).** Where the science
happens: `src/data/` cleans and preprocesses, `src/models/` trains, tunes and
evaluates the 8 models, everything is saved into `src/models/registry/` and
`data/processed/`. This room runs once per training run.

**Room 2 — the backend (`src/api/`, FastAPI).** The "brain behind the screen".
It loads the *saved* models and preprocessor and answers questions over HTTP:
`GET /models` (list models + metrics), `GET /compare` (chart data), `GET
/attack-info/{type}` (plain-language attack explanations), `POST /predict`
(classify one connection), `POST /simulate` (replay real test rows as a "live"
feed), `GET /docs` (interactive API docs). Models load lazily and are cached.

**Room 3 — the dashboard (`frontend/`, React + Vite + Recharts).** What you
click. Four tabs: **Live Monitor** (polls `/simulate` every 1.6 s, shows up to
28 flows with verdict pills, confidence bars, correct/wrong markers, a
"SIMULATED TRAFFIC" badge, and a **Stored prediction log** panel below that
lists every flow the monitor classified — saved server-side to
`data/processed/prediction_log.json`, max 200 entries), **Model Comparison**
(bar + radar charts, scoreboard and latency tables — including a **live**
latency column averaged from the prediction log while monitoring runs — plus
the tuning-impact analysis and the training-curve / development-progression
charts, which are **interactive** (hover tooltips, clickable legends, a dashed
reference line at the saved model's setting, a true numeric x-axis, a
NSL-KDD / CICIDS2017 / "Compare both" overlay, and a red overfitting band on
the Decision Tree depth chart)), **Database** (the full stored
prediction log with dataset/verdict filters and summary statistics, refreshed
every two seconds), and **How It Works** (the methodology in plain
language + an attack library).
The monitoring loop lives in a React context shared by all tabs, so the stream
keeps running while you browse and the Database tab stays live.
First-time users get a **self-guided 10-step spotlight tour** (auto-starts on
every page load, and replayable via the "Take the tour" button), inline
**"?" help tooltips** on the controls and counters, and a friendly **empty
state** on the Live Monitor that invites them to start the stream.

**How they talk:** the dashboard sends an HTTP request (e.g. `POST /simulate`);
the backend classifies and returns JSON; the dashboard renders it. In dev, Vite
(on :5173) proxies `/api` to the backend; in production the backend **serves
the built dashboard from `/`** — one `uvicorn` process runs the whole demo. The
frontend's `api.js` picks `/api` in dev and the root path in production
(`import.meta.env.DEV`).

**Why the separation?** (a) The model doesn't care what the screen looks like —
cleanly separating science from interface means you can swap the dashboard or
the model without rebuilding the other. (b) The API is reusable: any client
(React, a SOC tool, a script) can call the same endpoints. (c) The lazy-loaded,
cached backend keeps response times fast for a demo.

**And the panel companion:** a second project, `research_panel_project/`, wraps
the same models behind a DB-backed FastAPI app with a SQLite database
(`predictions` table) that logs *every* live detection — a verifiable,
"under-the-hood" view you can query in any SQLite viewer during a committee
demonstration.

**Quality gate:** `tests/test_api.py` + `tests/test_panel_api.py` — **19 tests, all passing** — cover every
endpoint.

---

## 8. Likely committee questions, with your own answers drafted

Say these in your own words. They are built from the *actual* decisions and
numbers in the repo.

1. **Why these four algorithms?**
   "They form a deliberate ladder: Logistic Regression as the simple baseline,
   Decision Tree for explainability — you can literally read its decisions —
   and Random Forest and XGBoost as the two ensemble families. The ensemble
   literature (Gao et al., 2019; Ramu, 2025) consistently shows these two are
   the strongest classical approaches. That spread lets me measure the
   simple-to-complex accuracy trade-off, which is the point of the project.
   (Why I did NOT also pick SVM, k-NN, Naive Bayes or deep learning — the
   "negative case" — is answered in question 3.)"

2. **Why not deep learning?**
   "The literature (Berman et al., 2019) shows deep learning often wins on raw
   benchmark accuracy but at high computational and interpretability cost, and
   Gao et al. (2019) argue ensemble methods are competitive and much cheaper.
   For a 16-week project, the four classical models let me control the
   experiment rigorously — grid search, interpretability, latency measurement —
   and still hit 0.99 F1 on CICIDS2017. Comparing against deep learning is
   explicitly listed as future work."

3. **Why these four algorithms and not deep learning / SVM / other classifiers?**
   "I have a positive case (the ladder in question 1) and a negative case (the
   exclusions). Deep learning is excluded on compute and interpretability
   grounds — Berman et al. (2019) and Mahdavifar & Ghorbani (2019) report high
   accuracy but heavy cost, and Gao et al. (2019) show ensembles are competitive
   far more cheaply. SVM is excluded on scalability: kernel training is roughly
   quadratic in the number of rows, which is untenable at CICIDS2017's scale for
   the tuning and latency budget I wanted. k-NN is excluded because it stores
   every training row and pays that cost on every prediction; Naive Bayes
   because it assumes independent features, which network flow data violates.
   The full comparison table is in
   `reports/algorithm_selection_justification.md`."

4. **Why these datasets and not others?**
   "They're complementary by design: NSL-KDD is the classic, most-cited academic
   benchmark (Tavallaee et al., 2009), CICIDS2017 is modern, realistic captured
   traffic (Sharafaldin et al., 2018). Together they span ~two decades of
   traffic and let me test cross-dataset robustness — one of my named research
   gaps. Alternatives were rejected for concrete reasons: KDD Cup '99 is
   redundant, UNSW-NB15 partly synthetic, CSE-CIC-IDS2018 too large (100GB+)
   for this timeframe. Both are public and anonymised."

5. **How did you handle class imbalance?**
   "Three layers. At loading, I capped the huge CICIDS classes at 15,000 rows
   while keeping every rare-class row — Heartbleed has 11 rows in the whole
   dataset. During training, SMOTE synthesises extra rare-class examples, but
   strictly inside the cross-validation folds, fitted only on each fold's
   training portion. And I scored tuning with F1-macro so rare classes weigh
   the same as Normal."

6. **What is data leakage and how did you prevent it?**
   "Leakage is test-set or future information reaching the model during
   training, inflating results. Three defences: preprocessors fitted on
   training data only and saved for reuse; SMOTE applied inside CV folds, never
   before the split; and for NSL-KDD I dropped the 'difficulty' column at load
   because it's metadata, not traffic — otherwise the model would memorise
   'hard rows are attacks'."

7. **Why is NSL-KDD test score lower than training?**
   "It's by design. The official test set contains attack variants the training
   set never showed, to measure generalisation to unseen attacks. XGBoost drops
   from 0.9565 CV to 0.6086 test; R2L recall is 0.15. That gap is the honest
   measurement of robustness to novelty — and reporting it, rather than hiding
   it, is deliberate."

8. **Which model is best?**
   "For deployment, XGBoost: best test F1 on CICIDS2017 (0.9897), best AUC on
   both datasets, and microsecond latency. I'd keep a Decision Tree running
   alongside purely for explainability. On the adversarial NSL-KDD test, the
   Decision Tree had the best F1 (0.6170), which is itself a finding about
   simple models surviving novelty."

9. **Why f1-macro and not accuracy?**
   "Accuracy is meaningless on imbalanced data — CICIDS2017 is 80% Normal, so
   'always say Normal' scores 80% while detecting nothing. F1-macro averages
   over classes equally, so detecting 11 Heartbleed rows counts the same as a
   million Normal rows."

10. **How did you choose features?**
   "I compared three independent methods — Pearson correlation, mutual
   information, and recursive feature elimination — on the pre-SMOTE training
   data. Mutual information matters because it catches non-linear relationships.
   The winners made domain sense: src_bytes for NSL-KDD, packet/flow-size
   features for CICIDS2017."

11. **Explain SMOTE in one sentence.**
    "It creates slightly-varied synthetic copies of rare attack examples so the
    model sees enough of them to learn the pattern instead of being drowned out
    by normal rows — and I used k_neighbors=3 so it still works when a class is
    tiny inside a CV fold."

12. **How do I know your results are reproducible?**
    "Fixed random seed 42 for every split, SMOTE and model initialisation;
    pinned package versions in requirements.txt; and the whole pipeline is
    notebooks 01–04 or the one command `python -m src.models.train`, which
    reloads raw data, rebuilds the splits, re-tunes every model and refreshes
    the registry. Preprocessors and label encoders are saved, forcing inference
    to match training."

13. **Why report AUC when F1 is your headline?**
    "F1 answers 'how often is the decision right?'; AUC answers 'how well does
    the model rank attacks above normal?' They disagree on trees — the Decision
    Tree has the best NSL-KDD F1 but the lowest AUC (0.7672) because it doesn't
    produce well-calibrated probabilities. Reporting both is honest and it
    changes the practical recommendation."

14. **What about ethics?**
    "Only public, anonymised, labelled datasets — no human participants, no
    personal data, no offensive capability. The UREC1-style form (in Finalds.md)
    documents this, and the deployment guidelines repeat the same boundary:
    a passive detector with human SOC review, never an inline blocker as a
    first step. Dual-use risk is mitigated by focusing purely on detection with
    defensive framing."

15. **How would this actually deploy in a real network?**
    "Passively, on a SPAN/mirror port — the switch copies traffic without
    touching it. A feature extractor turns packets into the same 78 features
    the model was trained on; the saved preprocessor transforms them
    identically; the model returns probabilities; a threshold decides whether
    an alert reaches the SOC queue. Passive-first means a model mistake can't
    take the network down. The real bottleneck isn't the model — it's feature
    extraction, and my latency numbers show the model is not the constraint."

16. **How would you handle concept drift in production?**
    "Monitor the model's probability outputs: PSI compares the current
    probability distribution against a baseline and triggers at ~0.25. Also
    watch the alert rate against a 30-day rolling baseline, and watch for new
    attack families in the SOC queue. Response: retrain quarterly at minimum,
    and trigger early when drift is detected — retraining here is one command."

17. **What are the genuine limitations of your work?**
    "Four. Both datasets are old (2009 and 2017) — modern traffic looks
    different. Cross-dataset robustness is only partially addressed: each model
    is trained and tested within its own dataset; mapping the two feature
    spaces so one model works on both is future work. There are no encrypted /
    TLS-traffic features, where many attacks now hide. And I measured per-row
    inference latency, not the full feature-extraction-to-alert pipeline."

18. **Why is CICIDS2017 so much 'easier'?**
    "Its test distribution closely matches its training distribution, so a
    well-fitted model reaches ~0.99 F1. NSL-KDD's test set is adversarial.
    The datasets measure two different things — fit and survival — and the gap
    between them is itself a finding about benchmark design."

19. **What would you do with more time?**
    "Retrain on a newer benchmark (NF-UNSW or CICIDS2019), build the
    cross-dataset transfer test, add a deep-learning comparison (the natural
    extension), build feature extraction so the pipeline ingests raw packets
    end-to-end, and automate the analyst-feedback → retraining loop."

20. **Walk me through the architecture.**
    "Notebooks 01–04 are the research pipeline; artifacts live in
    data/processed and src/models/registry. A FastAPI backend loads them and
    exposes /models, /compare, /attack-info, /predict, /simulate, plus the
    analysis endpoints /tuning-impact and /progression. A React+Vite
    dashboard polls /simulate for the live feed and draws comparison charts.
    The backend serves the built frontend from /, so one process runs the whole
    demo, and 19 API tests cover every endpoint."

21. **What was the compute situation?**
    "Google Colab for training; the longest fits were under 4 minutes
    (NSL-KDD Random Forest ~205 s, CICIDS2017 XGBoost ~195 s) with grid search
    over 4–9 hyperparameter combinations and 5-fold CV, so the whole experiment
    is repeatable on modest hardware. The exact table of grid sizes, fit times,
    CV scores and per-row latencies is in
    `reports/model_dataset_usage_statistics.md`."

---

## 9. Glossary (quick reference)

- **Accuracy:** share of all answers that were correct.
- **Precision:** of the alarms raised, the share that were real attacks.
- **Recall:** of the real attacks, the share that were caught.
- **F1 / F1-macro:** harmonic mean of precision and recall; F1-macro averages it
  equally over all classes.
- **AUC-ROC:** how well the model ranks attacks above normal — 0.5 = coin flip,
  1.0 = perfect ranking.
- **Latency:** time to classify one row (here: milliseconds per row).
- **Feature:** one measurable column describing a connection.
- **Label:** the true category of a connection.
- **Class:** one possible label value (NSL-KDD: 5; CICIDS2017: 9).
- **Training set / test set:** the pile a model learns from / the locked-away
  exam pile it's scored on.
- **Overfitting:** memorising training quirks; great train scores, poor test.
- **Underfitting:** too simple to capture the pattern at all.
- **Generalisation:** performing well on data never seen before.
- **Hyperparameter:** a dial set before training (depth, tree count,
  regularisation); tuned by grid search.
- **Grid search:** try every combination of hyperparameter values, keep the best
  by cross-validation score.
- **k-fold cross-validation:** split training data into k folds; train on k−1,
  score on the remaining one, repeat so every fold gets its turn.
- **Stratified:** folds keep the same class proportions as the full data.
- **Class imbalance:** one class vastly outnumbers others, tempting models to
  "always say Normal".
- **SMOTE:** creates synthetic rare-class examples by interpolating between real
  neighbours; training-only.
- **Data leakage:** test/future information reaching the model during training,
  inflating results.
- **Imputation:** filling missing values (here: median).
- **Min-max scaling:** rescaling numeric features into [0,1].
- **One-hot encoding:** turning text categories into 0/1 columns.
- **Zero-variance feature:** a constant column carrying no information.
- **Pearson correlation / mutual information / RFE:** three feature-selection
  methods (linear / non-linear / iterative elimination).
- **Logistic Regression:** linear classifier; the fast, explainable baseline.
- **Decision Tree:** a flowchart of yes/no questions; explainable, can overfit.
- **Random Forest:** many independent trees that vote (bagging).
- **XGBoost:** sequential trees, each correcting the last (boosting).
- **Bagging vs boosting:** independent averaging vs sequential error-correction.
- **Confusion matrix:** predictions vs reality table (TP/FP/TN/FN).
- **DoS / DDoS:** flooding a target until it can't serve real users.
- **Probe:** port scanning / reconnaissance.
- **R2L:** remote-to-local — attacker gains local access remotely.
- **U2R:** user-to-root — local privilege escalation (52 training rows in
  NSL-KDD).
- **Brute Force:** guessing credentials until one works.
- **Web Attack:** exploiting a web app (SQL injection, XSS, login brute force).
- **Botnet:** a fleet of compromised machines remotely controlled.
- **Heartbleed:** a 2014 OpenSSL memory-read bug; 11 rows in CICIDS2017.
- **Signature-based detection:** matching known attack fingerprints; blind to
  new attacks.
- **Anomaly detection:** flagging statistically unusual traffic; where ML shines.
- **Zero-day:** an attack on a not-yet-known vulnerability (no signature).
- **SPAN/mirror port:** a switch setting copying traffic for passive monitoring.
- **SOC:** Security Operations Center — the people who act on alerts.
- **Concept drift:** the data's pattern shifts over time; models silently decay.
- **PSI (Population Stability Index):** measures distribution shift; >0.25
  triggers retraining.
- **Threshold:** the probability cutoff for declaring an attack; tunes the
  recall/precision trade-off.
- **FastAPI / Uvicorn:** the Python web framework and server behind the API.
- **React / Vite / Recharts:** the JS UI library, build tool, and charting.
- **Joblib:** saves/loads trained models (.joblib).
- **scikit-learn / xgboost / imbalanced-learn:** the ML libraries (models,
  boosting, SMOTE).
- **EDA:** exploratory data analysis — first look at the data before modelling.
- **Pipeline:** the ordered chain of steps applied together (SMOTE →
  classifier); prevents leakage, keeps train/serve identical.
- **Registry:** the folder of saved models + metadata the API loads.
- **Inference:** running a trained model on new data to get an answer.
- **Reproducibility:** same steps → same numbers; ensured by seed 42, pinned
  versions, one-command retraining.

---

*Source files behind this guide: `data/processed/evaluation_results.json`,
`src/models/registry/models_metadata.json`, `reports/model_comparison_report.md`,
`reports/algorithm_selection_justification.md`,
`reports/tuning_impact_report.md`,
`reports/development_progression_report.md`,
`reports/model_dataset_usage_statistics.md`,
`data/processed/{tuning_impact,development_progression}.json`,
`reports/dataset_selection_justification.md`, `reports/deployment_guidelines.md`,
`reports/eda_report.md`, `reports/examiner_qa.md`, `docs/PROJECT_WALKTHROUGH.md`,
`docs/PHASE_EXPLANATIONS.md`, `GLOSSARY.md`, `P2633978.md`.*
