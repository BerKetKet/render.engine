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


## Stage F `[F]` (Contents Page `nav` / p.2) & Stage G `[P]` (Boundary Hardening) — Completed (`boundary-1.9.1`)
- **DONE**:
  - **Stage F `[F]` (`commits 1677882`, `08889f2`)**:
    - Measured `<ol><li>` horizontal text indent (`ol_indent_em = 2.1054` across all 3 geometries `(34,51)`, `(42,57)`, `(45,68)`) and Skia subpixel antialiased link underline geometry (`role="link_underline"`, `base_thk = float(round(0.065 * sz_px))`, `y_off_top = base_thk + 0.02612 * sz_px + 0.00245 * pt_px - 0.5855`, `thk_fl = base_thk - 0.00015 * sz_px + 0.00013 * pt_px - 0.00165`, rendered with `min(cov_x, cov_y)` subpixel edge coverage in `kindle_render/raster.py`).
    - Achieved **`0` diff pixels (`100%` bitwise identity)** on **ALL 5 Contents pages (`p.2`)** across all 5 corpora (`probe` p.2 `27/27`, `exam1` p.2 `21/21`, `exam2` p.2 `27/27`, `exam3_normal` p.2 `18/18`, `exam3_small` p.2 `18/18`) plus `+101` positional-exact lines on body `<ol>` pages (`exam2` p.7 and `exam2` p.12 also became `100%` bitwise identical).
    - Total across all 5 corpora (`357` compared pages): **`179 / 357` bitwise-identical pages** (`+17` over `1.8.0-rc1`, `+7` over `rhythm-1.9.0`), **`8,913 / 9,638` positional-exact lines** (`+755` over `1.8.0-rc1`, `+218` over `rhythm-1.9.0`), and **`4,888,301` total diff pixels** (`-58.0%` reduction from `11,642,724`). Zero regressions on any corpus.
  - **Stage G `[P]` (`commit 8bc97c9`)**:
    - Added full IR deserialization (`PositionedDocument.from_dict`, `PositionedPage.from_dict`, `_cmd_from_dict`) and schema/coordinate invariant validation (`validate_ir_page`, `validate_ir_document`) in `kindle_render/ir.py`.
    - Added `tools/test_boundary.py` and verified `0` validation errors, `369/369` pages `layout_sha256` round-trip equality, and `25/25` sampled pages `100%` pixel SHA-256 round-trip equality across all 5 corpora (`tools/reports/stage_g/boundary_hardening.json`, `tools/reports/stage_g/boundary_hardening.md`).
- **NEXT**:
  - **Stage H `[F]` (Re-scoped Round 1 Fidelity Items)**:
    1. `<mark>` highlight preservation in `kindle_render/epub.py:_collapse` (`bg=getattr(r, "bg", None)`) and `<mark>` box geometry in `kindle_render/page.py:draw_line`.
    2. `ul_indent_em` subpixel `em` measurement across `(34,51)`, `(42,57)`, `(45,68)` and `dl/dt/dd` / `figure` / `cover` p.1 block rules.
    3. Inline monospace `<code>`/`<kbd>`, `sub`/`sup`, drop caps (`.dc::first-letter` / `.ini::first-letter`), hyphenation apostrophes, and complex scripts.
    4. Subpixel `32/64` tie-breaking in justified line last-word placement (`(start26 + off26) & 63 == 32`).
- **EXACT COMMANDS TO RESUME**:
  ```bash
  python3 tools/check_imports.py
  python3 tools/test_harfbuzz_lock.py
  python3 tools/test_boundary.py
  python3 tools/test_parallel_raster.py
  python3 tools/test_text_layer.py
  python3 tools/corpus.py --only probe --skip-existing
  ```


## Stage H `[F]` — Shaping, Tokenization, `<mark>` Highlights & `float32` Justified Pen Accumulation — Completed (`v1.10.0`)
- **DONE**:
  - **Stage H1 (`commit 8f2c6f6`)**: Preserved `bg` in `epub.py:_collapse`, added vulgar eighth/third fractions in `fonts.py`, added leading ellipsis `…` splitting and cross-box GPOS kerning across `hyphen`/`endash`/`emdash`/`slash` in `layout.py:build_items` (`+9` exact pages, `0` regressions).
  - **Stage H2 (`commit c428322`)**: Implemented `float32` justified-line last-word pen accumulation in `layout.py:layout_line` and `page.py` for `(start26 + off26) & 63 == 32` tie-breaking (`222 / 357` exact pages, `9,013 / 9,638` pos lines, `4,611,304` total diff px across all 5 corpora; `0` lost exact pages).
  - **Goldens & Gates (`commit 91b5736`)**: Updated all 5 corpus goldens; all gates `G1`–`G6` passed (`check_imports.py`, `test_harfbuzz_lock.py`, `test_parallel_raster.py`, `test_text_layer.py`, `test_boundary.py`).
- **NEXT**:
  - Evaluate `v1.10.0` against held-out `exam4` when available; remaining items (`ul_indent_em`, `cover` p.1, `dl/dt/dd`, complex scripts) are tracked in `BACKLOG.md`.
- **CURRENT COMMIT / TAG**: `v1.10.0` (`round1-1.10.0`)

## `v1.10.1` — `<mark>` Highlight Bounds (`hhea.ascent` + `floor(pitch/1.2)`)
- Updated `page.py:draw_line` (`commit 812c24a`), `-2,244` diff px on `exam2` p.40 (`4,609,060` total diff px across all 5 corpora), all gates `G1`–`G6` passed.
