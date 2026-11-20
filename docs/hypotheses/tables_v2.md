# Pre-Registered Hypotheses: Tables Widths, Scale, Row Pitch & Image/Icon Details (`tables_v2.md`)

- **Baseline**: `kindle_render` `v1.11.7` (`commit d16827e`, HarfBuzz `6.0.0`, FreeType `2.12.1`)
- **3-Theme Baseline (`v1.11.7`)**:
  - `tables_images` (Standard `45/68`, `x0=79..1001`): `44` pages, `4/44` exact, `8,465,321` diff px
  - `ti_compact` (Compact `39/53`, `x0=39..1041`): `35` pages, `3/35` exact, `6,715,837` diff px
  - `ti_large` (Large `50/82`, `x0=131..949`): `57` pages, `3/57` exact, `10,382,599` diff px
  - **Total (3 themes)**: `25,563,757` diff px

---

## Group A — Table Width & Column Widths
- **Statement**: In full-width collapsed tables (`tot_max > avail_w`, where columns share `avail_w`), the last column (`ci == ncols - 1`, non-right-aligned) currently receives interior padding (`49.0`) in `_col_pad2` instead of outer-edge padding (`~71.0` / `2 * collapsed_table_pad_1x`), causing the last column to be `~20–22 px` too narrow and shifted right (`Amount` left edge `765/828/726` vs device `742/808/704` on Standard/Compact/Large) and causing the middle `Detail` column to wrap `~20 px` too wide.
- **Evidence**: Measured column ink edges across all 3 themes on `Table 5.1` (`Row / Detail / Amount`) and held-out column tables (`t1_columns`, `t4_align`, `t5_flow`).
- **Prediction**: Fixing outer-column padding / width sharing for full-width wrapping tables (`tot_max > avail_w`) will align `Amount` and `Detail` column boundaries across all 3 themes, reduce total 3-theme diff pixels, preserve page counts (`44/35/57`), lose `0` exact pages, and preserve `100%` of `probe`/`exam1`/`exam2`/`exam3`/`sizes_00..07` goldens.
- **Pass/Fail Criterion**: `PASS` iff 3-theme total diff improves, `0` exact pages lost, page counts do not worsen (`44/35/57`), and `0` regression golden failures.



### Group A Measured Result (`v1.11.8` — `PASS`)
- **Rule implemented (`kindle_render/page.py:add_table`)**: For full-width wrapping collapsed tables (`tot_1x > avail_w`, `sc_tbl > 0.75`, `not has_spans`), allocate `_col_pad2(ncols - 1) = 61.0` (`col_l_pad 24.5 + col_r_pad 36.5`) and `col_l_pad[ncols - 1] = 13.5` for left-aligned final columns (`38 px` inter-column gap + `47.5 px` right inset).
- **Table 5.1 Column Ink Alignment (`Amount` left..right / `Detail` right)**:
  - Standard p16: `Amount 743..843` (ref `743..845`, `0–2 px` error), `Detail` right `699` (ref `698`, `+1 px`).
  - Compact p13: `Amount 806..894` (ref `809..898`, `-3..-4 px` error).
  - Large p21: `Amount 703..796` (ref `704..798`, `-1..-2 px` error).
- **3-Theme Diff Delta (`v1.11.7 -> v1.11.8`)**:
  - `tables_images`: `8,465,321 -> 8,377,201` (**`-88,120`** px, `4/44` exact, `44` pages).
  - `ti_compact`: `6,715,837 -> 6,711,375` (**`-4,462`** px, `3/35` exact, `35` pages).
  - `ti_large`: `10,382,599 -> 10,379,474` (**`-3,125`** px, `3/57` exact, `57` pages).
  - **Total**: `25,563,757 -> 25,468,050` (**`-95,707`** px), `0` lost exact pages, `15/15` regression goldens PASS, `test_bugfixes` & `test_determinism` PASS.



## Step A2 — Em-Scaled Column Padding for Full-Width Wrapping Collapsed Tables
- **Statement**: In `page.py:add_table`, the pixel literals in `_col_pad2` (`64.0`, `61.0`, `49.0`) and `col_l_pad`/`col_r_pad` (`36.5`, `24.5`, `13.5`) for full-width wrapping collapsed tables (`is_col and tot_1x > avail_w and sc_tbl > 0.75 and not has_spans`) are fixed at Standard's scaled table font size (`tbl_sz = 43.2 px`), causing `Row`/`Detail`/`Amount` horizontal offsets on Compact (`tbl_sz = 37.4 px`: `Detail` left `210` vs device `199`, `Amount` left `806` vs `809`) and Large (`tbl_sz = 40.5 px`: `Detail` left `309` vs device `303`). Expressing these paddings in `em` of `tbl_sz` (`pad2: 1.45*em` col 0, `1.41*em` last col, `1.13*em` interior; `lp: 0.84*em` col 0, `0.31*em` last col left-aligned, `0.56*em` interior; `rp: 0.84*em` last col, `0.56*em` interior) will eliminate the hardcoded pixel literals and align all three themes simultaneously.
- **Evidence**: Measured `Table 5.1` ink x-segments at `v1.11.8`: Standard `[(118,140),(263,699),(743,843)]` vs dev `[(118,140),(261,698),(743,845)]`; Compact `[(81,120),(210,746),(806,894)]` vs dev `[(78,117),(199,766),(809,898)]`; Large `[(169,190),(309,636),(703,796)]` vs dev `[(167,188),(303,661),(704,798)]`.
- **Prediction**: Replacing the pixel literals with `tbl_sz`-scaled `em` expressions on full-width wrapping collapsed tables will align `Row`, `Detail`, and `Amount` within `<= 3 px` across all 3 themes, reduce 3-theme total diff below `25,468,050`, preserve page counts (`44/35/57`), lose `0` exact pages, and pass `15/15` regression goldens.
- **Pass/Fail Criterion**: `PASS` iff 3-theme total diff < `25,468,050`, `0` lost exact pages, page counts `44/35/57`, and `0` regression golden failures.



### Step A2 Measured Result (`v1.11.9` — `PASS`)
- **Rule**: Replaced hardcoded pixel literals in `_col_pad2` and `col_l_pad`/`col_r_pad` for full-width wrapping collapsed tables (`tot_1x > avail_w`) with `em` expressions of `tbl_em = tbl_size26 / 64.0`: `_col_pad2` = `1.45*em` (col 0), `1.41*em` (last col), `1.134*em` (interior), `0.845*em` (right-aligned last col); `col_l_pad` = `0.845*em` (col 0), `0.312*em` (left-aligned last col), `0.567*em` (interior); `col_r_pad` = `0.845*em` (last col), `0.567*em` (interior).
- **Table 5.1 Column Ink Extents (`v1.11.9` vs Device)**:
  - Standard p16: `Row 118..140` (`0 px`), `Detail 262..698` (`0–1 px`), `Amount 743..844` (`0–1 px`).
  - Compact p13: `Row 76..115` (`-2 px`), `Detail 197..772` (`-2/+6 px`), `Amount 812..901` (`+3 px`).
  - Large p21: `Row 166..187` (`-1 px`), `Detail 302..664` (`-1/+3 px`), `Amount 705..798` (`0–1 px`).
- **3-Theme Diff (`v1.11.8 -> v1.11.9`, `tools/corpus.py` `totals.diff_pixels`, strict HB `6.0.0`)**:
  - `tables_images`: `8,377,201 -> 8,371,614` (`-5,587` px, `4/44` exact, `44` pages).
  - `ti_compact`: `6,711,375 -> 6,697,823` (`-13,552` px, `3/35` exact, `35` pages).
  - `ti_large`: `10,379,474 -> 10,365,702` (`-13,772` px, `3/57` exact, `57` pages).
  - **Total**: `25,468,050 -> 25,435,139` (**`-32,911`** px), `0` lost exact pages, `15/15` regression goldens PASS.

---

## Group B — Scale of 4+ Column Tables & Row Pitch Inside Scaled Tables
- **Statement**: Express `sc_tbl` for `ncols >= 4` as a cross-theme function of `avail_w`, min-content text widths, and font size, and align scaled-table `line_p` / `row_pad` with `scale * unscaled_pitch`, while keeping 2–3 column wrapping tables (`Name/Description`) at `1.0x`.
- **Pass/Fail Criterion**: `PASS` iff 3-theme total diff improves, page counts do not worsen (`44/35/57`), `0` exact pages lost, and `0` regression golden failures.

---

## Group C — Cross-Theme Table Fixes (a–d)
- **Statement**: Verify (a) unbreakable header word min-width, (b) caption wrap with hyphenation, (c) colspan centering & merged-corner/rowspan column widths, and (d) 9-column `Qtr1..Qtr9` column solver across all 3 themes and fix only what reproduces everywhere without regressing goldens.
- **Pass/Fail Criterion**: `PASS` iff each kept sub-fix improves 3-theme total diff with `0` lost exact pages and `0` regression golden failures.

---

## Group D — Image Remainder Fit, 105x57 Split Icon & Split-Table Verification
- **Statement**: Verify Step 1 image remainder fit (already on `main` since `v1.11.6`), evaluate `105x57/58` split icon (`_render_split_table_icon_rgb`) after Groups A–C align split bottoms, and audit mid-row splitting + dashed rules across all 3 themes.
- **Pass/Fail Criterion**: `PASS` iff 3-theme total diff improves with `0` lost exact pages and `0` regression golden failures.
