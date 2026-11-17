# Stage H Summary Report (`v1.10.2`)

## 1. Overview
Stage H completes the Round 1 fidelity items, decompiled Kindle library verification passes, and the 8-item bug-fix sweep across all 5 corpora (`probe`, `exam1`, `exam2`, `exam3_normal`, `exam3_small`), advancing total bitwise-identical pages from `179 / 357` (`boundary-1.9.1`) to **`222 / 357`** (`+43` exact pages in Stage H, `+60` total vs `1.8.0-rc1`) with **`0` lost exact pages**.

## 2. Sub-Stage Breakdown
1. **Stage H1 (`commit 8f2c6f6`)**:
   - Preserved `bg=getattr(r, 'bg', None)` in `kindle_render/epub.py:_collapse`.
   - Added vulgar third/eighth fraction decompositions (`\u2153`, `\u2154`, `\u215b`–`\u215e`) in `kindle_render/fonts.py:names_with_clusters`.
   - Added `\u2026` to `lstrip`, split leading `ellipsis` `Box`es into `Box([ellipsis]) + Penalty(0, 0, False) + Box(rest)`, and applied cross-box GPOS kerning across unspaced `{"hyphen", "endash", "emdash", "slash"}` splits in `kindle_render/layout.py:build_items`.
   - **Impact**: `+9` exact pages (`179 -> 188`), `-257,355` diff px, `0` regressions.
2. **Stage H2 (`commit c428322`, `v1.10.0`)**:
   - Replaced mixed float64/round space placement on justified lines with `float32` space step `sp_fl = f32(std_sp) + f32(delta) / f32(k)` and `float32` pen accumulation across words in `kindle_render/layout.py:layout_line` and `kindle_render/page.py`.
   - **Impact**: `+34` exact pages (`188 -> 222`), `-406,374` diff px, `0` regressions.
3. **Stage H3 (`commit 812c24a`, `v1.10.1`)**:
   - Tested all 4 candidate items from decompiled `libkrf.so` / `libyjr.so` notes one at a time; kept Bookerly `hhea.ascent` (`0.900 * size_px`) and `floor(pitch / 1.2)` `<mark>` highlight vertical bounds in `kindle_render/page.py:draw_line`.
   - **Impact**: `-2,244` diff px on `exam2` p.40 (`12/13 -> 13/13` pos-exact lines), `0` regressions.
4. **Stage H4 (`commit f596a12`, `v1.10.2` Bug-Fix Sweep)**:
   - Fixed tall table pagination (`page.py:add_table`), dynamic scaled-run `room` check (`page.py:add_text_block`), `math.floor(x + 0.5)` and `pitch=0` at `34px -> 51` (`config.py:pitch_px`), docstring & `BACKLOG.md` cleanup, and `_skia_bilerp_rgb` de-overfitting (`page.py`).
   - Added `tools/test_bugfixes.py` covering all fixed items plus verified device behaviors (multi-line heading split on `exam1` p.7–8 and `n_items > 1000` greedy fallback on `exam1 e13_pagination`).

## 3. 5-Corpus Metrics (`boundary-1.9.1` -> `v1.10.2`)
| Corpus | Geometry | `boundary-1.9.1` Exact | **`v1.10.2` Exact** | `boundary-1.9.1` Pos Lines | **`v1.10.2` Pos Lines** | `boundary-1.9.1` Diff Px | **`v1.10.2` Diff Px** |
|---|---|---:|---:|---:|---:|---:|---:|
| `probe` | `42px, 57` | `38 / 86` | **`43 / 86`** (`+5`) | `2,750 / 2,863` | **`2,753 / 2,863`** | `419,605` | **`416,248`** |
| `exam1` | `45px, 68` | `43 / 70` | **`50 / 70`** (`+7`) | `1,422 / 1,568` | **`1,452 / 1,568`** | `1,532,375` | **`1,516,670`** |
| `exam2` | `42px, 57` | `38 / 65` | **`40 / 65`** (`+2`) | `1,394 / 1,529` | **`1,395 / 1,529`** | `1,039,589` | **`1,034,912`** |
| `exam3_normal` | `45px, 68` | `43 / 82` | **`60 / 82`** (`+17`) | `1,843 / 2,027` | **`1,899 / 2,027`** | `1,150,423` | **`762,315`** |
| `exam3_small` | `34px, 51` | `17 / 54` | **`29 / 54`** (`+12`) | `1,508 / 1,651` | **`1,514 / 1,651`** | `1,133,053` | **`878,921`** |
| **TOTAL** | **357 pages** | **`179 / 357`** | **`222 / 357` (`+43`)** | **`8,917 / 9,638`** | **`9,013 / 9,638` (`+96`)** | **`5,275,045`** | **`4,609,066` (`-665,979`)** |
