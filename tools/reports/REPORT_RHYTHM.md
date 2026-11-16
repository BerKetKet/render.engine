# `kindle_render` v1.9.0 (`rhythm-1.9.0`) — Unified Vertical Rhythm, Page-Break & Ragged Text Report

## 1. Cross-Corpus Progression (`1.8.0-rc1` -> `rhythm-1.9.0`)

| Corpus | Geometry (`size_px`, `pitch`) | `1.8.0-rc1` Exact Pages | `1.9.0` Exact Pages | `1.8.0-rc1` Pos Lines | `1.9.0` Pos Lines | `1.8.0-rc1` PI Lines | `1.9.0` PI Lines | `1.8.0-rc1` Diff Pixels | `1.9.0` Diff Pixels |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `probe` | `42 px`, `pitch 57`, `39..1041` | `37 / 86` | **`37 / 86`** | `2,703 / 2,863` | **`2,703 / 2,863`** | `2,705 / 2,863` | **`2,705 / 2,863`** | `476,566` | **`476,566`** |
| `exam1` | `45 px`, `pitch 68`, `79..1001` | `42 / 70` | **`42 / 70`** | `1,402 / 1,568` | **`1,405 / 1,568`** | `1,411 / 1,568` | **`1,411 / 1,568`** | `1,593,164` | **`1,577,125`** |
| `exam2` | `42 px`, `pitch 57`, `79..1001` | `35 / 65` | **`35 / 65`** | `1,322 / 1,529` | **`1,322 / 1,529`** | `1,343 / 1,529` | **`1,343 / 1,529`** | `1,140,913` | **`1,140,913`** |
| `exam3_normal` | `45 px`, `pitch 68`, `79..1001` | `38 / 82` | **`42 / 82`** (`+4`) | `1,740 / 2,027` | **`1,835 / 2,027`** (`+95`) | `1,788 / 2,027` | **`1,847 / 2,027`** (`+59`) | `2,893,060` | **`965,580`** (`-1,927,480`) |
| `exam3_small` | `34 px`, `pitch 51`, `79..1001` | `10 / 54` | **`16 / 54`** (`+6`) | `991 / 1,651` | **`1,430 / 1,651`** (`+439`) | `1,416 / 1,651` | **`1,455 / 1,651`** (`+39`) | `5,539,021` | **`1,114,849`** (`-4,424,172`) |
| **TOTAL (All 5)** | **357 compared pages** | **`162 / 357`** | **`172 / 357` (`+10`)** | **`8,158 / 9,638`** | **`8,695 / 9,638` (`+537`)** | **`8,663 / 9,638`** | **`8,761 / 9,638` (`+98`)** | **`11,642,724`** | **`5,275,033` (`-6,367,691`)** |

---

## 2. Stage-by-Stage Summary & Evidence Index

### Stage A `[P]` — Hygiene (`commit 6dd8a2d`, tag `1.8.0-rc1`)
- **A1 (HarfBuzz Lock)**: Locked `libharfbuzz.so.0` to `6.0.0` in `kindle_render/fonts.py` (`HARFBUZZ_LOCKED_VERSION = "6.0.0"`), raising `RuntimeError` by default unless `allow_unshaped=True`; verified by `tools/test_harfbuzz_lock.py`.
- **A2 (`NO-GOLDEN` & `exam3` Baseline Goldens)**: Added `NO-GOLDEN` status reporting in `tools/corpus.py`, verified `page_bottom` (`2203` vs `2205` identical on `exam3_small`, `tools/reports/stage_a/page_bottom_verification.json`), and recorded baseline goldens for `exam3_normal` and `exam3_small`.
- **A3 (Version & Tag Hygiene)**: Renamed premature `round1-1.8.0` tag to `round1-partial` and tagged `1.8.0-rc1`.
- **A4 (`tools/rhythm.py` Unaligned Filter)**: Separated `aligned` (`|dev_text_len - ren_text_len| <= max(3, 0.15 * max_len)`) vs `unaligned` pairs across all 5 corpora (`tools/reports/rhythm/coverage.json`, `coverage.md`, `base.json`).
- **A5 (Complete Grep-Backed Inventory)**: Audited every vertical and horizontal spacing formula and constant across `kindle_render/` in `tools/reports/rhythm/inventory.md`.

### Stage B `[P]` — Hypothesis Registry (`commit 2ea8367`)
- Archived `kindle_formulae.md` read-only (`0444`) at `docs/hypotheses/kindle_formulae_v0.md` (`SHA-256: 5e24606c502f14c3de8d77536cdb74f5eb00eaa0d6bc4e87d78807b34a692c81`).
- Implemented pure-function evaluators in `tools/hypotheses/evaluate.py` and generated `tools/reports/hypotheses/registry.json` and `tools/reports/hypotheses/reconcile.md` classifying `H01`–`H14` (`SUPPORTED`, `REFUTED`, `UNTESTABLE`) across `(34, 51)`, `(42, 57)`, and `(45, 68)`.

### Stage C `[F]` — Cross-Geometry Vertical Rhythm (`commits a2bca22`, `b2e4c2a`)
- **C1 (Model Comparison)**: Eliminated all `std_body_pitch == 57` and `pitch_px() == 57` geometry conditionals and unverified 4–5 digit back-solved constants (`4.04124`, `0.6632`, `0.8140`, etc.) in `kindle_render/page.py`. Derived unified effective pitch `eff_body_pitch = max(float(std_body_pitch), (68.0 / 45.0) * size_px)` when `extra_lead > 0`, 2–3 digit heading margin multipliers with `0 px` residual across all 36 `(geometry, heading_level)` cells, and `(10/17) * std_body_pitch` spacer advance (`30 px` at `P=51`, `40 px` at `P=68`). Full details in `tools/reports/rhythm/c1_models.md` and `c1_models.json`.
- **C2 (Leave-One-Geometry-Out CV)**: `0.0 px` MAE across all 3 held-out geometry folds (`tools/reports/rhythm/c2_logo_cv.md`).
- **C3 (Smoothness Sweep `30..50 px`)**: Verified strict monotonicity (`h1 >= h2 >= h3 >= h4 >= h5 >= h6`) across all font sizes `30..50 px` (`tools/reports/rhythm/c3_smoothness.md`).
- **C4 (`exam3_small` p.3 & p.43 Anomalies)**: Fixed inter-word shrink (`w <= L + z`) and `w_last = 0.65` in `break_balanced_ragged` (`kindle_render/layout.py`), making `exam3_small` p.3 and p.43 `100%` bitwise identical (`tools/reports/rhythm/c4_anomalies.md`).

### Stage D `[F]` — Page-Break Rules (`commits a249f04`, `84d9548`)
- Retained `top_mt = int(round(b.mt_em * vem_px * b.scale))` when `i == 0` of a list item overflows to a new page (`exam3_normal` p.39).
- Added `+8 px` page-top offset when an uncollapsed table with `extra_lead > 0` overflows to a new page and marked page non-empty at the end of `add_table` (`exam3_normal` p.41).
- Added page-break handling in `add_hr` when `self.y + top_gap + 3 > c.page_bottom` instead of silently clipping the `<hr/>` rule (`exam3_small` p.25–26).
- Full report and crops in `tools/reports/stage_d/page_breaks.md` and `page_breaks.json`.

### Stage E `[F]` — Ragged Text & Last-Glyph `1 px` Rounding
- **E1 (`<br/>`-Segment DP & `B7` Guard Scope)**: Split `items` at internal `<br/>` forced breaks inside `break_kp` (`in_forced_seg=True`), applying `break_kp`'s quadratic ragged cost and restricting the `B7` paragraph-final hyphen penalty (`w10 == 1`) to true paragraph ends (`not in_forced_seg`). Result: `exam3_normal` p.48 (`24/24` lines, `0` diff px), `exam3_normal` p.49 (`28/28` lines, `0` diff px), and `exam3_small` p.31 (`33/33` lines, `0` diff px) are all `100%` bitwise identical! (`tools/reports/stage_e/e1_ragged.md`).
- **E2 (Last-Glyph `1 px` Right-Edge Rounding)**: Completed full 5-corpus census (`tools/reports/stage_e/e2_last_glyph.md` & `.json`). While `34` justified lines across the 5 corpora would become exact by shifting `gs[-1].x -= 1` at the half-pixel tie `(start26 + off) & 63 == 32` (`'k'` `26.5 px`, `'m'` `44.5 px`, `'e'` `17.5 px`), **`61` lines** at the exact same terminal glyph and `x` coordinate (`975`, `957`, `984`) are **already `100%` bitwise identical**. Per Stage E2's zero-regression rule, `place_phase = 0.5` is preserved unchanged.

---

## 3. Gate Verification (`G1`–`G6`)
- **`G1` (Goldens)**: All 5 corpora (`probe`, `exam1`, `exam2`, `exam3_normal`, `exam3_small`) + `synthetic` pass pixel and layout IR SHA-256 golden checks (`golden_passed=True`, `layout_golden_passed=True`).
- **`G2` (5-Corpus Metrics)**: Zero regressions on any previously identical page across all 5 corpora; `172/357` exact pages (`+10`), `8,695/9,638` positional-exact lines (`+537`), total diff pixels reduced by `6,367,691` (`-54.7%`).
- **`G3` (Determinism)**: Double-render pixel and layout SHA-256 determinism verified across all corpora.
- **`G4` (Import Graph)**: `python3 tools/check_imports.py` -> `passed=True errors=0`.
- **`G5` (Parallel Raster & Text Layer)**: `python3 tools/test_parallel_raster.py` -> `ALL PASSED`; `python3 tools/test_text_layer.py` -> `ALL PASSED`.
- **`G6` (HarfBuzz Lock & Fingerprint)**: `python3 tools/test_harfbuzz_lock.py` -> `PASSED` (`libharfbuzz.so.0` `6.0.0`, `FreeType 2.12.1`, `Pillow 12.0.0`).
