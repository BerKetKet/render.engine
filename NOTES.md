# Development Notes — Kindle Render Engine

## Current State
- **Working Directory**: `/home/bgg/projects/render.engine`
- **Module**: `kindle_render` v1.9.0
- **Git Branch**: `main`
- **Latest Tag**: `rhythm-1.9.0`
- **Python Runtime**: Python 3.13, FreeType 2.13+, HarfBuzz (Docker lock: 6.0.0, host CachyOS: 15.1.0)

## What is Verified
1. **Pipeline & Architectural Health**:
   - G4 import graph integrity verified clean via `python3 tools/check_imports.py` (0 errors).
   - Independent instance-owned FreeType rasterizer state design (`ir.py`, `raster.py`).
   - Clean git working tree; no tracked secrets, credentials, or unscrubbed logs.
2. **Corpus & Ground Truth Data**:
   - Added `exam/` directory containing `v1`, `v2`, and `v3` test EPUB fixtures.
   - `exam/v3` (`kindle_exam_v3.epub`): Complete ground truth dataset totaling 2,307 pages across 14 batches:
     - 12 Bookerly font sizes (`size_00_Bookerly` through `size_11_Bookerly`, 2,127 pages) under verified Standard layout (Line spacing 2/5, Paragraph/Word/Char spacing 1/5, Medium margins ~80px, Justified).
     - Compact theme preset (`theme_Compact`, 56 pages, pitch 53px, narrow margins 40px).
     - Large theme preset (`theme_Large`, 124 pages, pitch 82px, wide margins 133px).
     - All 14 batches labeled with verified reading configurations in `settings.txt`, `state.json`, and documented in `exam/v3/README.md`.
     - Added `exam/v3/settings_panels/` containing 16 Kindle UI settings menu screenshots.
3. **Milestone Progress (Stages A through E / v1.9.0)**:
   - **Stage A (`1.8.0-rc1`)**: Version lock & loud failure for HarfBuzz, baseline goldens for `exam3_normal` & `exam3_small`, unaligned pair filtering across 5 corpora (`tools/rhythm.py`).
   - **Stage B**: Read-only Kindle layout hypothesis registry (`docs/hypotheses/kindle_formulae_v0.md`) and evaluators (`tools/hypotheses/evaluate.py`).
   - **Stage C**: Cross-geometry vertical rhythm normalization (`eff_body_pitch`, exact heading margin multipliers, spacer advances, horizontal `em`/`rem` basis).
   - **Stage D**: Page-break rules for list items, uncollapsed tables, and horizontal rules (`add_hr`).
   - **Stage E**: Forced `<br/>` segment line breaking in `break_kp` achieving 100% bitwise matching on key ragged pages (`exam3_normal` p.48-49, `exam3_small` p.31), plus full last-glyph rounding census.
   - Cumulative 5-corpus metrics: 172/357 exact pages (+10), 8,695/9,638 positioned lines (+537), 5,275,033 diff pixels (-54.7%).

## What is Broken / Open Issues
- **HarfBuzz Host vs Lock**: Host runtime HarfBuzz on CachyOS is `15.1.0`, whereas reproducibility lock in `requirements.lock` targets `6.0.0` (Docker container required for exact shaping reproduction).
- **Remaining Fixtures**: Master probe fixtures (`master_probe_v1.epub`, etc.) remain untracked per `DATA_PROVENANCE.md` until added.
- **Stage F (Contents Page)**: Pending owner review before initiation.

## Next Steps
- Stage F (Contents Page): Pending owner review before initiation.
