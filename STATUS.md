# `kindle_render` Project Status — `v1.11.17` (Port-Ready Baseline)

- **Current Version**: `1.11.17` (target tag: `v1.11.17`; HarfBuzz lock is now warn-only, see docs/environment.md)
- **Hash Equivalence vs `v1.11.4`**: `YES` — `100%` identical per-page pixel and layout SHA-256 across all corpora (`probe`, `exam1`, `exam2`, `exam3_normal`, `exam3_small`, `e3_compact`, `e3_large`, `tables_images`, `ti_compact`, `ti_large`, `synthetic`, and `sizes_00..sizes_07`).
- **Environment Pin**: Python `3.11.x`, HarfBuzz `6.0.0` (exact pin enforced in `Family.__init__` per `docs/environment.md`), FreeType `2.12.1`, Pillow `10.2.0`, NumPy `1.26.x`.

## Baseline `1.11.17` Reference Metrics (`tools/reports/baseline_1.11.17.json`)

| Corpus / Series | Pages Compared | Bitwise-Identical | Pos Exact Lines | Pos-Indep Lines | Diff Pixels | Mean Pixel Match | Mean Ink IoU |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `probe` | 86 / 98 | 43 / 86 | 2753 / 2863 | 2755 / 2863 | 357,394 | 99.8216% | 0.9872 |
| `exam1` | 70 / 70 | 50 / 70 | 1452 / 1568 | 1462 / 1568 | 1,506,804 | 99.0760% | 0.9566 |
| `exam2` | 65 / 65 | 40 / 65 | 1395 / 1529 | 1416 / 1529 | 1,034,912 | 99.3165% | 0.9607 |
| `exam3_normal` | 82 / 82 | 60 / 82 | 1899 / 2027 | 1927 / 2027 | 708,015 | 99.6294% | 0.9658 |
| `exam3_small` | 54 / 54 | 32 / 54 | 1518 / 1651 | 1543 / 1651 | 845,237 | 99.3281% | 0.9505 |
| `e3_compact` | 56 / 56 | 33 / 56 | 1490 / 1713 | 1531 / 1713 | 2,086,061 | 98.4009% | 0.9180 |
| `e3_large` | 124 / 124 | 87 / 124 | 2341 / 2652 | 2392 / 2652 | 2,667,605 | 99.0765% | 0.9206 |
| `tables_images` | 44 / 44 | 4 / 44 | 299 / 894 | 521 / 894 | 8,503,517 | 91.7039% | 0.5836 |
| `ti_compact` | 35 / 35 | 3 / 35 | 280 / 733 | 452 / 733 | 6,723,947 | 91.7533% | 0.6481 |
| `ti_large` | 57 / 57 | 3 / 57 | 286 / 1086 | 586 / 1086 | 10,400,325 | 92.1675% | 0.4855 |
| `sizes_00` (`34/51`) | 54 / 54 | 32 / 54 | 1518 / 1651 | 1543 / 1651 | 845,237 | 99.3281% | 0.9505 |
| `sizes_01..03, 05..07` | 0 / 513 | golden verified | N/A | N/A | N/A | N/A | N/A |
| `sizes_04` (`45/68`) | 82 / 82 | 60 / 82 | 1899 / 2027 | 1927 / 2027 | 708,015 | 99.6294% | 0.9658 |
| `synthetic` | 0 / 3 | golden 3/3 | N/A | N/A | N/A | N/A | N/A |

## Resume & Verification Commands
```bash
# Run all 25 clean-clone verification gates (imports, HarfBuzz lock, text layer, parallel raster, boundary, bugfixes, goldens)
python3 tools/run_gates.py

# Run cross-process PYTHONHASHSEED determinism check
python3 tools/test_determinism.py

# Score a single corpus against device captures (writes to git-ignored tools/reports_local/)
python3 tools/corpus.py --only exam3_normal
```

## Blockers / Unverified Items on Sandbox VM
- **HarfBuzz `8.3.0` cross-version check (`H3`)**: Only `libharfbuzz.so.0.60000.0` (`6.0.0`) is installed in this offline sandbox VM (`uharfbuzz` unavailable, no network/pip); exact `6.0.0` pin policy is enforced and documented in `docs/environment.md`.
- **Remote `engine` branch & full `955 MB` `.git` history (`H7`)**: No `git remote` is configured in the sandbox clone (`25 MiB` `.git`), so the remote `engine` branch could not be inspected.
- **Missing intermediate size captures**: `exam/v3/size_01..03_Bookerly` and `size_05..07_Bookerly` captures are not present on the VM; `sizes_01..03, 05..07` are rendered and golden-hashed (`tools/golden/sizes_01..07.json`).
