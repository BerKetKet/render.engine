# `kindle_render` Status Log (`STATUS.md`)

## Current Version & Milestone
- **Version**: `1.9.0` (`kindle_render/__init__.py`)
- **Tag**: `rhythm-1.9.0`
- **Completed**:
  - **Stage A `[P]` (Hygiene, tag `1.8.0-rc1`)**: HarfBuzz `6.0.0` version lock & loud failure (`kindle_render/fonts.py`, `tools/test_harfbuzz_lock.py`); `NO-GOLDEN` reporting + `exam3_normal` & `exam3_small` baseline goldens + `page_bottom` check (`tools/reports/stage_a/page_bottom_verification.json`); `tools/rhythm.py` `unaligned` pair filter across all 5 corpora (`tools/reports/rhythm/coverage.json`, `coverage.md`, `base.json`); complete grep-backed spacing inventory (`tools/reports/rhythm/inventory.md`).
  - **Stage B `[P]` (Hypothesis Registry)**: Read-only `docs/hypotheses/kindle_formulae_v0.md` (`SHA-256: 5e24606c502f14c3de8d77536cdb74f5eb00eaa0d6bc4e87d78807b34a692c81`), pure evaluators in `tools/hypotheses/evaluate.py`, and 5-corpus evaluation in `tools/reports/hypotheses/registry.json` & `reconcile.md`.
  - **Stage C `[F]` (Cross-Geometry Vertical Rhythm)**: Removed all `std_body_pitch == 57` / `pitch_px() == 57` branches and back-solved 4–5 digit constants (`4.04124`, `0.6632`, `0.8140`, etc.) in `kindle_render/page.py`; implemented cross-geometry `eff_body_pitch`, 2–3 digit heading margin multipliers (`0 px` residual across all 36 cells), `(10/17) * std_body_pitch` spacer advance, `base_root_em_px` horizontal `em`/`rem` resolution, and inter-word shrink (`w <= L + z`) in `break_balanced_ragged` (`tools/reports/rhythm/c1_models.md`, `c2_logo_cv.md`, `c3_smoothness.md`, `c4_anomalies.md`).
  - **Stage D `[F]` (Page-Break Rules)**: Retained page-top `mt` on overflowing list items (`exam3_normal` p.39), added page-top `+8 px` offset and `_mark_page_non_empty()` on overflowing uncollapsed tables (`exam3_normal` p.41), and added page-break support in `add_hr` (`exam3_small` p.25–26) (`tools/reports/stage_d/page_breaks.md`).
  - **Stage E `[F]` (Ragged Text & Last-Glyph `1 px` Rounding)**: Split internal `<br/>` forced-break segments in `break_kp` (`in_forced_seg=True`), making `exam3_normal` p.48 (`24/24` lines), `exam3_normal` p.49 (`28/28` lines), and `exam3_small` p.31 (`33/33` lines) `100%` bitwise identical (`tools/reports/stage_e/e1_ragged.md`); completed 5-corpus last-glyph `1 px` rounding census (`tools/reports/stage_e/e2_last_glyph.md`); wrote `tools/reports/REPORT_RHYTHM.md`.

## 5-Corpus Metrics at `rhythm-1.9.0`
- **`probe` (`42 px, pitch 57`)**: `37/86` exact pages | `2,703/2,863` pos lines | `2,705/2,863` PI lines | `2` displaced | `476,566` diff px
- **`exam1` (`45 px, pitch 68`)**: `42/70` exact pages | `1,405/1,568` pos lines (`+3`) | `1,411/1,568` PI lines | `6` displaced | `1,577,125` diff px (`-16,039`)
- **`exam2` (`42 px, pitch 57`)**: `35/65` exact pages | `1,322/1,529` pos lines | `1,343/1,529` PI lines | `21` displaced | `1,140,913` diff px
- **`exam3_normal` (`45 px, pitch 68`)**: `42/82` exact pages (`+4`) | `1,835/2,027` pos lines (`+95`) | `1,847/2,027` PI lines (`+59`) | `12` displaced | `965,580` diff px (`-1,927,480`)
- **`exam3_small` (`34 px, pitch 51`)**: `16/54` exact pages (`+6`) | `1,430/1,651` pos lines (`+439`) | `1,455/1,651` PI lines (`+39`) | `25` displaced | `1,114,849` diff px (`-4,424,172`)
- **Total across all 5 corpora**: `172/357` exact pages (`+10`), `8,695/9,638` pos lines (`+537`), `8,761/9,638` PI lines (`+98`), `5,275,033` diff px (`-6,367,691`, `-54.7%`).

## NEXT (Resume Instructions for Next Session — Stage F)
- **STOP POINT REACHED**: Tag `rhythm-1.9.0` is complete and awaits owner review before Stage F (`Contents Page`).
- **Exact Commands to Verify & Resume at Stage F**:
  ```bash
  python3 tools/check_imports.py
  python3 tools/test_harfbuzz_lock.py
  python3 tools/test_parallel_raster.py
  python3 tools/test_text_layer.py
  python3 tools/corpus.py --only probe --no-determinism
  python3 tools/corpus.py --only exam1 --no-determinism
  python3 tools/corpus.py --only exam2 --no-determinism
  python3 tools/corpus.py --only exam3_normal --no-determinism
  python3 tools/corpus.py --only exam3_small --no-determinism
  ```
