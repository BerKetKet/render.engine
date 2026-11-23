# `kindle_render` v1.11.16 — Spacing Settings Device Fit Report

## 1. Readings of Ambiguities Taken
- **Keep rule (`<= 5%` single-cell worsening cap)**: Enforced strictly. `liga=False` on `char >= 2` improved Standard (`-22k`) and Large (`-23k`) and lowered the 3-theme char total by `-7.3k`, but worsened `Compact char 2` by `+44.9k` (`+11%`), so it was reverted and documented rather than kept.
- **No per-theme magic**: The Standard step-1 `h1` `mt` fix is expressed purely as the existing tight-regime floor check `std_body_pitch < (19.0 / 14.0) * c.size_px()` (`61 < 61.071` on 45 px vs `53 > 52.93` on 39 px and `68 > 67.86` on 50 px), gated on `line_spacing_step is not None and pitch == 0`.
- **S-H open items**: Deferred so `v1.11.16` stays strictly scoped to spacing settings without touching tables.

## 2. Before / After Table (`v1.11.15` -> `v1.11.16`, Pages 2–5 Summed, Thousand px)

| Variable | Theme | Step 1 | Step 2 | Step 3 | Step 4 | Step 5 | Theme Δ |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **line** | Standard | `231 -> 19` | `0 -> 0` | `117 -> 117` | `148 -> 148` | `80 -> 80` | `-212k` |
| **line** | Compact | `153 -> 153` | `175 -> 175` | `471 -> 471` | `249 -> 249` | `134 -> 134` | `0` |
| **line** | Large | `139 -> 139` | `126 -> 126` | `194 -> 194` | `147 -> 147` | `91 -> 91` | `0` |
| **paragraph** | Standard | `231 -> 19` | `217 -> 28` | `231 -> 56` | `228 -> 70` | `173 -> 28` | `-879k` |
| **paragraph** | Compact | `153 -> 153` | `124 -> 124` | `143 -> 143` | `156 -> 156` | `124 -> 124` | `0` |
| **paragraph** | Large | `139 -> 139` | `160 -> 160` | `190 -> 190` | `132 -> 132` | `135 -> 135` | `0` |
| **word** | Standard | `231 -> 19` | `255 -> 70` | `765 -> 593` | `597 -> 457` | `1020 -> 891` | `-837k` |
| **word** | Compact | `153 -> 153` | `665 -> 31` | `227 -> 227` | `457 -> 457` | `1096 -> 1096` | `-634k` |
| **word** | Large | `139 -> 139` | `571 -> 571` | `736 -> 736` | `808 -> 808` | `829 -> 829` | `0` |
| **char** | Standard | `231 -> 19` | `530 -> 400` | `735 -> 604` | `790 -> 580` | `775 -> 671` | `-785k` |
| **char** | Compact | `153 -> 153` | `409 -> 409` | `544 -> 547` | `470 -> 470` | `478 -> 478` | `+3k` |
| **char** | Large | `139 -> 139` | `487 -> 487` | `572 -> 572` | `514 -> 514` | `659 -> 659` | `0` |

- **Standard**: `7,584,793 -> 4,871,548` (`-2,713,245` px)
- **Compact**: `6,534,794 -> 5,903,914` (`-630,880` px)
- **Large**: `6,909,148 -> 6,909,148` (`0` px)
- **GRAND TOTAL**: **`21,028,735 -> 17,684,610` (`-3,344,125` px vs `v1.11.15`; `-8,622,828` px vs `v1.11.14`)**

## 3. Learned Acceptance Region (`docs/data/spacing_acceptance_region.json`)
- **Word spacing (`word_spacing_step >= 2`)**: Total-fit KP (greedy regressed `+1.21M`). Shrink budget decays smoothly with extra word spacing in `em`: `max_sh = G * (0.099 if ragged else 0.179) * max(word_spacing_shrink_mult, 1.0 - word_spacing_shrink_decay * extra_word_em)` with `word_spacing_shrink_decay = 3.27`, `word_spacing_shrink_mult = 0.10` (`0.28×` at step 2, `0.10×` at steps 3–5). Stretch remains governed by `s0 = (slack / G) * 2.0` normalized by base space `G = sum(min(w, 0.25*size))`.
- **Character spacing (`char_spacing_step >= 2`)**: Total-fit KP with `char_spacing_shrink_mult = 0.80` (`max_sh = G * 0.179 * 0.80`).

## 4. Kept / Reverted Experiments
- **KEPT**: S-A3 (`word_spacing_shrink_decay = 3.27`: `-633,847` px on Compact word 2), S-C1 (`char_spacing_shrink_mult = 0.80`: `-112,179` px across char 2..5, fixing Standard char 4 `-101k`), S-D1 (tight-floor `h1` `mt += 1`: `-2,713,245` px on Standard step-1 runs; Standard line 1 `p3/p4/p5` all `0`).
- **REVERTED**: S-A2 greedy (`+1.21M` word, `+229k` char), S-A4 cubic badness & `shk=5..12` (`+50k..+765k`), S-C2 `liga=False` (`-7.3k` net but `+11%` on Compact char 2) and `kern=False` (`+540k`), S-D unified `KR_H1MT` (`+500k` on Compact line 1).

## 5. Remaining Worst 5 Pages Per Variable (Side-by-Side PNGs in `docs/hypotheses/spacing_fit2/`)
- **line**: `Com s3 p3 (156,533)`, `Com s3 p5 (145,464)`, `Lar s1 p3 (117,938)`, `Com s3 p4 (111,752)`, `Com s2 p4 (111,752)` — residual `1 px` `h1` `mt` / `h_to_body` rounding on Compact steps 2–3 and Large step 1.
- **paragraph**: `Lar s1 p3 (117,938)`, `Lar s2 p4 (112,108)`, `Com s5 p5 (111,752)`, `Com s4 p5 (111,752)`, `Com s3 p5 (111,752)` — inherited from step-1 `line` baseline offset on Large p3 and Compact p4/p5.
- **word**: `Com s5 p4 (431,441)`, `Sta s5 p4 (400,969)`, `Com s5 p3 (392,683)`, `Lar s3 p5 (358,322)`, `Lar s4 p5 (348,598)` — high-step stretch-vs-hyphenation break differences when line slack exceeds `~0.5 * L`.
- **char**: `Lar s5 p5 (288,283)`, `Sta s5 p5 (285,980)`, `Com s5 p4 (248,066)`, `Lar s3 p5 (246,009)`, `Sta s3 p4 (241,255)` — ligature disabling (`fi/fl`) combined with high-step tracking break differences.

## 6. Gate Results (`KINDLE_RENDER_STRICT_HARFBUZZ=1`, HarfBuzz `6.0.0`)
- **Unit gates**: `check_imports` PASS, `test_harfbuzz_lock` (`6.0.0`) PASS, `test_bugfixes` PASS.
- **Goldens (`18/18` PASS, 100% bit-identical to `v1.11.15`, 0 golden changes)**: `probe`, `exam1`, `exam2`, `exam3_normal`, `exam3_small`, `e3_compact`, `e3_large`, `tables_images` (44p), `ti_compact` (35p), `ti_large` (57p), `sizes_00..sizes_07` (8/8). 3-theme table total unchanged at `24,122,051`.
- **Multi-book & combined smoke**: `exam1`, `exam2`, `tables_images` monotone page counts across line/para steps 1..5 (`0` empty pages, `0` glyph overflows); combined `W+C` and `L+P` clean.
