# Development Notes — Kindle Render Engine

## Current State
- **Working Directory**: `/home/bgg/projects/render.engine`
- **Module**: `kindle_render` v1.10.2
- **Git Branch**: `main`
- **Latest Tag**: `v1.10.2`
- **Python Runtime**: Python 3.13, FreeType 2.13+, HarfBuzz (Docker lock: 6.0.0, host CachyOS: 15.1.0)

## What is Verified
1. **Pipeline & Architectural Health**:
   - G4 import graph integrity verified clean via `python3 tools/check_imports.py` (0 errors).
   - Independent instance-owned FreeType rasterizer state design (`ir.py`, `raster.py`).
   - Round-trip IR deserialization and schema/coordinate invariant validation (`tools/test_boundary.py`, 0 validation errors, 369/369 pages `layout_sha256` round-trip equality).
   - Bug fix suite clean: `python3 tools/test_bugfixes.py` passes (tall table splitting, dynamic line-pitch room check, compact default pitch).
   - Clean git working tree; no tracked secrets, credentials, or unscrubbed logs.
2. **Corpus & Ground Truth Data**:
   - Added `exam/` directory containing `v1`, `v2`, `v3`, and `tables_images_exam` test EPUB fixtures.
   - `exam/v3` (`kindle_exam_v3.epub`): Complete ground truth dataset totaling 2,307 pages across 14 batches:
     - 12 Bookerly font sizes (`size_00_Bookerly` through `size_11_Bookerly`, 2,127 pages) under verified Standard layout (Line spacing 2/5, Paragraph/Word/Char spacing 1/5, Medium margins ~80px, Justified).
     - Compact theme preset (`theme_Compact`, 56 pages, pitch 53px, narrow margins 40px).
     - Large theme preset (`theme_Large`, 124 pages, pitch 82px, wide margins 133px).
     - All 14 batches labeled with verified reading configurations in `settings.txt`, `state.json`, and documented in `exam/v3/README.md`.
     - Added `exam/v3/settings_panels/` containing 16 Kindle UI settings menu screenshots.
   - `exam/tables_images_exam` (`kindle_tables_images_exam.epub`): Ground truth dataset for tables and images layout totaling 225 files (40 MB) across 3 theme presets captured on Samsung Galaxy M32 (`1080x2340`):
     - `theme_Compact`: 35 rendered pages, 23 expanded table screenshots, `index.csv`, `settings.txt`, and `state.json`.
     - `theme_Standard`: 44 rendered pages, 27 expanded table screenshots, `index.csv`, `settings.txt`, and `state.json`.
     - `theme_Large`: 57 rendered pages, expanded table screenshots, `index.csv`, `settings.txt`, and `state.json`.
3. **Milestone Progress (Stages A through H / v1.10.2)**:
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

## What is Broken / Open Issues
- **HarfBuzz Host vs Lock**: Host runtime HarfBuzz on CachyOS is `15.1.0`, whereas reproducibility lock in `requirements.lock` targets `6.0.0` (Docker container required for exact shaping reproduction).
- **Remaining Fixtures**: Master probe fixtures (`master_probe_v1.epub`, etc.) remain untracked per `DATA_PROVENANCE.md` until added.
- **Backlog Items**: Remaining items (`ul_indent_em`, `cover` p.1, `dl/dt/dd`, complex scripts) tracked in `BACKLOG.md`.

## Next Steps
- Evaluate against held-out `exam4` when available.
- Push release `v1.10.2` and new tags to GitHub.
