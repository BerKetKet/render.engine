# `kindle_render` v1.11.18 — Possessive Hyphenation Fix, Underline Model & Spacing Fit Report

## 1. Interpretation Choices
- **Default-render change allowed (Ground Rule 0)**: Fixing the English possessive `'s` hyphenation bug in `kindle_render/layout.py` improved default `exam1` by **-41,673 diff px** (`1,506,993 -> 1,465,320`, `e01_prologue 70,279 -> 28,795`, `+3` exact lines, `0` lost exact pages) while keeping **all 17 other default corpora** (`probe`, `exam2`, `exam3_normal`, `exam3_small`, `e3_compact`, `e3_large`, `tables_images`, `ti_compact`, `ti_large`, and `sizes_00..sizes_07`) **100% bit-identical**. Accordingly, it was enabled unconditionally and `tools/golden/exam1.json` was regenerated.
- **Spacing-mode gating**: `link_underline_center_em = 0.12593` stays gated on `line_spacing_step is not None and pitch == 0`, and `char_spacing_no_liga_px = 2.5` only activates when `user_char_spacing_26() >= 2.5 * 64`, so default renders are completely unaffected by both.

## 2. Before / After Table (`v1.11.17` -> `v1.11.18`, Pages 2–5 Summed, Thousand px)

| Variable | Theme | Step 1 | Step 2 | Step 3 | Step 4 | Step 5 | Theme Δ |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **line** | Standard | `19 -> 10` | `0 -> 0` | `10 -> 10` | `110 -> 110` | `36 -> 36` | `-10k` |
| **line** | Compact | `153 -> 41` | `175 -> 63` | `471 -> 359` | `249 -> 138` | `115 -> 115` | `-447k` |
| **line** | Large | `43 -> 32` | `43 -> 32` | `194 -> 183` | `117 -> 117` | `32 -> 32` | `-32k` |
| **paragraph** | Standard | `19 -> 10` | `19 -> 10` | `19 -> 10` | `19 -> 10` | `19 -> 10` | `-48k` |
| **paragraph** | Compact | `153 -> 41` | `124 -> 12` | `123 -> 12` | `123 -> 11` | `124 -> 12` | `-559k` |
| **paragraph** | Large | `43 -> 32` | `45 -> 34` | `58 -> 47` | `49 -> 38` | `29 -> 18` | `-54k` |
| **word** | Standard | `19 -> 10` | `70 -> 60` | `593 -> 583` | `457 -> 446` | `891 -> 880` | `-52k` |
| **word** | Compact | `153 -> 41` | `31 -> 31` | `227 -> 227` | `457 -> 457` | `1096 -> 1096` | `-112k` |
| **word** | Large | `43 -> 32` | `491 -> 480` | `665 -> 654` | `737 -> 725` | `803 -> 791` | `-57k` |
| **char** | Standard | `19 -> 10` | `400 -> 381` | `604 -> 494` | `580 -> 561` | `671 -> 652` | `-177k` |
| **char** | Compact | `153 -> 41` | `409 -> 409` | `547 -> 533` | `470 -> 471` | `478 -> 481` | `-122k` |
| **char** | Large | `43 -> 32` | `448 -> 378` | `527 -> 511` | `471 -> 457` | `628 -> 586` | `-153k` |

- **Standard**: `4,578,050 -> 4,290,767` (`-287,283` px)
- **Compact**: `5,831,191 -> 4,591,765` (`-1,239,426` px)
- **Large**: `5,507,764 -> 5,211,916` (`-295,848` px)
- **GRAND TOTAL**: **`15,917,005 -> 14,094,448` (`-1,822,557` px vs `v1.11.17`; `-12,212,990` px / `-46.4%` vs `v1.11.14`)**

## 3. Root Cause of Compact Page 4 (`111,752 -> 0`)
- Natural glyph widths on all 29 ragged body lines across Standard/Compact/Large have **`width_device / width_ours = 1.00000`** (`mean_dw = +0.00 px`), and Compact p4 line 2 (`"burned unregarded; ... and"`) had `+24.02 px` of positive slack (no shrink needed).
- The device's break sequence actually had a **lower** Knuth-Plass cost (`47.50`) than ours (`55.28`), because `kindle_render/layout.py:441-447` matched `family’s` (`a_idx = 6`) against the French elision rule (`1 <= a_idx <= 6`), stripping `family’` into `lead_punct` and leaving `alpha = "s"` unhyphenated (blocking `fam-ily’s`).
- Fixing apostrophe handling to strip trailing `'s`/`’s` into `trail_punct` when `len(left) >= min_word_length` (and requiring `len(right) >= 2` for French prefix elision) dropped Compact p4 from **`111,752 -> 0` (bitwise exact)** across all 7+ cells and improved default `exam1` by **`-41,673` diff px**.

## 4. Underline Model (S2)
- Subpixel `link_underline` on `p2` accounted for `100%` of remaining `Standard line 1` (`19,270`) and `Large line 1` (`21,439`) diffs (`0` text diff px).
- Modeling `y_off_top = _bl_frac + link_underline_center_em * sz_px - 0.5 * thk_fl` (`_bl_frac = bf - round(bf)`, `link_underline_center_em = 0.12593`) keeps `Standard line 2` at **`0`** while halving Standard (`19,270 -> 9,590`) and Large (`21,439 -> 10,693`) underline diffs (`~-360k` px across step-1 runs).

## 5. Acceptance Regions (S3 & S4)
- **Word**: Smooth em-decay `max_sh = G * (0.099 if ragged else 0.179) * max(0.10, 1.0 - 3.27 * extra_word_em)` (`6,432,289`) decisively beat constant-px shrink (`0.3/0.6/1.0` px/space -> `7.42M / 7.12M / 7.69M`, reverted).
- **Char**: `char_spacing_step_em = 0.056`, `char_spacing_shrink_mult = 0.80`, plus `char_spacing_no_liga_px = 2.5` (disabling ligatures when tracking `>= 2.5 px`, improving all 3 themes simultaneously by `-70,492` px without regressing Compact char 2).

## 6. Kept / Reverted Experiments
- **KEPT**: S1b possessive `'s` hyphenation fix (`-1.24M` Compact + `-41,673` default `exam1`), S2 float-baseline link underline (`~-360k`), S4 `char_spacing_no_liga_px = 2.5` (`-70,492` across all 3 themes).
- **REVERTED**: S3(e) constant-px shrink (`+690k..+1.26M` worse).

## 7. Remaining Worst 5 Pages Per Variable (Side-by-Side PNGs in `docs/hypotheses/spacing_fit4/`)
- **line**: `Com s3 p3 (156,533)`, `Com s3 p5 (145,464)`, `Com s4 p3 (91,762)`, `Lar s3 p3 (89,507)`, `Com s5 p4 (74,175)` — `1 px` `h1` `mt` offset on Compact steps 3–5 and Large step 3.
- **paragraph**: `Lar s3 p5 (31,369)`, `Com s1 p5 (29,317)`, `Lar s4 p5 (21,397)`, `Lar s2 p4 (21,397)`, `Lar s1 p3 (21,397)` — Standard paragraph 1..5 are all `9.6k` (underline only) and Compact paragraph 2..5 are all `11.3k..11.9k` (underline only)!
- **word**: `Com s5 p4 (431,441)`, `Sta s5 p4 (400,969)`, `Com s5 p3 (392,683)`, `Lar s3 p5 (358,810)`, `Lar s4 p5 (348,598)` — high-step stretch-vs-hyphenation break differences.
- **char**: `Sta s5 p5 (285,892)`, `Lar s5 p5 (265,763)`, `Com s5 p4 (249,697)`, `Lar s3 p5 (246,468)`, `Com s4 p4 (237,821)` — high-step tracking break differences.

## 8. Gate Results (`KINDLE_RENDER_STRICT_HARFBUZZ=1`, HarfBuzz `6.0.0`)
- **Unit gates**: `check_imports` PASS, `test_harfbuzz_lock` (`6.0.0`) PASS, `test_bugfixes` PASS.
- **Default Goldens (`18/18` PASS)**:
  - **`exam1` (UPDATED ON PURPOSE)**: `1,506,993 -> 1,465,320` (**`-41,673` diff px**, `e01_prologue 70,279 -> 28,795`, `50/70` exact pages unchanged, `pos_lines 1452 -> 1455/1568`).
  - **All 17 other goldens (100% BIT-IDENTICAL to `v1.11.17`)**: `probe`, `exam2`, `exam3_normal`, `exam3_small`, `e3_compact`, `e3_large`, `tables_images` (44p, 3-theme total `24,122,051`), `ti_compact` (35p), `ti_large` (57p), `sizes_00..sizes_07` (8/8).
