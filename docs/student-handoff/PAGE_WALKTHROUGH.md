# Student Handoff — Page Walkthrough

This guide is for a student who has **never seen this dashboard before**. It
explains every screen, every button, and how to read the results. You do not
need to know any programming or cyber-security to follow it.

If you have not started the app yet, do `SETUP_GUIDE.md` first — then open
http://127.0.0.1:8000 in your browser.

---

## If you only remember 5 things

1. **Everything here runs on recorded traffic — it is a simulation.** The
   dashboard replays rows from the datasets the models were tested on. It is
   not connected to a live network and it is not an attack tool. The
   "SIMULATED TRAFFIC" badge is that guarantee.
2. **The Live Monitor tab is the heart of the app.** Start it, and the four
   models classify a stream of connections; you watch an intrusion-detection
   system think in real time.
3. **The Model Comparison tab is the science.** It answers: which model is
   best, and why. Green cells in the scoreboard = the best score on that
   metric. Hover any chart to see exact numbers.
4. **XGBoost wins on the modern dataset; the Decision Tree wins on the old
   one.** Neither is simply "the best" — the results are honest about that.
5. **The database tab is a record of everything the monitor has classified.**
   It fills up as the monitor runs and is stored in a small file on the
   server, so it survives restarts.

---

## The top bar (every page)

- **CyberGuard** — the name of the system (the brand).
- **SIMULATED TRAFFIC** — a badge that never goes away: everything the monitor
  shows is a replay of recorded dataset traffic, not live capture.
- **Four tabs** — Live Monitor, Model Comparison, Database, How It Works. You
  can switch anytime; the monitor keeps running in the background while you
  look at other tabs.
- **Start/Resume the tour** — on first load the app opens a short guided tour
  (about 10 steps) that points at each important control. If you closed it,
  you can reopen it from the top bar. When the tour runs, the browser scrolls
  and highlights each element in turn; press **Next** to move on.

---

## Tab 1 — Live Monitor

This is the main page and the best demo.

### What you see

- **Start Monitoring** (or **Pause**) button — starts and stops the traffic
  stream.
- **Dataset** selector — `NSL-KDD` or `CICIDS2017` (the two benchmark
  datasets; see the How-It-Works tab and the structure guide for what they
  are).
- **Model** selector — one of the four classifiers (Logistic Regression,
  Decision Tree, Random Forest, XGBoost). You watch the model you picked.
- A **live indicator** — a pulsing dot and "LIVE" label while monitoring is
  running.
- **Status pills** — small labels telling you, e.g. whether monitoring is on
  and what dataset/model are active.
- **Attack cards** — when a connection is classified, the page shows cards
  for recent connections: the verdict, how confident the model is (a
  percentage/probability), which dataset the row came from, and how long the
  model took to answer (latency in milliseconds).
- **An explanation box** (below) — when an attack is detected, the system
  explains the attack in plain English (e.g. what a DoS is, how it works,
  what it looks like, how you defend against it).

### What is happening behind the scenes

Once every ~1.6 seconds the website asks the backend to pick a random row from
the dataset's test set and classify it. Each row is one real network
connection that was recorded when the dataset was created. The dataset also
records the *true* answer for that row, so the card can say whether the model
**matched** the real answer or not.

### A way to think about it

**Security-camera replay.** Imagine a bank showing you last month's CCTV
footage with an AI flagging suspicious moments: "this person was a thief — the
video already says so, and the AI agrees / disagrees." That is exactly what
the monitor does: replaying *known* footage so you can judge how good the
detector is, without any real risk. Every verdict is for a recorded connection
whose answer is already known — that is why the dashboard can honestly show a
"matched: yes/no" check.

### How to read a card

- **Prediction** — what the model thinks the connection is (`Normal`, `DoS`,
  `Probe`, ...).
- **Confidence** — the model's own certainty as a probability from 0 to 1
  (e.g. 0.98 = 98% sure).
- **Latency (ms)** — how long the classification took. The latency values are
  live numbers measured on your machine, not marketing figures.
- **Matched** — whether the model agreed with the dataset's true label. Do not
  panic at the occasional mismatch; that is the honest reality of a detector,
  and the Model Comparison tab shows each model's overall catch-rate.

---

## Tab 2 — Model Comparison

This is where the science lives: the same four models, the same pipeline,
scored on the untouched test sets. All charts here update when you switch
dataset.

### Dataset toggle

- **NSL-KDD / CICIDS2017** buttons at the top switch everything between the
  two datasets.
- The **?** (HelpTip) icon next to them gives a one-line reminder: same
  models, two benchmarks; CICIDS2017 is the modern one.

### Headline metrics (the big bar chart)

Five metrics, four coloured bars each (one per model):

- **Accuracy** — fraction of connections classified correctly.
- **Precision** — of the alarms raised, how many were real attacks.
- **Recall** — of the real attacks, how many were caught.
- **F1** — one number balancing precision and recall (the headline metric).
- **AUC-ROC** — how well the model ranks attacks above normal traffic.

**Airport-security analogy for precision vs recall:** the scanner's *precision*
is "of the people I stop, how many are actually carrying something?"; its
*recall* is "of the people carrying something, how many did I catch?". A
scanner that waves nobody through has great precision but useless recall. A
scanner that stops everyone has perfect recall but terrible precision. F1 is
the single score that punishes both failure modes.

### Radar chart

Draws the five metrics as one shape per model. A big, round shape = strong on
every metric at once; a squashed one = weak somewhere. It is the quickest
visual "who is the best all-rounder".

### Latency & speed table

Two columns per model: **Test set (ms/row)** from the official test-set
measurement, and **Live (ms/row)** measured end-to-end while the monitor runs
on your machine (shown when a dot turns LIVE). Every model answers in well
under a millisecond per row — speed is not the deciding factor between them.

### Scoreboard

A full table of every metric per model. **Green = the best value on that
metric.** Underneath, the page states the best overall model by F1.

### "How much did tuning help" panel

Two bars per model: **Baseline F1** (default settings) vs **Tuned F1** (the
saved, grid-searched model). A **ΔF1** column shows the change (+ green, −
red). The honest caption matters: tuning helps some models (XGBoost, Logistic
Regression) and leaves others roughly unchanged (Decision Tree, Random
Forest) because their defaults were already strong.

### Training insights & development progression (bottom)

- A **NSL-KDD / CICIDS2017 / Compare both** toggle.
- **Four training charts** — the real convergence curves collected while the
  models were being trained:
  - XGBoost — training loss over 100 boosting rounds (lower = better).
  - Random Forest — out-of-bag error as trees are added (lower = better).
  - Decision Tree — training error vs tree depth.
  - Logistic Regression — how the model's score converges as training
    iterations increase.
- The **dashed vertical line** on each chart marks the setting the *saved*
  model actually uses (e.g. "rounds: 100", "trees: 200", "depth: 20"). The
  caption above the chart states it in words.
- **How to read them:** hover any line to see exact values; click a name in
  the legend to hide/show that series; the solid dots are the measured points
  and the line between them is only a guide. If the charts cannot load, the
  page says "Training curves could not be loaded" — the data file is missing,
  see the troubleshooting in the Setup Guide.
- **The progression chart** (full width) shows Logistic Regression's test
  score as the pipeline improves:
  - **A** = raw features, **B** = + cleaning/scaling/encoding,
  - **C** = + aggressive feature selection (it *hurts* — too few features),
  - **D** = + SMOTE (class balancing), **E** = + grid-search tuning.
  The takeaway printed under the chart: most of the improvement comes from
  cleaning + balancing, not from fancy hyperparameters.

---

## Tab 3 — Database

A record of every connection the monitor has classified.

### What you see

A table of stored predictions — one row per classified connection — that
refreshes every 2 seconds:

- **Time** — when it was classified (HH:MM:SS).
- **Dataset / Model** — which combination made the call.
- **Prediction** — the verdict (Normal or an attack type).
- **is_attack** — yes/no.
- **Confidence** — the model's certainty.
- **Latency (ms)** — how long it took.
- **True label / Matched** — the dataset's real answer and whether the model
  got it right.

### Controls

- **Filters** — narrow the list by dataset and/or by verdict (e.g. show only
  CICIDS2017 rows predicted as attacks).
- **Limit** — how many of the newest rows to show.
- The newest rows appear first.

### Where the data lives

The log is kept by the backend and written to `data/processed/prediction_log.json`
(capped at the most recent 200 entries), so it survives a server restart. The
page never invents data — everything here was genuinely classified by the
models on your machine.

---

## Tab 4 — How It Works

Plain-language explanations, with no setup needed.

- **Four algorithm cards** — one for each model, written for a non-expert:
  what the model is, how it learns, and its honest strengths/weaknesses
  (this is the same framing as the "four security guards" idea below).
- **The attack-category list** — every attack type the models can predict,
  from both datasets: DoS, Probe, R2L, U2R (NSL-KDD) and DDoS, PortScan,
  Brute Force, Web Attack, Botnet, Infiltration, Heartbleed (CICIDS2017),
  plus Normal.
- Clicking an attack opens its explanation (from the backend's
  `/attack-info` endpoint): what it is, how it works, what it looks like on
  the network, its impact, how to defend against it, and a concrete example.

### The four models as four security guards

- **Logistic Regression** — a guard trained on a checklist. Simple, fast, and
  you can read exactly which checklist items he uses, but he misses patterns
  the checklist does not cover.
- **Decision Tree** — a guard following a flow-chart of yes/no questions
  ("is it small? yes → is it from port 80? no → suspicious"). Fully
  transparent: anyone can read his rules. Can become brittle on data he has
  not seen.
- **Random Forest** — a committee of many decision trees, each seeing a
  random slice of the evidence; they vote. Much harder to fool than one
  tree, at the cost of being unreadable.
- **XGBoost** — a committee that learns from its own mistakes: each new tree
  focuses on the cases the previous ones got wrong. Typically the strongest
  detector here (the classic "boosting" idea).

**Doctor-confidence analogy for predictions:** when a model says "0.95", that
is a doctor saying "I'm 95% sure it's a DoS". You would not trust 0.51 the way
you trust 0.99. The dashboard shows these probabilities honestly.

---

## Reading the results honestly (the 3-minute version)

- **No model is perfect.** Mismatched verdicts in the monitor and non-1.0
  scores in the comparison are expected — the project's whole point is that
  these differences are *measurable*.
- **The single most useful number is F1 (macro).** It balances precision and
  recall and gives rare attack classes equal weight to "Normal". Higher F1 =
  better detection overall.
- **The headline result.** On CICIDS2017 (modern traffic), XGBoost is best
  (test F1 ≈ 0.99). On NSL-KDD (an older, harder benchmark), the Decision Tree
  generalises best (test F1 ≈ 0.62) — its transparency and robustness matter
  there. Those are the two numbers people will ask you about.
- **Speed is a non-issue.** Every model answers in well under a millisecond
  per row, so the choice between models is about accuracy and
  explainability — not speed.

---

## The 10 words you will see on screen

| Word | Plain meaning |
|---|---|
| **Dataset** | A big table of recorded network connections with known answers. |
| **Test set** | Connections the models never trained on — the "unseen exam". |
| **Row** | One network connection (one line in the table). |
| **Feature** | One measured property of a connection (duration, bytes sent, ...). |
| **Label / True label** | The connection's real answer (its correct class). |
| **Classification** | The model deciding which class a connection belongs to. |
| **Confidence** | How sure the model is, as a probability 0–1. |
| **Latency** | How long the model took to answer (milliseconds). |
| **SMOTE** | A technique that creates synthetic rare-attack rows so the model can learn them (training only). |
| **Hyperparameter** | A dial set *before* training (e.g. "how deep may trees grow?"); tuning = trying dial combinations. |
