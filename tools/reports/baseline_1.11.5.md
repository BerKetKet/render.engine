# Baseline Metrics (`kindle_render` v1.11.5 — Port-Ready Reference)

- **Hash equivalence vs `v1.11.4`**: `YES` (100% identical pixel & layout SHA-256 on all corpora and `sizes_00..07`)
- **Environment fingerprint**: `0a54d71bb5a5988b99f67f4281f2ff9d339c91c8324fc6496a50d77ebf952e3d`

| Corpus / Series | Pages Compared | Bitwise-Identical | Pos Exact Lines | Pos-Indep Lines | Diff Pixels | Mean Pixel Match | Mean Ink IoU |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `probe` | 86 / 98 | 43/86 | 2753/2863 | 2755/2863 | 357,394 | 99.8216% | 0.9872 |
| `exam1` | 70 / 70 | 50/70 | 1452/1568 | 1462/1568 | 1,506,804 | 99.0760% | 0.9566 |
| `exam2` | 65 / 65 | 40/65 | 1395/1529 | 1416/1529 | 1,034,912 | 99.3165% | 0.9607 |
| `exam3_normal` | 82 / 82 | 60/82 | 1899/2027 | 1927/2027 | 708,015 | 99.6294% | 0.9658 |
| `exam3_small` | 54 / 54 | 32/54 | 1518/1651 | 1543/1651 | 845,237 | 99.3281% | 0.9505 |
| `e3_compact` | 56 / 56 | 33/56 | 1490/1713 | 1531/1713 | 2,086,061 | 98.4009% | 0.9180 |
| `e3_large` | 124 / 124 | 87/124 | 2341/2652 | 2392/2652 | 2,667,605 | 99.0765% | 0.9206 |
| `tables_images` | 44 / 44 | 4/44 | 299/894 | 521/894 | 8,503,517 | 91.7039% | 0.5836 |
| `ti_compact` | 35 / 35 | 3/35 | 280/733 | 452/733 | 6,723,947 | 91.7533% | 0.6481 |
| `ti_large` | 57 / 57 | 3/57 | 286/1086 | 586/1086 | 10,400,325 | 92.1675% | 0.4855 |
| `sizes_00` | 54 / 54 | 32/54 | 1518/1651 | 1543/1651 | 845,237 | 99.3281% | 0.9505 |
| `sizes_01` | 0 / 59 | N/A | N/A | N/A | N/A | N/A | N/A |
| `sizes_02` | 0 / 69 | N/A | N/A | N/A | N/A | N/A | N/A |
| `sizes_03` | 0 / 73 | N/A | N/A | N/A | N/A | N/A | N/A |
| `sizes_04` | 82 / 82 | 60/82 | 1899/2027 | 1927/2027 | 708,015 | 99.6294% | 0.9658 |
| `sizes_05` | 0 / 89 | N/A | N/A | N/A | N/A | N/A | N/A |
| `sizes_06` | 0 / 101 | N/A | N/A | N/A | N/A | N/A | N/A |
| `sizes_07` | 0 / 122 | N/A | N/A | N/A | N/A | N/A | N/A |
| `synthetic` | 0 / 3 | golden 3/3 | N/A | N/A | N/A | N/A | N/A |
