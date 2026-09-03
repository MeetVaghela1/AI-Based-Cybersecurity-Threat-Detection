"""preprocess.py — cleaning, imputation, scaling, one-hot encoding, SMOTE.

Everything in here exists because raw network data is messy:
  * some cells are missing or infinite (CICIDS2017 divides by zero),
  * some features are text ("tcp", "http", "SF") and models can't read text,
  * features have wildly different scales (a duration of 0 vs 12,000,000
    microseconds),
  * attacks are extremely rare, so classes are unbalanced.

THE MOST IMPORTANT RULE IN THIS FILE — "fit on train, transform on test":
  Every step below is *fitted* on the TRAINING set only, then *applied* to the
  test set with the same fitted values.

  Why?  Imagine we fill missing values using the *whole* dataset's median, or
  scale using the *whole* dataset's min/max.  Then the test set has already
  "leaked" its information into the model — the model has effectively seen the
  answers before the exam, so its score looks better than it ever would on
  brand-new traffic.  That is called **data leakage**, and it makes results
  dishonest.  A real intrusion-detection system meets new traffic it has never
  seen, so our evaluation must simulate that by never touching the test set
  until the model is finished.

  (SMOTE is the extreme case: it invents synthetic attack rows.  If we ran
   SMOTE on train+test together, test rows would literally be copies/mixtures
   of training rows — guaranteed cheating.  So SMOTE is applied to the training
   split only, and even then ideally *inside* each cross-validation fold.)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder
from imblearn.over_sampling import SMOTE

from src.utils import config as C


# ---------------------------------------------------------------------------
# 0. Cleaning helper
# ---------------------------------------------------------------------------

def replace_inf_with_nan(df: pd.DataFrame) -> pd.DataFrame:
    """Turn infinity into "missing".

    CICIDS2017 computes rates like "bytes per second" = bytes / duration.
    When duration is 0 that is division by zero, so the file contains
    infinity (Inf) instead of a number.  An Inf is not a missing value to
    pandas (isna() returns False), but a model can't use it either, so we
    convert Inf -> NaN so the imputer (step 2) will fill it in.
    """
    return df.replace([np.inf, -np.inf], np.nan)


# ---------------------------------------------------------------------------
# 1. The Preprocessor — imputation + scaling + one-hot encoding in one object
# ---------------------------------------------------------------------------

class Preprocessor:
    """Turns messy raw features into clean numeric features a model can use.

    It is a small wrapper around three scikit-learn steps chained together:
      1. Median imputation  (fill missing numeric cells)
      2. Min-max scaling    (squash numbers into the [0, 1] range)
      3. One-hot encoding   (turn text features into 0/1 columns)

    Usage (notice fit on train / transform on test):
        pp = Preprocessor(categorical_features=["protocol_type", "service", "flag"])
        X_train = pp.fit_transform(X_train_raw)   # learns medians, mins, cats
        X_test  = pp.transform(X_test_raw)        # reuses what train learned

    A fitted Preprocessor can also be saved with joblib and reloaded at
    prediction time (Phase 5) so the web API transforms a single incoming row
    in exactly the same way the model was trained on.
    """

    def __init__(self, categorical_features: list[str], random_state: int | None = None):
        # ---------------------------------------------------------------
        # Numeric features: impute with the MEDIAN, then min-max scale.
        # ---------------------------------------------------------------
        # Why median and not mean?  Network data has extreme outliers (a few
        # connections transfer gigabytes).  The mean gets dragged by those
        # few giants, the median ("the middle value when sorted") does not,
        # so it is a more honest value to fill gaps with.
        self.numeric_pipeline = Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", MinMaxScaler()),
        ])

        # ---------------------------------------------------------------
        # Categorical features: fill any blank with the word "missing",
        # then one-hot encode them.
        # ---------------------------------------------------------------
        # One-hot encoding: "protocol" can be tcp / udp / icmp.  Models only
        # understand numbers, so we turn it into three yes/no columns:
        #     protocol_tcp  protocol_udp  protocol_icmp
        #        1              0              0          <- this row was tcp
        # handle_unknown="ignore" is crucial: if the test set (or a future
        # live packet) contains a service never seen in training, it becomes
        # all-zero instead of crashing.
        self.categorical_pipeline = Pipeline([
            ("impute", SimpleImputer(strategy="constant", fill_value="missing")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ])

        self.categorical_features = list(categorical_features)
        self.random_state = random_state
        self._column_transformer = None      # built during fit()
        self.feature_names_out_ = None       # final column names

    # -- fit ----------------------------------------------------------------
    def fit(self, X_raw: pd.DataFrame) -> "Preprocessor":
        """Learn everything needed from the TRAINING data only."""
        # which columns are numeric vs categorical
        numeric = [c for c in X_raw.columns if c not in self.categorical_features]
        self.numeric_features_ = numeric

        # Inf -> NaN so the median imputer can see them as "missing"
        X_clean = replace_inf_with_nan(X_raw)

        self._column_transformer = ColumnTransformer([
            ("num", self.numeric_pipeline, numeric),
            ("cat", self.categorical_pipeline, self.categorical_features),
        ], verbose_feature_names_out=True)
        self._column_transformer.fit(X_clean)

        # sklearn names columns "num__duration", "cat__service_http";
        # strip the "num__"/"cat__" prefixes for clean feature names.
        raw_names = self._column_transformer.get_feature_names_out()
        self.feature_names_out_ = [n.split("__", 1)[1] if "__" in n else n
                                   for n in raw_names]
        return self

    # -- transform ----------------------------------------------------------
    def transform(self, X_raw: pd.DataFrame) -> pd.DataFrame:
        """Apply the already-fitted pipeline to new data (train OR test)."""
        X_clean = replace_inf_with_nan(X_raw)
        arr = self._column_transformer.transform(X_clean)
        return pd.DataFrame(arr, columns=self.feature_names_out_)

    # -- fit_transform ------------------------------------------------------
    def fit_transform(self, X_raw: pd.DataFrame) -> pd.DataFrame:
        """Fit on this data AND return its transformed version."""
        return self.fit(X_raw).transform(X_raw)


# ---------------------------------------------------------------------------
# 2. SMOTE — oversampling the rare attack classes
# ---------------------------------------------------------------------------

def apply_smote(
    X: pd.DataFrame,
    y: pd.Series,
    sampling_strategy: str | dict | None = "auto",
    random_state: int | None = C.RANDOM_STATE,
):
    """Balance the training classes by inventing synthetic minority samples.

    What SMOTE does (Synthetic Minority Oversampling TEchnique):
      For a rare class, pick a real row, find its 5 nearest neighbours in
      feature-space, then create a NEW fake-but-plausible row somewhere along
      the line between them.  Repeating this grows a tiny class (e.g. U2R's 52
      rows) into thousands of rows, so the model actually has enough examples
      to learn what that attack looks like.

    WHY TRAIN ONLY:
      * Test data must stay exactly as collected — the "exam".  We never
        invent rows for it.
      * If we SMOTE'd test+train together, test rows could be synthetic
        mixtures of training rows, which would guarantee unrealistically high
        scores (data leakage).

    Returns:
        (X_balanced, y_balanced) — X unchanged, y re-sampled to match.
    """
    smote = SMOTE(
        sampling_strategy=sampling_strategy,
        random_state=random_state,
        k_neighbors=5,          # nearest-neighbour count used to invent rows
    )
    Xb, yb = smote.fit_resample(X, y)
    return Xb, yb
