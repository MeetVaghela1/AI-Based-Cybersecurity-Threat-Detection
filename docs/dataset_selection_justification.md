# Dataset Selection Justification

This project uses **NSL-KDD** and **CICIDS2017** as its two benchmark datasets.
This selection is deliberate rather than a default choice: the two datasets are
complementary in age, feature structure, and attack diversity, which allows the
study to directly test cross-dataset robustness — one of the core research gaps
identified in the literature review (Thakkar & Lohiya, 2021).

## Comparison of Public IDS Benchmark Datasets

| Dataset | Year | Size | Attack Coverage | Key Limitation |
|---|---|---|---|---|
| KDD Cup '99 | 1999 | ~4.9M records | DoS, Probe, R2L, U2R | Outdated traffic patterns; heavy redundancy |
| NSL-KDD (selected) | 2009 | 148,517 records | DoS, Probe, R2L, U2R | Still reflects late-1990s traffic structure |
| UNSW-NB15 | 2015 | ~2.5M records | 9 attack types (Fuzzers, DoS, Exploits, etc.) | Partly synthetic traffic; smaller benchmarking base |
| CICIDS2017 (selected) | 2017 | ~2.8M records | 14 attack categories, 80 features | Known label-inconsistency/class-imbalance issues |
| CSE-CIC-IDS2018 | 2018 | Very large (100GB+) | Similar to CICIDS2017, larger scale | Impractical compute/time for a single dissertation |
| Bot-IoT / TON_IoT | 2019-2020 | Varies | IoT-specific attacks | Domain-specific (IoT), not general enterprise traffic |

## Rationale for the Selected Pair

- **Complementary by design:** NSL-KDD is a refined, widely-benchmarked classic
  dataset (Tavallaee et al., 2009); CICIDS2017 is a modern, high-dimensional
  dataset with contemporary attack traffic (Sharafaldin et al., 2018). Testing
  across both spans roughly two decades of network traffic evolution.
- **Comparability with prior work:** NSL-KDD remains one of the most cited IDS
  benchmarks, enabling direct comparison of this project's results against a
  large body of existing literature.
- **Practical feasibility:** Alternatives such as CSE-CIC-IDS2018 (100GB+) or
  UNSW-NB15 (synthetic attack-tool traffic) introduce compute or methodological
  constraints not well suited to a 16-week, Google Colab-based project;
  UNSW-NB15 and KDD Cup '99 are retained as documented backup datasets in the
  project risk register.
- **Directly serves the stated research gap:** cross-dataset generalisability
  is one of this project's three named gaps in current knowledge, making the
  two-dataset design methodologically necessary rather than incidental.

## References

- Moustafa, N., & Slay, J. (2015). UNSW-NB15: A comprehensive data set for
  network intrusion detection systems. In *Military Communications and
  Information Systems Conference (MilCIS)*.
- Sharafaldin, I., Lashkari, A. H., & Ghorbani, A. A. (2018). Toward generating
  a new intrusion detection dataset and intrusion traffic characterization.
  In *Proceedings of the International Conference on Information Systems
  Security and Privacy (ICISSP)*, 108–116.
- Tavallaee, M., Bagheri, E., Lu, W., & Ghorbani, A. A. (2009). A detailed
  analysis of the KDD CUP 99 data set. In *IEEE Symposium on Computational
  Intelligence for Security and Defense Applications (CISDA)*.
- Thakkar, A., & Lohiya, R. (2021). A review of the advancement in intrusion
  detection datasets. *Procedia Computer Science, 167*, 636–645.
