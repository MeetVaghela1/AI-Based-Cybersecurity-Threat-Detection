# Algorithm Selection Justification

This project compares **Logistic Regression, Decision Tree, Random Forest, and
XGBoost** for intrusion detection. The selection is deliberate rather than a
default pick: the four algorithms form a controlled ladder of model families —
linear, single tree, bagging, boosting — which is exactly what is needed to
answer the project's research question about the *accuracy vs interpretability
vs speed* trade-off. Candidate algorithms that are popular in the literature
(SVM, k-NN, Naive Bayes, deep learning) were explicitly considered and excluded
for concrete reasons, so the study deliberately stays within the *classical*
machine-learning family (Berman et al., 2019; Mahdavifar & Ghorbani, 2019).

## Comparison of Candidate Algorithms

| Algorithm | Family | Why included / excluded |
|---|---|---|
| Logistic Regression (included) | Linear | Fast, cheap, fully explainable (read the weights); the honest baseline every stronger model must beat. |
| Decision Tree (included) | Tree (white-box) | Readable "if/then" rules — the explainability companion for deployment; measures how far a *single* interpretable model can go. |
| Random Forest (included) | Bagging ensemble | Many independent trees that vote; the bagging family, robust to overfitting when the world doesn't change. |
| XGBoost (included) | Boosting ensemble | Sequential trees that fix each other's mistakes; consistently among the strongest classical classifiers in the IDS literature (Ramu, 2025). |
| SVM | Kernel | **Excluded** — kernel methods scale poorly on data of this size (roughly quadratic cost in the number of rows) and are memory-hungry and slow to tune; on CICIDS2017 (tens of thousands of rows) the compute and latency cost could not be justified against the ensemble models' results. |
| k-Nearest Neighbours | Instance-based | **Excluded** — keeps every training row in memory and pays that cost per prediction, making live inference slow and storage-heavy at this scale. |
| Naive Bayes | Probabilistic | **Excluded** — assumes features are independent; network flow features (byte counts, rates, packet sizes) are strongly correlated, so the assumption is violated. |
| Deep learning (DNN/CNN/LSTM) | Neural | **Excluded for this study** — the literature (Berman et al., 2019; Mahdavifar & Ghorbani, 2019) reports high benchmark accuracy but at substantial computational, tuning and interpretability cost, and ensembles reach competitive accuracy much more cheaply (Gao et al., 2019). A deep-learning comparison is listed as explicit future work. |

## Rationale for the Selected Four

- **A controlled methodological spread, not a grab-bag.** The four models span
  the classical-ML design space in one dimension at a time: linear (Logistic
  Regression) → non-linear single model (Decision Tree) → bagging ensemble
  (Random Forest) → boosting ensemble (XGBoost). Each step up adds capacity and
  complexity, which lets the project measure *where* accuracy is gained and
  what interpretability/speed is given up — the core of the research gap.
- **Explainability is a first-class requirement.** Logistic weights and the
  Decision Tree's rules can be read by a human SOC analyst; the ensembles cannot.
  Keeping both the readable and the black-box families means the project can
  recommend a *deployment pairing* (XGBoost to detect, Decision Tree to
  explain) rather than a single number.
- **Ensemble literature supports the top of the ladder.** Gao et al. (2019)
  showed adaptive ensembles are competitive with deep models at far lower cost,
  and Ramu (2025) found XGBoost outperforming other classical classifiers on
  threat detection. The four chosen algorithms include both ensemble families
  (bagging and boosting) so those claims can be tested on this project's own
  data.
- **Exclusions are reasons, not tastes.** SVM and k-NN fail the scalability
  test for live deployment at this dataset size; Naive Bayes fails on the
  correlated-feature reality of network flows; deep learning fails the
  interpretability-and-compute budget of a 16-week, Google Colab-based project
  (Berman et al., 2019; Mahdavifar & Ghorbani, 2019).
- **Practical feasibility within the project's constraints.** All eight models
  (4 algorithms × 2 datasets) are tuned with grid search over 4–9
  hyperparameter combinations and stratified 5-fold cross-validation, with
  SMOTE kept inside the folds. The longest single fit is under ~4 minutes
  (NSL-KDD Random Forest ≈ 205 s, CICIDS2017 XGBoost ≈ 195 s), so the entire
  experiment is reproducible on modest hardware — which is also what makes the
  `python -m src.models.train` one-command reproducibility path credible.

## How the choice plays out in the results

| Dataset | Logistic | Decision Tree | Random Forest | XGBoost |
|---|---:|---:|---:|---:|
| NSL-KDD (test F1, macro) | 0.5572 | **0.6170** | 0.5384 | 0.6086 |
| CICIDS2017 (test F1, macro) | 0.8267 | 0.9505 | 0.9276 | **0.9897** |

The ladder behaves as intended. On the realistic dataset (CICIDS2017) the
ensembles clearly win, with XGBoost best; on the adversarial benchmark
(NSL-KDD) the simple Decision Tree generalises best to unseen attack variants.
That *difference is the finding* — and it only exists because the four families
were chosen to be comparable in every other respect.

## References

- Berman, D. S., Buczak, A. L., Chavis, J. S., & Corbett, C. L. (2019). A
  survey of deep learning methods for cyber security. *Information, 10*(4),
  122. https://doi.org/10.3390/info10040122
- Gao, X., Shan, C., Hu, C., Niu, Z., & Liu, Z. (2019). An adaptive ensemble
  machine learning model for intrusion detection. *IEEE Access, 7*,
  82512–82521.
- Mahdavifar, S., & Ghorbani, A. A. (2019). Application of deep learning to
  cybersecurity: A survey. *Neurocomputing, 347*, 149–176.
- Ramu, A. (2025). Machine learning for cyber threat detection using historical
  vulnerabilities and security standards. *Journal of Computer and
  Communication Networks, 4*(1), 1–15.
