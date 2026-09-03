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
