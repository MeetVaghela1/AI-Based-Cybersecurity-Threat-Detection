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
