"""feature_selection.py — the three feature-selection methods from the proposal.

WHY DO FEATURE SELECTION AT ALL?
  NSL-KDD has 41 features, CICIDS2017 has 78 (and one-hot encoding turns the
  text features into ~120).  Many of those features carry the *same* information
  (the EDA showed dozens of pairs with correlation > 0.9).  Feeding a model a
  pile of redundant features:
    * slows it down (more math per prediction — the latency we care about),
    * can make it overfit noise instead of learning the real signal,
    * makes the model harder to explain.
  Thakkar & Lohiya (2021) report that a good feature subset can cut
  computational cost by ~40% without losing accuracy.

  This module implements the three methods the project proposal promises:
    1. Pearson correlation filtering — rank features by how correlated they
       are with the attack class; keep the strongest, drop the weakest.
    2. Mutual information ranking — a non-linear "how much does this feature
       tell us about the class?" score from information theory.
    3. Recursive Feature Elimination (RFE) — let a model repeatedly train on
       all features, then chop away the least important ones.

  Every method is run on the PREPROCESSED (imputed + scaled + encoded) numeric
  matrix, BEFORE SMOTE — we do not want synthetic rows influencing which
  features we choose.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.feature_selection import (
    mutual_info_classif,
    RFE,
)
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder

from src.utils import config as C


# ---------------------------------------------------------------------------
# Shared target encoding (classes are text like "DoS", "Normal", ...)
# ---------------------------------------------------------------------------

def _encode_target(y: pd.Series) -> tuple[pd.Series, LabelEncoder]:
    """Turn text labels into 0,1,2,... so numeric methods can use them."""
    le = LabelEncoder()
    return pd.Series(le.fit_transform(y), index=y.index), le


# ---------------------------------------------------------------------------
# Method 1 — Pearson correlation filtering
# ---------------------------------------------------------------------------

def pearson_ranking(X: pd.DataFrame, y: pd.Series, top_k: int = 30) -> pd.DataFrame:
    """Rank features by absolute Pearson correlation with the class label.

    Pearson correlation measures *linear* association between two numbers on
    a -1..+1 scale.  We compare each feature against the (numerically encoded)
    class label.  Features whose value changes consistently as the class
    changes get a high score and are kept.

    Caveat: this only finds *linear* relationships.  A feature can be vital
    yet score ~0 if its link to the class is non-linear — which is exactly why
    we also run mutual information (method 2).
    """
    y_enc, _ = _encode_target(y)

    def corr_with_target(col: pd.Series) -> float:
        # constant columns give NaN correlation -> treat as 0 importance
        if col.nunique() <= 1:
            return 0.0
        return abs(col.corr(y_enc))

    scores = X.apply(corr_with_target)
    table = pd.DataFrame({
        "feature": X.columns,
        "pearson_score": scores.values,
    })
    table = table.sort_values("pearson_score", ascending=False).reset_index(drop=True)
    table["pearson_rank"] = np.arange(1, len(table) + 1)
    table["pearson_kept"] = table["pearson_rank"] <= top_k
    return table


# ---------------------------------------------------------------------------
# Method 2 — Mutual information ranking
# ---------------------------------------------------------------------------

def mutual_info_ranking(X: pd.DataFrame, y: pd.Series, top_k: int = 30) -> pd.DataFrame:
    """Rank features by mutual information with the class label.

    Mutual information (MI) answers: "if I learn this feature's value, how many
    bits of information do I gain about which class it is?"  Unlike Pearson it
    catches ANY kind of relationship, linear or not, so it is the more powerful
    ranker.  It is computed from a count of how often feature/class combinations
    occur, so no distributional assumptions are needed.
    """
    y_enc, _ = _encode_target(y)
    mi = mutual_info_classif(
        X.astype(float),
        y_enc,
        discrete_features="auto",   # one-hot columns are 0/1 -> "discrete"
        random_state=C.RANDOM_STATE,
    )
    table = pd.DataFrame({
        "feature": X.columns,
        "mi_score": mi,
    })
    table = table.sort_values("mi_score", ascending=False).reset_index(drop=True)
    table["mi_rank"] = np.arange(1, len(table) + 1)
    table["mi_kept"] = table["mi_rank"] <= top_k
    return table


# ---------------------------------------------------------------------------
# Method 3 — Recursive Feature Elimination (RFE)
# ---------------------------------------------------------------------------

def rfe_selection(
    X: pd.DataFrame,
    y: pd.Series,
    base_estimator=None,
    n_features_to_select: int = 30,
    step: int = 5,
) -> pd.DataFrame:
    """Select features by recursively removing the least important ones.

    How RFE works:
      1. train the base model on ALL features,
      2. ask the model which features mattered least (coefficients /
         importance scores),
      3. delete the least important `step` features,
      4. repeat with the smaller set until `n_features_to_select` remain.

    The surviving set is the model's own opinion of what matters, so RFE is
    usually the most task-specific of the three methods.  The cost is that it
    trains the base model many times (slower than the other two methods).

    Default base model: Logistic Regression — fast, and its coefficients give
    a clean importance ranking.  You may pass any estimator that has either
    `.coef_` or `.feature_importances_`.
    """
    y_enc, _ = _encode_target(y)
    if base_estimator is None:
        base_estimator = LogisticRegression(max_iter=1000, random_state=C.RANDOM_STATE)

    rfe = RFE(
        estimator=base_estimator,
        n_features_to_select=n_features_to_select,
        step=step,
    )
    rfe.fit(X, y_enc)

    table = pd.DataFrame({
        "feature": X.columns,
        "rfe_kept": rfe.support_,
    })
    # rank the kept features by their model-importance (coef magnitude)
    if hasattr(rfe.estimator_, "coef_"):
        importances = np.abs(rfe.estimator_.coef_).sum(axis=0)
    else:
        importances = rfe.estimator_.feature_importances_
    imp_map = {name: imp for name, imp in zip(X.columns, importances)}
    table["rfe_importance"] = table["feature"].map(imp_map)
    kept = table[table["rfe_kept"]].sort_values("rfe_importance", ascending=False)
    rank_map = {name: i for i, name in enumerate(kept["feature"], start=1)}
    table["rfe_rank"] = table["feature"].map(rank_map).fillna(0).astype(int)
    return table.sort_values("rfe_rank").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Comparison — run all three methods and write one table
# ---------------------------------------------------------------------------

def compare_methods(
    X: pd.DataFrame,
    y: pd.Series,
    dataset_name: str,
    top_k: int = 30,
    out_path=None,
) -> pd.DataFrame:
    """Run all three methods and merge the results into one comparison table.

    Returns a DataFrame with, per feature:
        pearson_score / pearson_rank / pearson_kept
        mi_score      / mi_rank      / mi_kept
        rfe_kept      / rfe_rank     / rfe_importance

    The "kept" columns mark the top-`top_k` features of each method, making
    it easy to see where the methods agree and disagree.
    """
    print(f"Running all three feature-selection methods on {dataset_name} ...")
    pearson = pearson_ranking(X, y, top_k=top_k)
    mi = mutual_info_ranking(X, y, top_k=top_k)
    rfe = rfe_selection(X, y, n_features_to_select=top_k)

    table = pearson[["feature", "pearson_score", "pearson_rank", "pearson_kept"]]
    table = table.merge(
        mi[["feature", "mi_score", "mi_rank", "mi_kept"]], on="feature"
    )
    table = table.merge(
        rfe[["feature", "rfe_kept", "rfe_rank", "rfe_importance"]], on="feature"
    )
    table = table.sort_values(
        ["pearson_rank", "mi_rank", "rfe_rank"]
    ).reset_index(drop=True)

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(out_path, index=False)
        print(f"Saved comparison table -> {out_path}")

    # quick summary printed to screen
    for method, col in [("Pearson", "pearson_kept"),
                        ("Mutual info", "mi_kept"),
                        ("RFE", "rfe_kept")]:
        print(f"  {method:11s} kept {int(table[col].sum())} features")
    agree = table[(table["pearson_kept"]) & (table["mi_kept"]) & (table["rfe_kept"])]
    print(f"  Features all three methods agree on: {len(agree)}")
    return table
