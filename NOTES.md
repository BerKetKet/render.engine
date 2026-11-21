# Development Notes — Kindle Render Engine (Engine-Only Branch)

## Current State
- **Working Directory**: `/home/bgg/projects/render.engine`
- **Module**: `kindle_render` v1.11.13
- **Git Branch**: `engine`
- **Latest Tag**: `v1.11.13`
- **Python Runtime**: Python 3.13, FreeType 2.13+, HarfBuzz (Docker lock: 6.0.0, host CachyOS: 15.1.0)

## Scope
- This branch contains only the clean `kindle_render` engine source, verification tools, reports, and documentation.
- The heavy Kindle hardware screen captures and EPUB corpus (`exam/` directory, ~404 MB) are tracked exclusively on the `main` branch.

## What is Verified
1. **Pipeline & Architectural Health**:
   - G4 import graph integrity verified clean via `python3 tools/check_imports.py` (0 errors).
   - Independent instance-owned FreeType rasterizer state design (`ir.py`, `raster.py`).
   - Round-trip IR deserialization and schema/coordinate invariant validation (`tools/test_boundary.py`, 0 validation errors, 369/369 pages `layout_sha256` round-trip equality).
   - Bug fix suite clean: `python3 tools/test_bugfixes.py` passes (`pitch_34=51 tall_table_pages=3 scaled_run_pages=2 ALL PASSED`).
   - Clean git working tree; no tracked secrets, credentials, or unscrubbed logs.
2. **Milestone Progress (Stages A through H / v1.10.2)**:
   - **Stage A (`1.8.0-rc1`)**: Version lock & loud failure for HarfBuzz, baseline goldens for `exam3_normal` & `exam3_small`, unaligned pair filtering across 5 corpora (`tools/rhythm.py`).
   - **Stage B**: Read-only Kindle layout hypothesis registry (`docs/hypotheses/kindle_formulae_v0.md`), reading theme presets (`docs/hypotheses/kindle_themes.md`), and evaluators (`tools/hypotheses/evaluate.py`).
   - **Stage C**: Cross-geometry vertical rhythm normalization (`eff_body_pitch`, exact heading margin multipliers, spacer advances, horizontal `em`/`rem` basis).
   - **Stage D**: Page-break rules for list items, uncollapsed tables, and horizontal rules (`add_hr`).
   - **Stage E**: Forced `<br/>` segment line breaking in `break_kp` achieving 100% bitwise matching on key ragged pages (`exam3_normal` p.48-49, `exam3_small` p.31), plus full last-glyph rounding census.
   - **Stage F (`boundary-1.9.1`)**: Measured `<ol><li>` horizontal indent (`ol_indent_em = 2.1054`) and Skia subpixel link underline geometry; achieved 100% bitwise identity on all 5 Contents pages (`p.2`).
   - **Stage G (`boundary-1.9.1`)**: IR deserialization and coordinate validation (`ir.py`, `tools/test_boundary.py`).
   - **Stage H (`v1.10.0` / `round1-1.10.0`)**: Preserved `bg` in `epub.py`, fractions in `fonts.py`, ellipsis splitting, cross-box GPOS kerning, and `float32` justified-line last-word pen accumulation (222/357 exact pages).
   - **v1.10.1 (`v1.10.1`)**: Refined `<mark>` highlight box bounds using Bookerly `hhea.ascent` (0.900em) and `floor(pitch/1.2)`.
   - **v1.10.2 (`v1.10.2`)**: Tall table splitting across pages without overflowing `page_bottom`, dynamic line-pitch room check in `page.py`, `pitch_px()` half-up rounding, and general `_skia_bilerp_rgb` scaling.
   - **v1.11.0 (`v1.11.0`)**: Registered `tables_images` as the 6th corpus in `tools/profiles.json` and `tools/corpus.py`, added `Config.extra_lead_px()` tolerance helper, `tools/score_dir.py` cross-viewport scoring harness, generalized cross-theme block and inline image viewport scaling, and generalized cross-theme collapsed and chromeless multi-page table layout with rich cell content rendering.
   - **v1.11.3 (`v1.11.3`)**: Integrated releases 1.11.1 through 1.11.3 from `kindle_render_1.11.3.zip`:
     - **v1.11.1 (Task A)**: Unified `<h1>` bottom-margin calibration across Compact (`39/53`) and Large (`50/82`) via pitch-scaled vertical-em formula (`docs/hypotheses/heading_block_v1.md`), eliminating residual offsets on Compact (`58 -> 59 px`) and Large (`92 -> 90 px`).
     - **v1.11.2 (Task C3)**: Extended cross-Box OpenType GPOS kerning in `build_items` across unspaced inline span boundaries (`<u>`, `<s>`, `<span>`) sharing the same `Face` (`e07_inline`).
     - **v1.11.3 (Task C4)**: Untruncated `float32` first-line `text-indent` subpixel remainder (`indent_frac26 = (indent_em * size_px * 64.0) - indent26`) in `layout_line` for `sub == 31` tie-breaking (`+3` exact pages on `exam3_small`).
     - Added analysis tools & diagnostic documents: `tools/score_all.py`, `tools/fit_geometry.py`, `tools/block_residuals.py`, `tools/ab_diff.py`, `docs/audit_v1_11_0.md`, `docs/diagnosis_task_c.md`, `docs/hypotheses/unproven_v1_11_0.md`, and crops.
   - **v1.11.4 (`v1.11.4`)**: Integrated release 1.11.4 from `kindle_render_v1.11.4.zip`:
     - Restored `ul_nested_indent_em` from `1.9762` to CSS standard `2.0000` em (`config.py`, `epub.py`), improving nested unordered list alignment across 6 geometries with zero lost exact pages.
     - Tight-regime block and bullet spacing in `page.py`: rounded first-item bullet top margin `mt = int(round(b.mt_em * vem_px * b.scale))` for `bullet == '•'` and applied `gap -= 1` to indented non-list blocks (`b.left_em > 0.0 and list_level == 0`) following `<h1>`.
     - Evaluated candidate proposals A, B, C, D against device captures in `tools/reports/incorporate/REPORT.md`, incorporated Candidate D, and updated golden files for `probe`, `exam1`, `exam3_normal`, and `exam3_small`.

   - **v1.11.5 (`v1.11.5`)**: Integrated release 1.11.5 from `kindle_render_v1.11.5.zip` (Port-Ready Baseline):
     - Clean-clone reproducibility (`H1`): Updated `tools/profiles.json` and `tools/corpus.py` to resolve EPUBs and captures directly under `exam/`, routed tool outputs to `tools/reports_local/`, added `tools/run_gates.py`.
     - Goldens & baseline metrics (`H2`): Updated all goldens to `engine_version: "1.11.5"`, added goldens for `sizes_00..07`, `e3_compact`, `e3_large`, `ti_compact`, `ti_large`, and baseline hash equivalence reports (`baseline_1.11.5.json`, `baseline_1.11.5.md`).
     - HarfBuzz policy (`H3`): Enforced `verify_harfbuzz(cfg.allow_unshaped)` in `Family.__init__` with `--allow-unshaped` in `kindle_render/cli.py` and exact-pin policy documentation in `docs/environment.md`.
     - Added numerics inventory (`docs/numerics_inventory.md`), determinism tests (`tools/test_determinism.py`), and asset/weight documentation (`docs/ASSETS.md`, `docs/repo_weight.md`).
   - **v1.11.6 (`v1.11.6`)**: Integrated `overlay_hb_fix.zip` (HarfBuzz Non-Blocking Policy) and `overlay_tables_v1.11.6.zip` (Table & Image Split Refinements):
     - HarfBuzz version mismatch no longer blocks rendering; non-pinned versions (e.g., 8.3.0, 15.1.0) run with a one-time stderr warning instead of throwing `RuntimeError`.
     - Strict mode preserved for CI/oracle via `KINDLE_RENDER_STRICT_HARFBUZZ=1`.
     - Added mid-row table splitting at line level respecting widow/orphan=2 in `page.py`.
     - Added dashed split rules (11/5 centered phase, 3px AA) to `RuleCommand` in `ir.py`, `raster.py`, and `page.py`.
     - Float-dimension image remainder fit with `maxw != 922` guard retained for `exam1` p49.
     - Reduced 3-theme tables/images diff by `-64,032` pixels (`25,627,789 -> 25,563,757`). All golden suites pass.
   - **v1.11.7 (`v1.11.7`)**: Integrated `overlay_h1.zip` (Heading Keep-Together & H1/H2/H3 Investigation):
     - Relaxed heading page-break keep-together rule in `kindle_render/page.py:add_text_block` from `not b.mt_em and len(lines) == 2 and self.y + gap + 2 * pitch_fl > c.page_bottom` to `len(lines) >= 2 and self.y + gap + c.widow_orphan * pitch_fl > c.page_bottom`.
     - Eliminates orphan 1-line heading splits on `sizes_02` (`-557,767` diff px), `sizes_06` (`-1,508,004` diff px, `93.7172% -> 94.3645%`), and `e3_compact` (`-233,081` diff px, `98.4009% -> 98.5796%`), with `0` lost exact pages and `0` regressions across all other corpora (`-2,298,852` diff px total).
     - Linked `size_01..03` and `size_05..07` capture directories in `tools/profiles.json` for full 8-size Bookerly scoring.
     - Documented pre-registered hypotheses in `docs/hypotheses/headings_v1.md`, H3 long-word measurements in `tools/reports/headings/h3_longwords.md`, and H2/H3 wrap residuals in `BACKLOG.md`.
     - Updated goldens for `e3_compact.json`, `sizes_02.json`, and `sizes_06.json`.
   - **v1.11.8 (`v1.11.8`)**: Integrated `overlay_tables_A.zip` (Group A: Full-Width Wrapping Table Column Padding):
     - In `kindle_render/page.py:add_table`: for full-width wrapping collapsed tables (`tot_1x > avail_w`), aligned last-column allocation (`_col_pad2 = 61.0`) and left-aligned final-column inner left padding (`13.5`) across all three themes.
     - Aligns `Table 5.1` (`Row / Detail / Amount`) `Amount` column within `1–3 px` of device captures on Standard, Compact, and Large.
     - Reduces 3-theme total diff by **`-95,707` px** (`25,563,757 -> 25,468,050`: Standard `-88,120`, Compact `-4,462`, Large `-3,125`) with `0` lost exact pages, unchanged page counts (`44/35/57`), and `15/15` regression goldens passing.
     - Documented pre-registered hypotheses in `docs/hypotheses/tables_v2.md`.
     - Updated goldens for `tables_images.json`, `ti_compact.json`, and `ti_large.json`.
   - **v1.11.9 (`v1.11.9`)**: Integrated `1.11.9_overlay_tables_A2.zip` (Step A2: Em-Scaled Table Column Padding):
     - In `kindle_render/page.py:add_table`: replaced hardcoded pixel literals (`64.0`, `61.0`, `49.0`, `36.5`, `24.5`, `13.5`) in `_col_pad2` and `col_l_pad`/`col_r_pad` for full-width wrapping collapsed tables (`tot_1x > avail_w`) with `em`-scaled expressions of `tbl_em = tbl_size26 / 64.0`.
     - Dynamically scales column padding with table font size, aligning `Table 5.1` (`Row / Detail / Amount`) within `0–3 px` of device captures across Standard, Compact, and Large.
     - Reduces 3-theme total diff by **`-32,911` px** (`25,468,050 -> 25,435,139`: Standard `-5,587`, Compact `-13,552`, Large `-13,772`) with `0` lost exact pages, unchanged page counts (`44/35/57`), and `15/15` regression goldens passing.
     - Documented Step A2 hypotheses and measured extents in `docs/hypotheses/tables_v2.md`.
     - Updated goldens for `tables_images.json`, `ti_compact.json`, and `ti_large.json`.
   - **v1.11.10 (`v1.11.10`)**: Integrated `1.11.10_overlay_tables_D.zip` (Step D: Physical Scaled Table Row Pitch & Padding):
     - In `kindle_render/page.py:add_table`: replaced artificial `1.36 * tbl_size_px` line pitch and hardcoded `row_pad = 7 / 10` for scaled collapsed tables (`sc_tbl < 1.0`, `c.size_px() != 42.0`) with the 0-parameter physical formula `line_p = int(round(std_pitch * sc_eff))` and `row_pad = max(7, int(round(int(0.28 * c.size_px()) * sc_eff)))`.
     - Reduces 3-theme total diff by **`-80,597` px** (`25,435,139 -> 25,354,542`: Standard `-87,322`, Compact `0`, Large `+6,725`) with `0` lost exact pages, unchanged page counts (`44/35/57`), and `15/15` regression goldens passing.
     - Documented Step B (reverted) and Step D hypotheses and measurements in `docs/hypotheses/tables_v2.md`.
     - Updated goldens for `tables_images.json` and `ti_large.json`.
   - **v1.11.11 (`v1.11.11`)**: Integrated `1.11.11_overlay_tables_D2.zip` (Step D2: Cross-Theme 4+ Column Table Scale & Unified Row Padding):
     - In `kindle_render/page.py:add_table`: replaced fixed 4+ column table scale with cross-theme model `max(0.35, min(0.95, avail_w / max(text_1x_cols + 7.75 * ncols, 3.081 * ncols * std_pitch)))` for `c.size_px() != 42.0`, and unified `row_pad = max(7, int(int(0.28 * c.size_px()) * sc_eff)) if is_col else 7`.
     - Reduces 3-theme total diff by **`-143,963` px** (`25,354,542 -> 25,210,579`: Standard `-100,773`, Compact `+50,120`, Large `-93,310`) with `0` lost exact pages, unchanged page counts (`44/35/57`), and `15/15` regression goldens passing.
     - Documented Step D2 hypotheses and measurements in `docs/hypotheses/tables_v2.md`.
     - Updated goldens for `tables_images.json`, `ti_compact.json`, and `ti_large.json`.
   - **v1.11.12 (`v1.11.12`)**: Integrated `1.11.12_overlay_spacing.zip` (Four 5-Step Kindle User Spacing Settings):
     - Added `line_spacing_step` (1..5), `paragraph_spacing_step` (1..5), `word_spacing_step` (1..5), and `char_spacing_step` (1..5) to `Config` and CLI options.
     - Line spacing resolves `round(K[step-1] * size_px)` with `K = (1.358, 1.515, 1.642, 2.313, 2.977)` when explicit pitch is 0.
     - Paragraph spacing adds `(step - 1) * size_px` extra vertical gap between paragraphs, lists, and TOC items while keeping page-top invariant.
     - Word spacing adds `(step - 1) * 0.22` body `em` per step (`user_word_spacing_26()`), and character spacing adds `(step - 1) * 0.056` body `em` per step after every glyph (`user_char_spacing_26()`).
     - Zero regressions on default presets: all 18 corpora/sizes goldens and unit tests pass bit-identically.
   - **v1.11.13 (`v1.11.13`)**: Integrated `1.11.13_overlay_tables_M.zip` (Table Scale Model M Adoption, Tuning & Extensions):
     - Adopted Model M collapsed table scaling and uniform layout in `kindle_render/page.py` and `config.py` (`tbl_pad_em=1.37`, `tbl_cap_em=7.5`, `tbl_scale_floor=0.2`, `tbl_uniform_layout=True`) gated by `is_col` and `size_px() != 42.0`.
     - Integrated E2 (long 3-col table), E3 (data-cell unbreakable min-content with factor 0.8), and E4 (unscaled collapsed tables with em-based paddings).
     - Reduces 3-theme total diff by **`-1,088,528` px** (`25,210,579 -> 24,122,051`: Standard `-241,880`, Compact `-505,494`, Large `-341,154`, exact pages `10 -> 11`) with unchanged page counts (`44/35/57`).
     - Added lab tooling in `tools/lab_tables/`, measurement data in `docs/data/table_scale_measurements.json`, and documentation in `docs/hypotheses/table_scale_model_M.md` and `docs/hypotheses/tables_v3.md`.
     - Updated goldens for `tables_images.json`, `ti_compact.json`, and `ti_large.json`.

## What is Broken / Open Issues
- **HarfBuzz Host vs Lock**: Runtime warning emitted on host CachyOS (HarfBuzz `15.1.0`); strict mode disabled by default per v1.11.6 policy.
- **Corpus Fixtures**: Corpus EPUBs and captures reside on the `main` branch.
- **Backlog Items**: Remaining items (`ul_indent_em`, `cover` p.1, `dl/dt/dd`, complex scripts) tracked in `BACKLOG.md`.

## Next Steps
- Evaluate against held-out `exam4` when available.
- Track incoming updates or porting tasks for Rust implementation.
