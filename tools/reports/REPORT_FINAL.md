# kindle_render v1.10.0 — Unified Plan Final Report (Stages A–H)

## 1. 5-Corpus Progression Summary (`1.8.0-rc1` -> `rhythm-1.9.0` -> `boundary-1.9.1` -> `v1.10.0`)

| Corpus | Geometry (`size_px, pitch`) | `1.8.0-rc1` Exact Pages | `rhythm-1.9.0` Exact Pages | `boundary-1.9.1` Exact Pages | **`v1.10.0` Exact Pages** | `1.8.0-rc1` Pos Lines | **`v1.10.0` Pos Lines** | `1.8.0-rc1` Diff Px | **`v1.10.0` Diff Px** |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `probe` | `42 px, pitch 57` | `37 / 86` | `37 / 86` | `38 / 86` | **`43 / 86`** (`+6`) | `2,703 / 2,863` | **`2,753 / 2,863`** (`+50`) | `476,566` | **`415,528`** (`-12.8%`) |
| `exam1` | `45 px, pitch 68` | `42 / 70` | `42 / 70` | `43 / 70` | **`50 / 70`** (`+8`) | `1,402 / 1,568` | **`1,452 / 1,568`** (`+50`) | `1,593,164` | **`1,516,670`** (`-4.8%`) |
| `exam2` | `42 px, pitch 57` | `35 / 65` | `35 / 65` | `38 / 65` | **`40 / 65`** (`+5`) | `1,322 / 1,529` | **`1,395 / 1,529`** (`+73`) | `1,140,913` | **`1,037,156`** (`-9.1%`) |
| `exam3_normal` | `45 px, pitch 68` | `38 / 82` | `42 / 82` | `43 / 82` | **`60 / 82`** (`+22`) | `1,740 / 2,027` | **`1,899 / 2,027`** (`+159`) | `2,893,060` | **`762,672`** (`-73.6%`) |
| `exam3_small` | `34 px, pitch 51` | `10 / 54` | `16 / 54` | `17 / 54` | **`29 / 54`** (`+19`) | `991 / 1,651` | **`1,514 / 1,651`** (`+523`) | `5,539,021` | **`879,278`** (`-84.1%`) |
| **TOTAL (All 5)** | **357 compared** | **`162 / 357`** | **`172 / 357`** | **`179 / 357`** | **`222 / 357` (`+60`)** | **`8,158 / 9,638`** | **`9,013 / 9,638` (`+855`)** | **`11,642,724`** | **`4,611,304` (`-60.4%`)** |

## 2. Stage-by-Stage Implemented Changes (`A`–`H`)
- **Stage A `[P]` (Hygiene)**: Locked `libharfbuzz.so` (`6.0.0`) in `kindle_render/fonts.py`, added `NO-GOLDEN` reporting in `tools/corpus.py`, verified `max_device_ink_y <= 2203`, and built `tools/rhythm.py`.
- **Stage B `[P]` (Hypothesis Registry)**: Added `tools/hypotheses/evaluate.py` and `tools/reports/hypotheses/registry.json` across all 5 corpora.
- **Stage C `[F]` (Vertical Rhythm)**: Derived cross-geometry vertical spacing and heading/list/paragraph margin formulas in `kindle_render/page.py` (`+6` exact pages on `exam3_small`, `+4` on `exam3_normal`).
- **Stage D `[F]` (Page-Break Rules)**: Generalized page-bottom heading widow/orphan lookahead and list-item margin collapse.
- **Stage E `[F]` (Ragged Text & Last-Glyph Rounding)**: Generalized balanced ragged DP and trailing glyph rounding.
- **Stage F `[F]` (Contents Page `nav` / p.2)**: Measured `ol_indent_em = 2.1054` and Skia `min(cov_x, cov_y)` subpixel link underlines (`role="link_underline"`), achieving `0` diff pixels (`100%` bitwise identity) on all 5 Contents pages (`p.2`) plus `+101` positional-exact lines on body `<ol>` pages.
- **Stage G `[P]` (Boundary Hardening)**: Added `from_dict` / `from_json` deserialization and `validate_ir_page` / `validate_ir_document` in `kindle_render/ir.py`; verified `369/369` pages `layout_sha256` and `25/25` sampled pages pixel SHA-256 round-trip equality in `tools/test_boundary.py`.
- **Stage H `[F]` (Shaping, Tokenization, Highlights & `float32` Pen Accumulation)**:
  - **H1**: Preserved `bg=getattr(r, "bg", None)` in `kindle_render/epub.py:_collapse` (`-6,658` diff px on `exam2` p.40); added eighth/third vulgar fractions (`⅓`, `⅔`, `⅛`–`⅞`) in `kindle_render/fonts.py:names_with_clusters`; added `…` to `lstrip`, split leading `ellipsis` `Box`es with `Penalty(0, 0, False)`, and applied cross-box GPOS kerning across unspaced `{"hyphen", "endash", "emdash", "slash"}` boundaries in `kindle_render/layout.py:build_items` (`+9` exact pages, `-257,355` diff px, `0` regressions).
  - **H2**: Added `float32` justified-line pen accumulation (`sp_fl = f32(std_sp) + f32(delta) / f32(k)`) for last-word glyphs landing on the half-pixel boundary `(start26 + off26) & 63 == 32` in `kindle_render/layout.py:layout_line` and `kindle_render/page.py` (`+43` exact pages over Stage F, `0` lost exact pages on any corpus).

## 3. Verification Gates (`G1`–`G6`)
- `G1` (Goldens): All 5 corpus goldens updated and verified (`golden_passed=True`, `layout_golden_passed=True`, `0` lost exact pages).
- `G2` (5-Corpus Metrics): Measured and recorded before/after across `probe`, `exam1`, `exam2`, `exam3_normal`, and `exam3_small`.
- `G3` (Determinism): `deterministic=True` on all 5 corpora.
- `G4` (`tools/check_imports.py`): `passed=True errors=0`.
- `G5` (`tools/test_parallel_raster.py`, `tools/test_text_layer.py`, `tools/test_boundary.py`): `ALL PASSED`.
- `G6` (`tools/test_harfbuzz_lock.py`): `loaded=True version=6.0.0 locked=6.0.0 PASSED`.
