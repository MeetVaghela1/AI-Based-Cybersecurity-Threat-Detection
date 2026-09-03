# DATASET MANIFEST — data/raw/

> This file documents the dataset triage performed in **Phase 0.5**.
> It is written so the "data collection" section of the thesis can simply
> reference it. Every file placed in `data/raw/` is listed below, marked as
> **USED** (feeding the ML pipeline) or **IGNORED** (kept for record, not used),
> with the reason.

---

## 1. Inventory of every file in data/raw/

### 1.1 NSL-KDD — folder `nsl-kdd/`

| File | Size | Rows | What it is |
|------|------|------|------------|
| `KDDTrain+.txt` | 18.2 MB | 125,973 | **Core train set.** 43 comma-separated columns: 41 features + attack-type label + difficulty score |
| `KDDTrain+_20Percent.txt` | 3.6 MB | 25,192 | **Subset train set.** Random 20% of `KDDTrain+.txt` (same schema) |
| `KDDTest+.txt` | 3.3 MB | 22,544 | **Core test set.** Full NSL-KDD test set (43 columns, incl. difficulty) |
| `KDDTest-21.txt` | 1.7 MB | 11,850 | **Subset test set.** `KDDTest+.txt` minus the 21 most difficult-to-classify groups |
| `KDDTrain+.arff` | 17.9 MB | 125,973 | Alternate format (Weka `.arff`) of `KDDTrain+.txt` — **binary** normal/anomaly labels only |
| `KDDTrain+_20Percent.arff` | 3.6 MB | 25,192 | Alternate format of the 20% train subset (binary labels) |
| `KDDTest+.arff` | 3.2 MB | 22,544 | Alternate format of the full test set (binary labels) |
| `KDDTest-21.arff` | 1.7 MB | 11,850 | Alternate format of the -21 test subset (binary labels) |
| `index.html` | 0.03 MB | — | Saved NSL-KDD project web page (documentation) |
| `KDDTrain1.jpg` | 0.01 MB | — | Figure from the NSL-KDD website |
| `KDDTest1.jpg` | 0.01 MB | — | Figure from the NSL-KDD website |

### 1.2 CICIDS2017 (ML-ready) — folder `MachineLearningCSV/MachineLearningCVE/`

Each file: 79 columns (78 flow features + `Label`), one CSV per day/attack-scenario.
Total = **2,830,743 rows** — this is the canonical, widely-cited CICIDS2017 release.

| File | Size | Rows | Attack labels present |
|------|------|------|-----------------------|
| `Monday-WorkingHours.pcap_ISCX.csv` | 168.7 MB | 529,918 | BENIGN only |
| `Tuesday-WorkingHours.pcap_ISCX.csv` | 128.8 MB | 445,909 | BENIGN, FTP-Patator, SSH-Patator (Brute Force) |
| `Wednesday-workingHours.pcap_ISCX.csv` | 214.7 MB | 692,703 | BENIGN, DoS Hulk, DoS GoldenEye, DoS slowloris, DoS Slowhttptest, Heartbleed |
| `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv` | 49.6 MB | 170,366 | BENIGN, Web Attack — Brute Force, Web Attack — XSS, Web Attack — Sql Injection |
| `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv` | 79.3 MB | 288,602 | BENIGN, Infiltration (only 36 rows!) |
| `Friday-WorkingHours-Morning.pcap_ISCX.csv` | 55.6 MB | 191,033 | BENIGN, Bot (Botnet) |
| `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv` | 73.3 MB | 286,467 | BENIGN, PortScan |
| `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv` | 73.6 MB | 225,745 | BENIGN, DDoS |

### 1.3 CICIDS2017 (raw flow exports) — folder `GeneratedLabelledFlows/TrafficLabelling/`

Same 8 daily files as 1.2, but each has **85 columns**: the extra `Flow ID`,
`Source IP`, `Source Port`, `Destination IP`, `Destination Port`, `Protocol` and
`Timestamp` metadata, plus the raw per-flow features. These are the raw flow
exports from CICFlowMeter *before* the ML-ready cleanup of version 1.2.

| File | Size | Rows |
|------|------|------|
| `Monday-WorkingHours.pcap_ISCX.csv` | 256.2 MB | 529,918 |
| `Tuesday-WorkingHours.pcap_ISCX.csv` | 166.6 MB | 445,909 |
| `Wednesday-workingHours.pcap_ISCX.csv` | 272.4 MB | 692,703 |
| `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv` | 87.8 MB | **458,968** |
| `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv` | 103.7 MB | 288,602 |
| `Friday-WorkingHours-Morning.pcap_ISCX.csv` | 71.9 MB | 191,033 |
| `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv` | 97.2 MB | 286,467 |
| `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv` | 91.7 MB | 225,745 |

> **Important difference:** the raw version of the Thursday-Morning-WebAttacks
> file contains **458,968** rows, while the ML-ready version contains only
> **170,366**. The ML-ready version dropped ~288k flows (flows with missing /
> invalid flow-rate values, a documented quirk of the official release). The two
> versions otherwise have identical row counts.

---

## 2. Triage decisions

### 2.1 NSL-KDD — what is USED

| Selected files | Role |
|----------------|------|
| `nsl-kdd/KDDTrain+.txt` | **Training set** (full, 125,973 rows) |
| `nsl-kdd/KDDTest+.txt` | **Test set** (held-out, 22,544 rows) |

Why these two: they are the official NSL-KDD train/test split, used by virtually
every study that benchmarks on NSL-KDD, so our results stay comparable to the
literature (Thakkar & Lohiya 2021, etc.). The `.txt` versions are used instead of
the `.arff` because they carry the **full attack-type label** (e.g. `neptune`,
`satan`) needed to build the five classes Normal / DoS / Probe / R2L / U2R. The
`.arff` versions only have a binary normal/anomaly label.

### 2.2 NSL-KDD — what is IGNORED and why

| File | Reason |
|------|--------|
| `KDDTrain+_20Percent.txt` | 20% random subset. Useful for fast code-testing only. We have the **full** `KDDTrain+.txt` (125,973 rows), so there is **no need to fall back** to the subset — the subset exists for people whose machines can't handle the full set. We will use the full train set for final numbers. |
| `KDDTest-21.txt` | Variant used by some older studies to remove the hardest records; using it would inflate reported accuracy and make cross-study comparison harder. The official test set is `KDDTest+.txt`. |
| All 4 `.arff` files | Duplicate data, and only binary labels (lose the attack subtypes). |
| `index.html`, `KDDTrain1.jpg`, `KDDTest1.jpg` | Website documentation/figures, not data. |

### 2.3 CICIDS2017 — what is USED

**Source of truth = the `MachineLearningCVE` version** (the 79-column ML-ready CSVs).

Reasons:
1. It is the canonical, widely-cited release of CICIDS2017 used in ML papers
   (exactly 2,830,743 flows — the number cited in the literature).
2. It is already **cleaned and ML-ready**: numeric features only, ready to feed a
   classifier after scaling, and it has already dropped the malformed Web-Attack
   flows (458,968 → 170,366).
3. It **excludes identifying metadata** (`Flow ID`, IP addresses, ports,
   timestamps). The raw version includes these, and IP/timestamp columns are
   *information leaks* for a classifier — they let the model memorise specific
   hosts rather than learn general traffic patterns. Keeping them out makes the
   model genuinely useful.

The `GeneratedLabelledFlows` folder is the raw flow export the ML-ready version
was generated from — **duplicate traffic, ignored**, to avoid double-counting the
same flows.

### 2.4 Known data-quality notes (handled at load time in Phase 1)

1. **Encoding quirk in the ML-ready Web-Attacks file:** the "—" (en dash) inside
   labels such as `Web Attack — Brute Force` has already been corrupted to the
   replacement character `\uFFFD` in the ML-ready CSV (the raw version still has
   the original Windows-1252 byte). Labels will be normalised to clean categories
   (`Web Attack`) when loading.
2. **Trailing spaces:** a small number of labels carry trailing whitespace (e.g.
   `Heartbleed ` in the Wednesday file). Labels will be stripped on load.
3. **Extreme class imbalance:** Infiltration (36 rows), Heartbleed (11), Web
   Attack — Sql Injection (21), FTP/SSH-Patator, DoS, PortScan, DDoS and Bot all
   have far fewer rows than BENIGN (≈2.2 M rows). This is exactly why Phase 2
   applies SMOTE to the training split only.
4. **NSL-KDD `.txt` schema:** all `.txt` files have **43** columns (41 features +
   label + difficulty). The difficulty column (a 0–21 score) is metadata, **not** a
   feature, and will be dropped at load time so the model cannot peek at it.

---

## 3. Final selection summary

| Dataset | Files used (train) | Files used (test) | Rows (train/test) |
|---------|--------------------|-------------------|-------------------|
| NSL-KDD | `nsl-kdd/KDDTrain+.txt` | `nsl-kdd/KDDTest+.txt` | 125,973 / 22,544 |
| CICIDS2017 | All 8 `MachineLearningCVE/*.csv` (train/test split created inside Phase 1-3) | — | 2,830,743 total |

*CICIDS2017 is delivered as a single (per-day) collection without an official
train/test split, so Phase 1 will create a stratified train/test split from it
(e.g. 80/20) — the NSL-KDD split, by contrast, is pre-defined by the dataset.
*
