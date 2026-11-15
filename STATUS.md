# STATUS — `kindle_render` v1.8.0-rc1

## Current State
- **Version**: `1.8.0-rc1` (`kindle_render/__init__.py`)
- **Latest Tag**: `1.8.0-rc1` (previous partial Round 1 tag renamed from `round1-1.8.0` to `round1-partial`)
- **Environment Fingerprint**: `948049bcd0bf17c4b5ee1680c539ea99f16919e0393546324b68e3651ede6439` (`Python 3.11.2`, `Pillow 11.1.0`, `libjpeg-turbo 3.1.0`, `zlib 1.2.13`, `FreeType 2.12.1`, `HarfBuzz 6.0.0`, `numpy 1.24.2`)

## Completed Stages
- **Stage A [P] — Hygiene (`1.8.0-rc1`)**:
  - **A1 (HarfBuzz Lock & Loud Failure)**: `kindle_render/fonts.py` verifies `libharfbuzz.so` presence and exact version match against `requirements.lock` (`6.0.0`), failing loudly unless `--allow-unshaped` is passed (`manifest.json` records `allow_unshaped`). Verified via `tools/test_harfbuzz_lock.py`.
  - **A2 (Goldens & `page_bottom` Verification)**: `tools/corpus.py` prints `NO-GOLDEN` when a golden file is absent. Generated pixel + layout goldens (`tools/golden/exam3_normal.json`, `tools/golden/exam3_small.json`) and recorded `environment_fingerprint` across all golden files. Verified `page_bottom` across pages 2..N on `exam3_normal` (`max_ink_y = 2202` on p.62) and `exam3_small` (`max_ink_y = 2202` on p.39) in `tools/reports/stage_a/page_bottom_verification.json`.
  - **A3 (Version Hygiene)**: Set `__version__ = "1.8.0-rc1"` across `kindle_render/__init__.py`, `kindle_render/ir.py`, `README.md`, `CHANGELOG.md`, and `STATUS.md`. Renamed tag `round1-1.8.0` to `round1-partial` and tagged `1.8.0-rc1`.
  - **A4 (Rhythm Harness Unaligned Filter & Coverage)**: Updated `tools/rhythm.py` to label boundaries with `|delta| > pitch` as `"unaligned"` and exclude them from statistics and coverage counts. Generated `tools/reports/rhythm/gaps_<corpus>.json`, `base.json`, `coverage.json`, and `coverage.md` across all 5 corpora.
  - **A5 (Complete Calibration Inventory)**: Audited `config.py`, `epub.py`, `layout.py`, and `page.py` via regex grep and documented every geometry-keyed branch, table, and constant in `tools/reports/rhythm/inventory.md`.

## Baseline Metrics Across All 5 Corpora (at `1.8.0-rc1`)
- `probe` (`42px, pitch 57`): `37/86` exact pages | `2,703/2,863` pos lines | `2,705/2,863` PI lines | `2` displaced lines | `476,566` diff px
- `exam1` (`45px, pitch 68`): `42/70` exact pages | `1,402/1,568` pos lines | `1,411/1,568` PI lines | `9` displaced lines | `1,593,164` diff px
- `exam2` (`42px, pitch 57`): `35/65` exact pages | `1,322/1,529` pos lines | `1,343/1,529` PI lines | `21` displaced lines | `1,140,913` diff px
- `exam3_normal` (`45px, pitch 68`): `38/82` exact pages | `1,740/2,027` pos lines | `1,788/2,027` PI lines | `48` displaced lines | `2,893,060` diff px
- `exam3_small` (`34px, pitch 51`): `10/54` exact pages | `991/1,651` pos lines | `1,416/1,651` PI lines | `425` displaced lines | `5,539,021` diff px

## NEXT
- **Stage B [P] — Hypothesis Registry (no engine change)**:
  1. Write `tools/reports/hypotheses/reconcile.md` reconciling every numbered formula in `docs/hypotheses/kindle_formulae_v0.md` against the codebase (`file:line`, `match`/`mismatch`/`not found`).
  2. Implement pure functions in `tools/hypotheses/evaluate.py` and write `tools/reports/hypotheses/registry.json` (`SUPPORTED` / `REFUTED` / `UNTESTABLE` per geometry).
- **Exact Commands to Resume**:
  ```bash
  python3 tools/check_imports.py
  python3 tools/test_harfbuzz_lock.py
  python3 tools/corpus.py --only exam3_small --no-determinism
  ```
