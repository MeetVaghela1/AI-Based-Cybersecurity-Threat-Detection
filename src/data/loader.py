"""loader.py — reads the raw datasets and standardises them into one schema.

Why this module exists:
  The project uses two datasets that look completely different on disk:
    * NSL-KDD    — 41 features (3 of them text), one .txt file per split.
    * CICIDS2017 — 78 numeric features, eight CSV files (~2.8 million rows
                   in total, so it is read in CHUNKS to avoid blowing up RAM).
  Every later stage (EDA, preprocessing, training, the web API) should be
  able to pretend the two datasets are one.  This module is the only place
  that knows the raw file formats: it converts everything into the common
  columns defined in config.py:
      source, is_attack, attack_category, attack_type  + the original features

  What "is_attack / attack_category / attack_type" mean:
    * attack_type      — the fine-grained name from the dataset
                         (NSL-KDD: neptune, satan, ...  CICIDS2017: DDoS, Bot...)
    * attack_category  — the coarse class we actually predict
                         (NSL-KDD: Normal/DoS/Probe/R2L/U2R,
                          CICIDS2017: Normal/DDoS/PortScan/Brute Force/...)
    * is_attack        — 1 if the row is any kind of attack, 0 if normal.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.utils import config as C

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _snake_case(name: str) -> str:
    """Turn a messy CICIDS column header into a clean snake_case name.

    Examples:
        " Total Fwd Packets"      -> "total_fwd_packets"
        "Flow Bytes/s"            -> "flow_bytes_s"
        "Fwd Header Length.1"     -> "fwd_header_length_1"
        "Init_Win_bytes_forward"  -> "init_win_bytes_forward"

    Why do this?  The rest of the code refers to features by name.  If every
    header keeps its own weird spacing/case, we can never share feature lists
    between scripts — one typo and the model silently gets different columns.
    Normalising once, here, removes that whole class of bugs.
    """
    s = name.strip().replace("/", "_").replace("-", "_")
    s = s.replace(".", "_").replace("(", "").replace(")", "")
    s = re.sub(r"\s+", "_", s)      # collapse runs of spaces to one "_"
    s = re.sub(r"_+", "_", s)       # "A__B" -> "A_B"
    return s.strip("_").lower()


def _nsl_kdd_category(attack_type: str) -> str:
    """Coarse category for an NSL-KDD attack name; 'Normal' if it is normal."""
    return C.NSL_KDD_ATTACK_CATEGORY.get(attack_type, C.NORMAL_CATEGORY)


def _cicids_category(label: str) -> str:
    """Coarse category for a CICIDS2017 label, handling known data quirks."""
    if label == "BENIGN":
        return C.NORMAL_CATEGORY
    if label.startswith("Web Attack"):     # Web Attack - X, XSS, Sql Injection
        return "Web Attack"
    return C.CICIDS_ATTACK_CATEGORY.get(label, "Unknown")


# ---------------------------------------------------------------------------
# NSL-KDD
# ---------------------------------------------------------------------------

def load_nsl_kdd(split: str = "train") -> pd.DataFrame:
    """Load the NSL-KDD train or test set into the common schema.

    Args:
        split: "train" (KDDTrain+.txt) or "test" (KDDTest+.txt).

    Returns a DataFrame with the 41 NSL-KDD features PLUS the common
    label columns (source, is_attack, attack_category, attack_type).

    What we do here step by step:
      1. read the file with NO header and give the columns our own names;
      2. drop the "difficulty" column (a 0-21 score researchers attached to
         each row).  It is metadata, not traffic, so a model must never see
         it — otherwise the model would learn "hard rows are attacks".
      3. turn every non-categorical feature into numbers (they arrive as text);
      4. build the three label columns from the attack type.
    """
    if split == "train":
        path = C.NSL_KDD_TRAIN_FILE
    elif split == "test":
        path = C.NSL_KDD_TEST_FILE
    else:
        raise ValueError(f"split must be 'train' or 'test', got {split!r}")

    if not Path(path).exists():
        raise FileNotFoundError(
            f"NSL-KDD file not found: {path}\n"
            "Check data/raw/DATASET_MANIFEST.md — the .txt files are required."
        )

    # 43 columns in the file: 41 features + attack type + difficulty score
    file_columns = C.NSL_KDD_FEATURES + [C.TYPE_COL, "difficulty"]
    df = pd.read_csv(path, header=None, names=file_columns, engine="c")

    # 1. drop the difficulty score (metadata, not a traffic feature)
    df = df.drop(columns=["difficulty"])

    # 2. coerce all non-categorical features to numbers
    numeric_cols = [
        c for c in C.NSL_KDD_FEATURES if c not in C.NSL_KDD_CATEGORICAL_FEATURES
    ]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    # 3. build the common label columns
    df[C.CATEGORY_COL] = df[C.TYPE_COL].map(_nsl_kdd_category)
    df[C.IS_ATTACK_COL] = (df[C.CATEGORY_COL] != C.NORMAL_CATEGORY).astype(int)
    df[C.SOURCE_COL] = "NSL-KDD"
    df[C.TYPE_COL] = df[C.TYPE_COL].str.strip()   # just in case of stray spaces

    return df


# ---------------------------------------------------------------------------
# CICIDS2017
# ---------------------------------------------------------------------------

def _standardise_cicids_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Clean one chunk of CICIDS2017 into the common schema."""
    # 1. normalise column names to snake_case
    chunk.columns = [_snake_case(c) for c in chunk.columns]

    # 2. drop any identifying metadata columns if present (raw version only)
    chunk = chunk.drop(
        columns=[c for c in chunk.columns if c in C.CICIDS_META_COLUMNS]
    )

    # 3. the label column must be "label" in snake_case
    if "label" not in chunk.columns:
        raise ValueError(f"Expected a 'Label' column, got {list(chunk.columns)}")

    # 4. clean the labels: strip spaces, fix the corrupted em-dash
    labels = chunk["label"].astype(str).str.strip()
    labels = labels.str.replace("\ufffd", "-", regex=False)
    chunk = chunk.drop(columns=["label"])

    # 5. build the common label columns
    attack_type = labels.rename(C.TYPE_COL)
    attack_category = labels.map(_cicids_category).rename(C.CATEGORY_COL)
    is_attack = (attack_category != C.NORMAL_CATEGORY).astype(int).rename(
        C.IS_ATTACK_COL
    )
    chunk = pd.concat(
        [chunk, attack_type, attack_category, is_attack], axis=1
    )
    chunk[C.SOURCE_COL] = "CICIDS2017"

    return chunk


def cicids2017_chunks(chunksize: int = 500_000):
    """Yield cleaned chunks of CICIDS2017 one at a time.

    CICIDS2017 is ~2.8 million rows / ~1 GB of CSV.  Reading it all into
    memory at once is wasteful (and can crash laptops).  This generator
    reads the eight daily files piece by piece and hands each chunk back,
    so an EDA pass can count things without ever holding the whole table.
    """
    files = sorted(C.CICIDS_RAW_DIR.glob(C.CICIDS_FILE_PATTERN))
    if not files:
        raise FileNotFoundError(
            f"No CICIDS2017 CSV files found in {C.CICIDS_RAW_DIR} matching "
            f"{C.CICIDS_FILE_PATTERN!r}. See data/raw/DATASET_MANIFEST.md."
        )
    for path in files:
        for chunk in pd.read_csv(
            path,
            chunksize=chunksize,
            low_memory=False,
            on_bad_lines="skip",      # ignore any malformed line rather than crash
        ):
            yield _standardise_cicids_chunk(chunk)


def load_cicids2017(
    sample_frac: float | None = None,
    random_state: int | None = C.RANDOM_STATE,
    max_rows: int | None = None,
) -> pd.DataFrame:
    """Load (part of) CICIDS2017 into one DataFrame in the common schema.

    Args:
        sample_frac: if set (e.g. 0.2), keep a random fraction of every chunk.
            Useful when you only need a representative sample for experiments
            or EDA and want to save memory/time.
        random_state: seed so the sampled rows are the same every run
            (reproducibility for the thesis).
        max_rows: stop once roughly this many rows have been collected.

    Returns one concatenated DataFrame with the 78 features + label columns.
    """
    frames = []
    total = 0
    for chunk in cicids2017_chunks():
        if sample_frac is not None:
            chunk = chunk.sample(frac=sample_frac, random_state=random_state)
        frames.append(chunk)
        total += len(chunk)
        if max_rows is not None and total >= max_rows:
            break
    return pd.concat(frames, ignore_index=True)


def load_cicids2017_capped(
    per_class_cap: int = 15_000,
    random_state: int | None = C.RANDOM_STATE,
) -> pd.DataFrame:
    """Load CICIDS2017 keeping EVERY rare-class row but capping common classes.

    Why not just random-sample?
      CICIDS2017 is so imbalanced that ordinary random sampling would keep
      80% normal traffic and throw away the rare attacks entirely (Heartbleed
      has only 11 rows in the whole dataset!).  A model trained without them
      could never learn to detect them.

    How this works (two passes over the data):
      Pass 1: count how many rows each attack category has.
      Pass 2: for every category, keep ALL its rows if it is rare, otherwise
              keep a random sample so that the class has at most
              `per_class_cap` rows.  Rare classes are therefore preserved
              100% while huge classes (BENIGN, DoS) are downsized.
    """
    from collections import Counter

    # Pass 1: count rows per coarse category (streaming, low memory).
    counts = Counter()
    for chunk in cicids2017_chunks():
        counts.update(chunk[C.CATEGORY_COL].value_counts().to_dict())

    # The fraction of each class we keep so no class exceeds per_class_cap.
    frac = {cat: min(1.0, per_class_cap / n) for cat, n in counts.items()}

    # Pass 2: sample per class, keeping rare classes intact.
    frames = []
    for chunk in cicids2017_chunks():
        keep = []
        for key, sub in chunk.groupby(C.CATEGORY_COL, group_keys=False):
            n_keep = max(1, int(round(len(sub) * frac[key])))
            keep.append(sub.sample(n=n_keep, random_state=random_state))
        frames.append(pd.concat(keep))
    return pd.concat(frames, ignore_index=True)
