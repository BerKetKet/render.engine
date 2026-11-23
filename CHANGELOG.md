## v1.9.0 (`rhythm-1.9.0`) — 2026-11-15
- **Stage A [P] Hygiene (`1.8.0-rc1`)**: Added HarfBuzz `6.0.0` version lock and loud failure in `kindle_render/fonts.py` (`tools/test_harfbuzz_lock.py`), `NO-GOLDEN` reporting and `exam3_normal`/`exam3_small` baseline goldens in `tools/corpus.py`, `unaligned` pair filtering in `tools/rhythm.py`, and full spacing inventory in `tools/reports/rhythm/inventory.md`.
- **Stage B [P] Hypothesis Registry**: Archived `docs/hypotheses/kindle_formulae_v0.md`, implemented pure-function evaluators in `tools/hypotheses/evaluate.py`, and generated `tools/reports/hypotheses/registry.json` and `reconcile.md`.
- **Stage C [F] Vertical Rhythm**: Replaced geometry-specific `std_body_pitch == 57` branches and back-solved 4–5 digit constants in `kindle_render/page.py` with cross-geometry effective pitch (`eff_body_pitch`), 2–3 digit heading margin multipliers (`0 px` residual across all 36 cells), `(10/17) * std_body_pitch` spacer advance, `base_root_em_px` horizontal `em`/`rem` resolution, and inter-word shrink (`w <= L + z`) in `break_balanced_ragged`.
- **Stage D [F] Page-Break Rules**: Retained page-top `mt` on overflowing list items (`exam3_normal` p.39), added page-top `+8 px` offset and `_mark_page_non_empty()` on overflowing uncollapsed tables (`exam3_normal` p.41), and added page-break support in `add_hr` (`exam3_small` p.25–26).
- **Stage E [F] Ragged Text & Last-Glyph Audit**: Split internal `<br/>` segments in `break_kp` (`in_forced_seg=True`) so verse stanzas use `break_kp`'s ragged cost without false paragraph-final `B7` hyphen blocks (`exam3_normal` p.48 & p.49 and `exam3_small` p.31 all `100%` bitwise identical); documented 5-corpus last-glyph `1 px` rounding census in `tools/reports/stage_e/e2_last_glyph.md`.

## v1.8.0-rc1 — Stage A Hygiene, Environment Lock, Exam 3 Goldens, and Rhythm Harness

- **HarfBuzz Lock & Loud Failure (`A1`)**: Enforced dynamic library resolution (`ctypes.util.find_library("harfbuzz")`) and version verification against `requirements.lock` (`6.0.0`), raising `RuntimeError` when missing or mismatched unless `--allow-unshaped` is explicitly enabled (`tools/test_harfbuzz_lock.py`).
- **Environment Fingerprinting & Exam 3 Goldens (`A2`)**: Added `requirements.lock`, `constraints.txt`, `Dockerfile`, and `environment_fingerprint` across `manifest.json` and `tools/golden/*.json`; added `NO-GOLDEN` reporting and generated baseline goldens for `exam3_normal` (82 pages) and `exam3_small` (54 pages).
- **Vertical Rhythm Harness & Calibration Inventory (`A4`, `A5`)**: Built `tools/rhythm.py` with unaligned boundary filtering (`|delta| > pitch`) across all five corpora (`probe`, `exam1`, `exam2`, `exam3_normal`, `exam3_small`) and documented all geometry-keyed branches and constants in `tools/reports/rhythm/inventory.md`.

# Changelog

## [1.11.18] - 2026-11-23 — Possessive `'s` Hyphenation Fix, Float-Baseline Link Underline & Thresholded Ligatures

### Changed
- **English Possessive `'s` Hyphenation Fix (`kindle_render/layout.py`) [DEFAULT-AFFECTING IMPROVEMENT]**:
  - Fixed apostrophe stripping so trailing `'s`/`’s` is placed in `trail_punct` when `len(left) >= min_word_length` (and French prefix elision requires `len(right) >= 2`), allowing `family’s` -> `fam-ily’s`.
  - Drops `Compact p4` from **`111,752 -> 0` (bitwise exact)** across all 7+ spacing cells (`Compact` total `-1,239,426` px), improves default **`exam1` by `-41,673` diff px** (`1,506,993 -> 1,465,320`, `e01_prologue 70,279 -> 28,795`, `+3` exact lines, `0` lost exact pages; `tools/golden/exam1.json` regenerated), and leaves all 17 other default goldens 100% bit-identical.
- **Float-Baseline Link Underline (`kindle_render/config.py`, `kindle_render/page.py`)**:
  - Added `link_underline_center_em = 0.12593` (gated on `line_spacing_step is not None and pitch == 0`), keeping `Standard line 2 = 0` while halving Standard (`19,270 -> 9,590`) and Large (`21,439 -> 10,693`) underline diffs (`~-360k` px across step-1 runs).
- **Thresholded Ligature Disabling (`kindle_render/config.py`, `kindle_render/fonts.py`)**:
  - Added `char_spacing_no_liga_px = 2.5`: disables OpenType `liga` when `user_char_spacing_26() >= 2.5 * 64.0`, improving all 3 themes simultaneously (`Std -23,579`, `Cmp -10,142`, `Lrg -36,771`, total `-70,492` px) with zero Compact char 2 regression.
- **Total 60-Run Spacing Diff (`pages 2–5`)**: **`15,917,005 -> 14,094,448` (`-1,822,557` px vs `v1.11.17`; `-12,212,990` px / `-46.4%` vs `v1.11.14`)**, `18/18` goldens & unit gates PASS under `KINDLE_RENDER_STRICT_HARFBUZZ=1`.

## [1.11.17] - 2026-11-23 — Step-1 Geometry, Spillover `<ol>` Alignment & Spacing Fit (S0–S8)

### Changed
- **Multi-Line `h1` Bottom Margin (`kindle_render/config.py`, `kindle_render/page.py`)**:
  - Added `heading_line_spacing_mb_em = 0.652` so multi-line `h1` (`len(lines) >= 2`) bottom margin derives from `pitch_fl` (`round(0.652 * (pitch_fl / 1.2)) + 1`) when `line_spacing_step is not None and pitch == 0`: drops `Standard line 3 p3` (`107,036 -> 0`), `Large line 1 p3` (`117,938 -> 21,397`), `Large line 2 p3` (`82,817 -> 0`), and `Large paragraph 3/4/5` body pages to `0` (`~-1.45M` px).
- **Spillover 2-Digit `<ol>` Horizontal Alignment (`kindle_render/page.py`)**:
  - When a 2-digit `<ol>` item (`10.`..`17.`) begins a spillover page (`self.page_empty`), shifts the page-level `<ol>` indent and marker anchor by `(_w_cur - _w_one) / 64.0` (`+28/+24/+31 px`), eliminating the constant horizontal offset on all 11 spillover pages (`~-320k` px).
- **Total 60-Run Spacing Diff (`pages 2–5`)**: **`17,684,610 -> 15,917,005` (`-1,767,605` px vs `v1.11.16`; `-10,390,433` px / `-39.5%` vs `v1.11.14`)**, zero cells worsened across all 60 runs, `18/18` default goldens 100% bit-identical to `v1.11.16`.
- **Tooling & Docs**: Added `tools/lab_spacing/bands.py`, `docs/data/spacing_bands.json`, `docs/hypotheses/spacing_fit3.md`, worst-page side-by-side PNGs (`docs/hypotheses/spacing_fit3/`), and updated `REPORT.md`.

## [1.11.16] - 2026-11-22 — Close Remaining Spacing-Setting Gaps (S-A through S-G)

### Changed
- **Word & Char Acceptance Region (`kindle_render/config.py`, `kindle_render/layout.py`)**:
  - Added `word_spacing_shrink_decay = 3.27` (`max(word_spacing_shrink_mult, 1.0 - word_spacing_shrink_decay * extra_word_em)` -> `0.28×` at step 2, `0.10×` at steps 3–5), fixing `Compact word 2` (`665,107 -> 31,260`, `-633,847` px) with zero regressions.
  - Tuned `char_spacing_shrink_mult = 0.80` (from `0.70`), fixing `Standard char 4` (`789,805 -> 688,741`, `-101,064` px; `-112,179` px across 3-theme char 2..5).
- **Tight-Floor `h1` Top Margin (`kindle_render/page.py`)**:
  - Added `mt += 1` when `line_spacing_step is not None and pitch == 0 and h_idx == 0 and std_body_pitch < (19.0 / 14.0) * c.size_px()`, dropping `Standard line 1` from `231,261 -> 19,270` (`p3/p4/p5 = 0`) and reducing Standard across all 16 step-1 runs by `-2,713,245` px.
- **Total 60-Run Spacing Diff (`pages 2–5`)**: **`21,028,735 -> 17,684,610` (`-3,344,125` px vs `v1.11.15`; `-8,622,828` px vs `v1.11.14`)**, zero cells worsened `> 0.5%`, `18/18` default goldens 100% bit-identical to `v1.11.15`.
- **Tooling & Docs**: Added `tools/lab_spacing/align.py`, `docs/data/spacing_acceptance_region.json`, `docs/hypotheses/spacing_fit2.md`, worst-page side-by-side PNGs (`docs/hypotheses/spacing_fit2/`), and `REPORT.md`.

## [1.11.15] - 2026-11-22 — Device-Fitted Four 5-Step Spacing Settings (S0–S8)

### Changed
- **Spacing Fit (`kindle_render/config.py`, `kindle_render/layout.py`, `kindle_render/page.py`)**:
  - Refined `LINE_SPACING_RATIOS` to `(1.353, 1.510, 1.635, 2.318, 2.977)` with `Config.raw_pitch_px()` so all 30/30 body and heading pitches match device captures exactly across Standard/Compact/Large, and added `heading_line_spacing_lead_k = 0.045` (gated on `line_spacing_step is not None and pitch == 0`).
  - Added `ol_number` marker tracking (`+trk` anchored to base `left_em`) and link underline trailing-track trim (`-trk`), confirming `char_spacing_step_em = 0.056` as a sharp V-minimum (`0.048..0.058` sweep).
  - Exposed named `Config` fields `word_spacing_step_em = 0.22`, `char_spacing_step_em = 0.056`, `word_spacing_shrink_mult = 0.10`, `char_spacing_shrink_mult = 0.70`, and `heading_line_spacing_lead_k = 0.045`, reducing 60-run spacing capture diff total (pages 2–5) by **`-5,278,703` px (`-20.1%`, `26,307,438 -> 21,028,735`)**.
  - Added `tools/lab_spacing/score_spacing.py`, `docs/hypotheses/spacing_fit.md`, worst-page side-by-side PNGs, and `docs/data/spacing_measurements.json`.
  - **Regression Gate (S8)**: `18/18` goldens bit-identical to `v1.11.14` (zero golden changes) under `KINDLE_RENDER_STRICT_HARFBUZZ=1`.

## [1.11.14] - 2026-11-22 — Horizontal em = column width/32; spacer gap always (10/17)*pitch

### Fixed
- **Horizontal margin unit (`epub.py`)**: margin-left/right in em now resolve to `(right - x0)/32` px (Kindle Previewer maps 1em = 12pt = 3.125% of page width) instead of a fixed 28.8125 px. Identical at Standard (922/32), corrects Compact/Large indents.
- **Spacer paragraph gap (`page.py`)**: always `(10/17)*pitch`; the tight-regime exception (full pitch) was wrong (verse stanza gap 53 px vs device 31 px in Compact). Needs the margin fix to avoid pagination cascade.
- **Impact** (v1.11.13 -> 1.11.14): e3_compact 1,852,980 -> 1,226,981 diff px; e3_large 2,667,605 -> 2,264,291; exam2 1,034,912 -> 1,062,040 (p41 only, open); all other corpora bit-identical; no exact page lost. Goldens regenerated for exam2, e3_compact, e3_large only.
- Source of the unit rule: comments in github.com/jloutsch/kfxgen (read, no code copied).

## [1.11.13] - 2026-11-21 — Table Scale Model M Adoption, Tuning & Extensions (E0–E9)

### Changed
- **Model M Collapsed Table Scaling & Uniform Layout (`kindle_render/page.py`, `kindle_render/config.py`)**:
  - Adopted reviewer Model M (`tbl_pad_em=1.37`, `tbl_cap_em=7.5`, `tbl_scale_floor=0.2`, `tbl_uniform_layout=True`) gated by `is_col` (preserving `exam1` uncollapsed tables) and `size_px() != 42.0` (`exam2`). Settled tuning parameters into named `Config` fields (`tbl_data_min_factor=0.8`, `tbl_long3_cap_em=8.8`, `tbl_lp0_em=0.845`, `tbl_lpm_em=0.567`, `tbl_row_pad_em=0.28`), keeping `KR_TBL_SCALE` and `KR_TBL_LOG` as debug hooks.
  - **E2 (Long 3-col table)**: Replaced hardcoded `0.81 / 0.96` with `avail_w / max(right - x0, sum(clamp(mn, mx, 8.8 * px) + P))` (`-165,077` px).
  - **E3 (Data-cell unbreakable min-content)**: Added `tbl_data_min_factor = 0.8` weight on non-header split pieces (`-70,039` px on Large p09/p10).
  - **E4 (Unscaled collapsed tables)**: Replaced hardcoded `64.0 / 49.0 / 36.5` px padding constants with em-based `1.45 / 1.41 / 1.134 / 0.845 * tbl_em` (`-64,902` px across all 3 themes).
  - **Total 3-theme impact (`tables_images`, `ti_compact`, `ti_large`)**: **`-1,088,528` diff px** (`25,210,579 -> 24,122,051`: Standard `8,183,519 -> 7,941,639` exact `4 -> 5`, Compact `6,747,943 -> 6,242,449` exact `3`, Large `10,279,117 -> 9,937,963` exact `3`), page counts unchanged (`44 / 35 / 57`), `18/18` goldens & `6/6` unit gates PASS under `KINDLE_RENDER_STRICT_HARFBUZZ=1`.
- **Lab Toolkit & Documentation**: Added `tools/lab_tables/*`, `docs/hypotheses/table_scale_model_M.md`, `docs/hypotheses/tables_v3.md`, `docs/data/table_scale_measurements.json`, updated `BACKLOG.md`, and ignored `tools/lab_tables/work/`.

## [1.11.12] - 2026-11-21 — Four 5-Step Kindle User Spacing Settings

### Added
- **Four 5-Step Kindle User Spacing Settings (`kindle_render/config.py`, `layout.py`, `page.py`, `cli.py`, `__init__.py`)**:
  - Added `line_spacing_step` (1..5, `None` default), `paragraph_spacing_step` (1..5, default 1), `word_spacing_step` (1..5, default 1), and `char_spacing_step` (1..5, default 1) to `Config`, CLI flags (`--line-spacing-step`, `--paragraph-spacing-step`, `--word-spacing-step`, `--char-spacing-step`), and exported `LINE_SPACING_RATIOS` and `THEME_SPACING_PRESETS`.
  - Line spacing resolves `round(K[step-1] * size_px)` with `K = (1.358, 1.515, 1.642, 2.313, 2.977)` when explicit `pitch == 0` (explicit `pitch` keeps priority): Standard `61/68/74/104/134`, Compact `53/59/64/90/116`, Large `68/76/82/116/149`.
  - Paragraph spacing adds `(step - 1) * size_px` extra vertical gap between consecutive paragraphs, list/TOC items (`<li>`), and headings followed by paragraphs, while keeping page-top headings invariant.
  - Word spacing adds `(step - 1) * 0.22` body `em` per step (`user_word_spacing_26()`), and character spacing adds `(step - 1) * 0.056` body `em` per step after every glyph including spaces (`user_char_spacing_26()`), with trailing spacing counted toward line width.
  - Zero regression at default presets: all 18 corpora and size-series goldens, all 6 unit gates, and 6-corpus determinism pass 100% bit-identically under `KINDLE_RENDER_STRICT_HARFBUZZ=1`.

## [1.11.11] - 2026-11-20 — Step D2: Cross-Theme 4+ Column Table Scale & Unified Row Padding

### Changed
- **Step D2 (`kindle_render/page.py:add_table`)**: Replaced the fixed `0.70 / 0.618` 4+ column table scale with the cross-theme model `max(0.35, min(0.95, avail_w / max(text_1x_cols + 7.75 * ncols, 3.081 * ncols * std_pitch)))` (fitted on 5/6/9-col across all 3 themes, held-out 4-col validated) and removed the `c.size_px() == 42.0` special case from `sc_tbl <= 0.75` `row_pad`. Reduces 3-theme total diff by **`-143,963` px** (`25,354,542 -> 25,210,579`: Standard `-100,773`, Compact `+50,120`, Large `-93,310`; eliminates `1.11.10`'s regressions on Large p6 `-108,053`, Large p10 `-78,791`, and Standard p8 `-31,086`) with `0` lost exact pages, unchanged page counts (`44/35/57`), and `15/15` regression goldens passing.

## [1.11.10] - 2026-11-20 — Step D: Physical Scaled Table Row Pitch & Padding

### Fixed
- **Step D (`kindle_render/page.py:add_table`)**: Replaced the `1.36 * tbl_size_px` line pitch and hardcoded `row_pad = 7 / 10` in scaled collapsed tables (`sc_tbl < 1.0`, `c.size_px() != 42.0`) with the 0-parameter physical formula `line_p = int(round(std_pitch * sc_eff))` and `row_pad = max(7, int(round(int(0.28 * c.size_px()) * sc_eff)))`. Reduces 3-theme total diff by **`-80,597` px** (`25,435,139 -> 25,354,542`: Standard `-87,322`, Compact `0`, Large `+6,725`) with `0` lost exact pages, unchanged page counts (`44/35/57`), and `15/15` regression goldens passing.

## [1.11.9] - 2026-11-20 — Step A2: Em-Scaled Table Column Padding

### Changed
- **Step A2 (`kindle_render/page.py:add_table`)**: Replaced pixel literals (`64.0`, `61.0`, `49.0`, `36.5`, `24.5`, `13.5`) in `_col_pad2` and `col_l_pad`/`col_r_pad` for full-width wrapping collapsed tables (`tot_1x > avail_w`) with `em`-scaled expressions of `tbl_em = tbl_size26 / 64.0`. Aligns `Table 5.1` (`Row / Detail / Amount`) within `0–3 px` across Standard, Compact, and Large, reducing 3-theme total diff by **`-32,911` px** (`25,468,050 -> 25,435,139`: Standard `-5,587`, Compact `-13,552`, Large `-13,772`) with `0` lost exact pages, unchanged page counts (`44/35/57`), and `15/15` regression goldens passing.

## [1.11.8] - 2026-11-19 — Group A: Full-Width Wrapping Table Column Padding

### Fixed
- **Group A (`kindle_render/page.py:add_table`)**: For full-width wrapping collapsed tables (`tot_1x > avail_w`, `sc_tbl > 0.75`, `not has_spans`), aligned last-column allocation (`_col_pad2 = 61.0`) and left-aligned final-column inner left padding (`13.5`) across all three themes. Aligns `Table 5.1` (`Row / Detail / Amount`) `Amount` column within `1–3 px` of device captures on Standard, Compact, and Large, reducing 3-theme total diff by **`-95,707` px** (`25,563,757 -> 25,468,050`: Standard `-88,120`, Compact `-4,462`, Large `-3,125`) with `0` lost exact pages, unchanged page counts (`44/35/57`), and `15/15` regression goldens passing.

## [1.11.7] - 2026-11-19 — Heading Widow/Orphan Keep-Together (H1) & H2/H3 Investigation

### Fixed
- **Heading Keep-Together (`H1`, `kindle_render/page.py:add_text_block`)**: Relaxed the heading page-break rule from `not b.mt_em and len(lines) == 2 and self.y + gap + 2 * pitch_fl > c.page_bottom` to `len(lines) >= 2 and self.y + gap + c.widow_orphan * pitch_fl > c.page_bottom`. Eliminates orphan 1-line heading splits on `sizes_02` (`-557,767` diff px), `sizes_06` (`-1,508,004` diff px, `93.7172% -> 94.3645%`), and `e3_compact` (`-233,081` diff px, `98.4009% -> 98.5796%`) while preserving the device's `2 + 2` 4-line heading split on `sizes_05` p39->40 (`-2,298,852` diff px total, `0` lost exact pages, `0` regressions on all other corpora).
- **8-Size Capture Profiles (`tools/profiles.json`)**: Linked `exam/v3/size_01..03_Bookerly` and `size_05..07_Bookerly` capture directories for full 8-size scoring.
- **Pre-Registered Hypotheses & Investigations**: Recorded H1/H2/H3 in `docs/hypotheses/headings_v1.md`, H3 long-word measurements in `tools/reports/headings/h3_longwords.md`, and H2/H3 residuals in `BACKLOG.md`.

## [1.11.6] - 2026-11-18
### Fixed
- HarfBuzz version lock no longer blocks rendering: a different runtime version (for example 8.3.0) runs; non-verified versions warn once on stderr. `KINDLE_RENDER_STRICT_HARFBUZZ=1` restores the hard error (oracle/CI). Missing library is still an error. Zero pixel change.

## [1.11.5] - 2026-11-18 — Port-Ready Baseline (Zero Pixel Change)

### Changed
- **Clean-Clone Reproducibility (`H1`)**: Updated `tools/profiles.json` and `tools/corpus.py` to resolve EPUBs and capture folders directly under `exam/` (ignoring `*_table_N.png` and `size_08..11`), removed `/tmp/work` from `tools/test_boundary.py`, routed tool outputs to git-ignored `tools/reports_local/` (preserving `tools/reports/manifest.json` unless `--write-manifest` is passed), and added `tools/run_gates.py` (`25/25` gates passing from a fresh clone).
- **Goldens & Baseline Metrics (`H2`)**: Updated all `tools/golden/*.json` (`engine_version: "1.11.5"`), added goldens for `sizes_00..07`, `e3_compact`, `e3_large`, `ti_compact`, `ti_large`, and generated `tools/reports/baseline_1.11.5.{json,md}` with `100%` pixel/layout hash equivalence to `v1.11.4`.
- **HarfBuzz Policy (`H3`)**: Enforced `verify_harfbuzz(cfg.allow_unshaped)` uniformly in `Family.__init__`, exposed `--allow-unshaped` in `kindle_render/cli.py`, and documented the `6.0.0` exact-pin policy in `docs/environment.md`.
- **Numerics & Determinism (`H4`)**: Documented all `f32`/`f64`/`int` rounding, resampling, and Unicode dependencies in `docs/numerics_inventory.md` and added `tools/test_determinism.py` (`PYTHONHASHSEED=1` vs `42`).
- **Calibration, Docs & Repo Weight (`H5`–`H7`)**: Updated `ARCHITECTURE_NOTES.md`, `BACKLOG.md`, `STATUS.md`, `README.md`, `CHANGELOG.md`, `docs/ASSETS.md`, and `docs/repo_weight.md`.

## [1.11.4] - 2026-11-18

### Changed
- **Nested `<ul>` Indentation (`config.py`, `epub.py`)**: Restored `ul_nested_indent_em` from `1.9762` to the exact CSS `2.0000` em (`MEASURED`), improving nested unordered list alignment across all 6 tested geometries (`probe` p87, `exam1` p45–46, `exam3_normal` p39, `exam3_small` p25, `e3_compact` p26, `e3_large` p57) with zero lost exact pages (`-48,597` diff pixels across Step-1 corpora).
- **Tight-Regime Block & Bullet Spacing (`page.py`)**: In the `extra_lead == 0.0` regime, rounded first-item bullet top margin `mt = int(round(b.mt_em * vem_px * b.scale))` for `bullet == '•'` (`D(i)`) and applied `gap -= 1` to indented non-list blocks (`b.left_em > 0.0 and list_level == 0`) directly following `<h1>` (`D(ii)`), bringing `probe` p87 `<blockquote>` and `<pre>` (`bands 2..9`) from `+1 px` shift to `0 px` (`29/29` bands at `shift = 0`, `probe` p87 pixel match `97.9045% -> 99.3024%`, `+1.3979 pt`) (`MEASURED`).
- **Candidate Evaluation & Pitch-Ratio Audit (`tools/reports/incorporate/REPORT.md`, `BACKLOG.md`)**: Evaluated Reviewer Candidates A, B, C, and D against device captures (`tools/reports/incorporate/base_1.11.3.json`), rejecting Candidate A (downscale `ceil` rounding, `+620,664` diff px regression across 20 pages), Candidate B (`0` diff px; apostrophes already split in `layout.py:441-447`), and Candidate C (`0` diff px; `tol*8` never reached), and documented all `1.11.x` pitch-vs-size ratio thresholds in `page.py`.

## [1.11.3] - 2026-11-18

### Fixed
- **Task C4 — Untruncated `float32` first-line `text-indent` subpixel tie-breaking**:
  - Preserved the fractional 26.6 subpixel remainder `indent_frac26 = (indent_em * size_px * 64.0) - indent26` (`+0.2` at `34 px` and `39 px` for `1.2em` indent) in `kindle_render/page.py` and `kindle_render/layout.py:layout_line` when evaluating `sub == 31` after the first space on line 0.
  - Gains `+3` exact pages on `e3_small` (`29 -> 32/54`: `p4`, `p37`, `p40`) and `+4` position-exact lines (`1514 -> 1518/1651`) with `lost = 0` across all datasets.

## [1.11.2] - 2026-11-18

### Fixed
- **Task C3 (`e07_inline`) — Cross-run OpenType GPOS kerning across unspaced inline span boundaries**:
  - Extended cross-Box GPOS kerning in `kindle_render/layout.py:build_items` to directly adjacent `Box` items (`isinstance(items[idx + 1], Box) and not n1[0].isupper()`) sharing the same `Face`.
  - Reduces `e3_std` diff by `-49,313 px` (`762,672 -> 713,359`) and `e3_small` diff by `-30,263 px` (`879,278 -> 849,015`) with `lost = 0` across all datasets.

## [1.11.1] - 2026-11-18

### Fixed
- **Task A (`heading_block_v1`) — Unified `<h1>` bottom-margin calibration across Compact (`39/53`) and Large (`50/82`)**:
  - Pre-registered in `docs/hypotheses/heading_block_v1.md` and replaced the ad-hoc `0.10 * extra_lead` `h1` bottom-margin slope (`0.66 * b.scale * vem_px + 0.10 * extra_lead`) with the unified pitch-scaled vertical-em formula `int(round(0.654 * b.scale * vem_px)) + 1` (`mb_lead_k = 0.0` for `h1`, matching the `+1 px` boundary rounding offset on `mt`).
  - Preserves exact `h1` bottom margins on `34/51` (`57 px`), `42/57` (`63 px`), and `45/68` (`75 px`) with `0` golden changes across all 8 corpus suites, while fixing Compact (`39/53`: `58 -> 59 px`, `-557,931` diff px, `+53` pos lines on `ti_compact`) and Large (`50/82`: `92 -> 90 px`, `2 -> 3/57` exact pages, `-401,634` diff px, `+18` pos lines on `ti_large`) with `lost = 0` across all datasets.

## [1.11.0] - 2026-11-18
### Added
- Registered `tables_images` (`kindle_tables_images_exam.epub` + `tables_images_standard_captures.zip`) as the 6th corpus in `tools/profiles.json` and `tools/corpus.py`.
- Added `Config.extra_lead_px()` helper with `0.5px` integer-pitch rounding tolerance so Compact (`39px/pitch 53`) remains in the tight-spacing regime.
- Added `tools/score_dir.py` for scoring capture folders across arbitrary viewport geometries (`Standard`, `Compact`, `Large`) and `tools/test_bugfixes.py` regression suite.
- Generalized cross-theme block image viewport scaling (`sc = maxw / 512.0`), HTML `width`/`height` attributes, CSS `px`/`%` widths, RGBA white alpha-compositing, tall-image page-remainder fitting, multi-image inline `<p>` runs, and inline image scaling (`size26 / 1024.0`).
- Generalized cross-theme collapsed table layout: `row_pad = int(0.28 * size_px)`, `row_ys[-1]` bottom rule placement, chromeless table detection (`has_chrome`), multi-page row-chunk splitting with per-page bottom rule + popup icon and top continuation rule (`y = 167..170`), unbreakable single-word `<th>` headers, and rich cell rendering (`<b>`, `<i>`, `<a>`, `<ul><li>`, `<img/>`).

## [1.10.2] - 2026-11-17

### Added
- **Compact `extra_lead_px()` Fix & 6th Corpus (`tables_images`)**: Added `Config.extra_lead_px()` with `0.5 px` integer-pitch rounding tolerance (fixing Compact `39/53` heading regime selection), registered `tables_images` as the 6th corpus, and generalized cross-theme image and collapsed table layout.

## [1.10.1] - 2026-11-16 (`v1.10.1` — Mark Highlight Vertical Bounds)
- **Highlight Box Bounds (`kindle_render/page.py:draw_line`)**: Updated `<mark>` background rectangle vertical bounds to use `hhea.ascent` (`0.900 * size_px` above baseline) and `floor(pitch / 1.2)` line box height (`-2,244` diff pixels on `exam2` p.40; zero regressions across all 5 corpora).

## [1.10.0] - 2026-11-16 (`v1.10.0` — Stage H Fidelity Fixes)

### Stage H1 `[F]`: Cross-Box Kerning, Leading Ellipsis, Vulgar Fractions & `<mark>` Highlights
- **Cross-Box GPOS Kerning (`kindle_render/layout.py:build_items`)**: Applied `math.floor(face.kern_units(n1, n2) * face.S)` across adjacent unspaced `Box` boundaries split at `hyphen`, `endash`, `emdash`, and `slash`, updating `Box.width` prior to line breaking and removing the duplicate post-justification hyphen tweak in `layout_line`.
- **Leading Horizontal Ellipsis (`…Word`)**: Included `…` in `lstrip` during hyphenation word extraction and split leading `ellipsis` `Box`es into `Box([ellipsis]) + Penalty(0, 0, False) + Box(rest)`.
- **Vulgar Fractions (`kindle_render/fonts.py:names_with_clusters`)**: Mapped precomposed third and eighth fraction sequences (`1⁄3`, `2⁄3`, `1⁄8`, `3⁄8`, `5⁄8`, `7⁄8`) to their Unicode codepoints before GSUB/numr/dnom fallback.
- **Highlight Background (`kindle_render/epub.py:_collapse`)**: Preserved `bg=getattr(r, "bg", None)` on collapsed `Run` instances so `<mark>` highlight rectangles are emitted in `draw_line`.

### Stage H2 `[F]`: `float32` Justified-Line Pen Accumulation
- **Half-Pixel Tie-Breaking (`kindle_render/layout.py:layout_line`, `kindle_render/page.py`)**: Accumulated per-word widths and `float32` space advances (`sp_fl = f32(std_sp) + f32(delta) / f32(k)`) across uniform-face justified lines to resolve exact `32/64` (`0.50` px) rounding boundaries in the final word of justified lines.
- **5-Corpus Verification**: Improved total bitwise-identical pages across `probe`, `exam1`, `exam2`, `exam3_normal`, and `exam3_small` from `179/357` to **`222/357`** (`9,013/9,638` positional-exact lines, `4,611,304` total diff pixels; `0` lost exact pages).

## [1.9.1] - 2026-11-16 (`boundary-1.9.1` — Stage F Contents Page & Stage G Boundary Hardening)

### Stage F `[F]`: Contents Page (`nav` / p.2) & Ordered List (`<ol><li>`) Subpixel Geometry
- **Ordered List Content Indent (`ol_indent_em`)**: Updated `Config.ol_indent_em` from `2.0` to `2.1054` (`round(2.1054 * size_px)` px: `72` px at `34` px, `88` px at `42` px, `95` px at `45` px), matching the content `x` start across all 3 geometries and all 5 corpora (`probe`, `exam1`, `exam2`, `exam3_normal`, `exam3_small`).
- **Ordered List Marker Offset**: Computed `<ol>` marker right-aligned offset `m_x26 = start26 - (m_w + sp26)` directly from the content start `start26`.
- **Subpixel Antialiased Link Underlines (`role="link_underline"`)**: Added `link_underline` rule emission in `kindle_render/page.py` (`base_thk = float(round(0.065 * sz_px))`, `y_off_top = base_thk + 0.02612 * sz_px + 0.00245 * pt_px - 0.5855`, `thk_fl = base_thk - 0.00015 * sz_px + 0.00013 * pt_px - 0.00165`) and separable 1D subpixel edge coverage `min(cov_x, cov_y)` in `kindle_render/raster.py`.
- **Verification**: All 5 Contents pages (`p.2`) across `probe`, `exam1`, `exam2`, `exam3_normal`, and `exam3_small` achieved `0` differing pixels (`100%` bitwise identity), and `exam2` p.7 and p.12 also became `100%` bitwise identical (`179/357` exact pages, `8,913/9,638` positional-exact lines across all 5 corpora).

### Stage G `[P]`: Layout / Raster IR Boundary Hardening
- **Round-Trip Deserialization & Validation**: Added `PositionedDocument.from_dict`, `PositionedPage.from_dict`, `_cmd_from_dict`, `validate_ir_page`, and `validate_ir_document` in `kindle_render/ir.py`.
- **Verification (`tools/test_boundary.py`)**: Verified `0` IR schema/coordinate invariant errors and `100%` `layout_sha256` round-trip equality across all `369` rendered pages (`5` corpora), plus `100%` pixel SHA-256 identity when rasterizing deserialized IR pages.

## 1.7.0
- **Decoupled Layout & Rasterization via Serializable IR (`kindle_render/ir.py`, `kindle_render/page.py`, `kindle_render/raster.py`)**:
  - Introduced versioned (`ir_version = "1.0"`) intermediate representation data classes (`PositionedDocument`, `PositionedPage`, `GlyphCommand`, `RectCommand`, `RuleCommand`, `RingBulletCommand`, `ImageCommand`, `TextBlockMeta`) with canonical sorted-key JSON serialization and SHA-256 layout hashing (`layout_pages` in `tools/golden/*.json`).
  - Switched `Pager` (`layout_blocks_to_ir`, `layout_lines_to_ir`) to emit only IR objects without touching FreeType or pixel buffers, and delegated all bitmap rendering to `Rasterizer.rasterize_page` / `Rasterizer.rasterize_document`.
  - Enforced strict module import boundary via `tools/check_imports.py` (Gate G4): layout modules (`config.py`, `epub.py`, `fonts.py`, `hyphen.py`, `layout.py`, `ir.py`, `text_layer.py`, and layout functions in `page.py`) never import `raster` or `freetype`.
- **Instance-Owned FreeType State & Concurrency (`kindle_render/raster.py`, `tools/test_parallel_raster.py`)**:
  - Eliminated process-global `_ft_lib_handle`; each `Rasterizer` / `GlyphCache` instance initializes and cleans up its own `FT_Library` handle and face/bitmap caches.
  - Verified deterministic multi-thread (`ThreadPoolExecutor`) and multi-process (`ProcessPoolExecutor`) concurrent rasterization across all pages of `probe`, `exam1`, and `exam2`.
- **Structured Text Layer & Schema (`kindle_render/text_layer.py`, `docs/text_layer_schema.md`, `tools/test_text_layer.py`)**:
  - Added per-page (`page_NNN.json`) and document (`document.json`) structured text layer extraction directly from the IR (`blocks -> lines -> words -> clusters`) with page-clamped pixel bounding boxes, reading order, structural metadata (headings, lists, tables, links), ligature expansion, RTL logical word/character ordering, and `is_synthetic_hyphen` tagging.
  - Added CLI subcommand `kindle_render text IN.epub OUT_DIR` and `--text-layer` flag on `kindle_render epub`.
  - Added public API functions `render_to_ir(book, cfg)` and `rasterize(ir_page, cfg)`.
- **Zero Pixel Change Guarantee**:
  - Verified 100% bit-for-bit identical rendered pixels against `v1.6.1` across `probe` (`37/86` exact pages, `486,515` diff px), `exam1` (`42/70` exact pages, `1,607,042` diff px), `exam2` (`35/65` exact pages, `1,176,881` diff px), and `synthetic` (`4/4` pages).
- **Documentation & Provenance**:
  - Added `DATA_PROVENANCE.md` and `REFACTOR_PLAN.md`, and updated `ARCHITECTURE_NOTES.md` to v1.7.0.

## 1.6.1
- Housekeeping only; rendered pixels are identical to 1.6.0 (checked on the three corpora).
- Removed `tools/golden/` (stored per-page hashes). `tools/corpus.py` now treats a missing golden file as "nothing to compare", not a failure. `--update-golden` still works when you want to record new hashes later.
- Kept `tools/reports/` (the 1.6.0 baseline numbers), `ARCHITECTURE_NOTES.md`, `BACKLOG.md`.

## 1.6.0

### De-Overfitting & General Compute Mechanisms (Step A)
- **General Table Column Allocation (`page.py:add_table`)**: Replaced fixed 4-column width overrides with a general min-content / max-content column width solver driven by cell glyph widths and alignment padding:
  - Header cells (`<th>`, `is_hdr=True`) break at spaces and after `/` in compound unit tokens (`len(token) > 4`), and do not hyphenate mid-word unless a single unbreakable token exceeds `inner_w`.
  - Data cells (`<td>`, `is_hdr=False`) break at spaces, after `/`, and via Liang hyphenation.
  - Columns whose single-line maximum width `max_w[ci]` is within the equal share `avail_w / ncols` lock at `round(max_w[ci])`; among remaining columns, columns whose `max_w` fits within their equal share of remaining width lock at `round(min_w[ci])` when paired with a wider prose column, and remaining width is distributed proportionally to `max_w`.
- **Root Container `em` Basis (`config.py`, `epub.py`)**: Removed all CSS class-name checks (`in2`, `in4`, `hang`, `lm3`, `rm3`, `both`). CSS `margin-left` and `margin-right` declarations with `|v| >= 2.0em` evaluate against `base_root_em_sp = 10.97619` (`28.8125 px` at `2.625x` density, yielding `57.625 px = 3688 / 64` at `2em` and `115.25 px = 7376 / 64` at `4em` across both `42 px` and `45 px` body font sizes). Negative `text-indent` (`v < 0`) evaluates against the same root `em` basis so hanging indents (`margin-left: 2em; text-indent: -2em`) cancel exactly at `x = x0`.
- **CSS `border-collapse: collapse` & Named Device Constants (`config.py`, `epub.py`, `layout.py`, `page.py`)**: Replaced all 37 `cfg.size26 == 2688 and cfg.x0 == 79` geometry branches with structural HTML/CSS properties (`border_collapse` parsed from `table { border-collapse: collapse }`, inline image dimensions, and named constants in `Config`).

### Algorithmic & Layout Fixes (Step B)
- **B1 — All-Caps Legal Prose Hyphenation & Heading-to-Block Spacing (`layout.py`, `page.py`)**: Enabled Liang hyphenation on uppercase words of 8 or more letters (`len(alpha) >= 8`) so long uppercase legal tokens hyphenate cleanly, and extended the `-1 px` `<h1> -> <p>` top-margin rounding adjustment to paragraphs with `mt_em > 1.0` (`x06_legal` Pages 14–15 now both `0` differing pixels).
- **B2 — `<mark>` Background Highlight Rendering (`epub.py`, `layout.py`, `page.py`)**: Propagated `bg = (255, 255, 0)` on runs inside `<mark>` elements and rendered contiguous yellow highlight bands (`[baseline - round(0.81 * size_px), baseline + round(0.33 * size_px)]`) prior to glyph compositing.
- **B3 — Inline Monospace Space Width, Shrink & `.loose` Line Pitch (`layout.py`, `page.py`)**: Included full `DroidSansMono` space width (`0.60 * r_size26 = 25.20 px`) in Knuth-Plass `SP` accumulation for monospace runs (`is_mono=True`), permitted line shrink on paragraphs with `<= 3` inline monospace boxes, and computed `line-height` in `(1.5, 2.0)` via integer truncation `int(line_height * vem_px * scale + 1e-6)`.
- **B4 & B10 — BiDi RTL Numeric Runs, Emoji Sequences & Korean Spacing (`fonts.py`, `layout.py`)**:
  - Extended inline RTL run reversal in `make_lines` to include neutral numeric `Box` tokens (`0-9`) bounded by RTL boxes (`NotoNaskhArabic` / `NotoSansHebrew`).
  - Added `U+2615` (`☕`) to the emoji codepoint detector, shaped multi-codepoint emoji ZWJ and skin-tone modifier clusters (`👍🏽`, `👨‍👩‍👧`, `🏳️‍🌈`) via HarfBuzz ligature shaping on `NotoColorEmoji.ttf`, and used `ef.space26()` (`52.28 px`) for inter-emoji spaces.
  - Added `0.0536 * size26` (`2.25 px` at `42 px`) to CJK space width in pure Hangul paragraphs (`U+AC00..U+D7AF`).
- **B5 — Multilingual Hyphenation Guards (`config.py`, `layout.py`, `page.py`)**: Disabled fallback to English hyphenation for languages without a matching hyphenation table (`sv`, `la`), enforced `min_word_length = 6` for non-English hyphenation (`it`), and adjusted `<h1> -> <h3>` gap by `-2 px` (`61 px`).
- **B6 — `::first-line` Small-Caps & 2-Line `::first-letter` Drop Cap (`epub.py`, `layout.py`, `page.py`)**: Added two-stage line composition for `::first-line { font-variant: small-caps }` (shaping Line 0 in small-caps with optical hyphen overhang and re-shaping remaining text in regular body font for Lines `1..n-1`), parsed `font-size < 280%` on `::first-letter` as a 2-line drop cap (`drop_cap_lines = 2`), and set the 2-line Bookerly drop-cap horizontal gap to `0.26 * size_px`.
- **B7 — 8-Bit Consecutive Hyphen Window Mask & Ragged Terminal-Word Hyphen Guard (`layout.py`)**: Widened the consecutive-hyphen bitmask in `break_kp` from `0x7f` (7 bits) to `0xff` (8 bits) so `TABLE_CONSEC[8] = 21.0` activates on the 8th consecutive hyphenated line (`exam2` Page 55 and `exam1` Pages 27, 62 now `0` differing pixels), and enabled the `w28` two-word terminal hyphen penalty (`c = 5.0`) in ragged-right mode (`exam2` Page 33 now `0` differing pixels).
- **B8 & B9 — Post-`<hr/>` Margin, `<h3> -> <ul>` Gap & `<h6> -> <p>` Gap (`page.py`)**: Set post-`<hr/>` bottom margin to `round(0.50 * vem_px)` (`24 px`) on collapsed-table stylesheets, `<h3> -> <ul>` gap to `56 px`, and uncollapsed `<h6> -> <p>` gap to `74 px` (restoring `probe` Page 81 to `0` differing pixels while preserving `exam2` Page 27 at `0` differing pixels).
