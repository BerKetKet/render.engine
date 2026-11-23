# `kindle_render` v1.11.17 — Step-1 Geometry & Spacing Fit Report

## 1. Interpretation Choices
- **Fractional vs Integer Body Pitch**: Least-squares regression over 33 consecutive body lines on device captures showed `0.00 px` residual for integer body pitches across Standard and Large (`61.000/68.000/74.000/104.000/134.000` and `68.000/76.000/82.000/116.000/149.000`), while the isolated `±1 px` bands on `Large line 1 p2` were link underline bands. Therefore integer body pitch was retained, `h1` `mb_est` was derived from `pitch_fl` (`heading_line_spacing_mb_em = 0.652`, `len(lines) >= 2`), and the `(19/14)` tight-floor guard for Standard step-1 `h1` `mt` was kept and documented as an open residual.
- **Zero Default Regression**: All new spacing-mode behaviours (`heading_line_spacing_mb_em`, spillover `<ol>` shift) are gated on `line_spacing_step is not None and pitch == 0` so all `18/18` default goldens remain 100% bit-identical to `v1.11.16`.

## 2. Before / After Table (`v1.11.16` -> `v1.11.17`, Pages 2–5 Summed, Thousand px)

| Variable | Theme | Step 1 | Step 2 | Step 3 | Step 4 | Step 5 | Theme Δ |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **line** | Standard | `19 -> 19` | `0 -> 0` | `117 -> 10` | `148 -> 110` | `80 -> 36` | `-189k` |
| **line** | Compact | `153 -> 153` | `175 -> 175` | `471 -> 471` | `249 -> 249` | `134 -> 115` | `-20k` |
| **line** | Large | `139 -> 43` | `126 -> 43` | `194 -> 194` | `147 -> 117` | `91 -> 32` | `-269k` |
| **paragraph** | Standard | `19 -> 19` | `28 -> 19` | `56 -> 19` | `70 -> 19` | `28 -> 19` | `-104k` |
| **paragraph** | Compact | `153 -> 153` | `124 -> 124` | `143 -> 123` | `156 -> 123` | `124 -> 124` | `-53k` |
| **paragraph** | Large | `139 -> 43` | `160 -> 45` | `190 -> 58` | `132 -> 49` | `135 -> 29` | `-533k` |
| **word** | Standard | `19 -> 19` | `70 -> 70` | `593 -> 593` | `457 -> 457` | `891 -> 891` | `0` |
| **word** | Compact | `153 -> 153` | `31 -> 31` | `227 -> 227` | `457 -> 457` | `1096 -> 1096` | `0` |
| **word** | Large | `139 -> 43` | `571 -> 491` | `736 -> 665` | `808 -> 737` | `829 -> 803` | `-344k` |
| **char** | Standard | `19 -> 19` | `400 -> 400` | `604 -> 604` | `580 -> 580` | `671 -> 671` | `0` |
| **char** | Compact | `153 -> 153` | `409 -> 409` | `547 -> 547` | `470 -> 470` | `478 -> 478` | `0` |
| **char** | Large | `139 -> 43` | `487 -> 448` | `572 -> 527` | `514 -> 471` | `659 -> 628` | `-255k` |

- **Standard**: `4,871,548 -> 4,578,050` (`-293,498` px)
- **Compact**: `5,903,914 -> 5,831,191` (`-72,723` px)
- **Large**: `6,909,148 -> 5,507,764` (`-1,401,384` px)
- **GRAND TOTAL**: **`17,684,610 -> 15,917,005` (`-1,767,605` px vs `v1.11.16`; `-10,390,433` px / `-39.5%` vs `v1.11.14`)** — **0 cells worsened across all 60 runs**.

## 3. Geometry Model & Horizontal Offset Cause
- **Body & Heading Pitch**: Device body pitch is an exact integer (`K_mean` over long-range band tops = `1.35827, 1.51473, 1.64191, 2.31218, 2.97723`; `LINE_SPACING_RATIOS = (1.353, 1.510, 1.635, 2.318, 2.977)` reproduces all 30/30 body and `h1` heading pitches exactly). Multi-line `h1` bottom margin uses `round(0.652 * (pitch_fl / 1.2)) + 1`.
- **Page-3 Constant Horizontal Offset (S2)**: All 11 constant-`dX0` pages (`-28 px` Standard, `-24 px` Compact, `-31 px` Large = exact width of 1 digit) were `<ol>` spillover pages starting with a 2-digit item (`10.`..`17.`). Shifting page-top spillover 2-digit `<ol>` items by `(_w_cur - _w_one) / 64.0` right after `new_page()` eliminated the offset across all 11 pages.
- **Link Underline Residual (S3)**: Remaining `19,270` px on `Standard line 1 / para 1..5` and `21,439` px on `Large line 1 p2` are 100% subpixel `link_underline` vertical offsets (`+0.70..+1.07 px` vs integer baseline).

## 4. Learned Acceptance Region
- **Word (`word_spacing_step >= 2`)**: Total-fit KP with `max_sh = G * (0.099 if ragged else 0.179) * max(0.10, 1.0 - 3.27 * extra_word_em)` (`0.28×` step 2, `0.10×` steps 3–5) and `s0 = (slack / G) * 2.0` (hard stretch limits and px-slack both regressed across themes).
- **Char (`char_spacing_step >= 2`)**: `char_spacing_step_em = 0.056` confirmed as sharp global minimum on all 3 themes independently (`Standard`, `Compact`, `Large`), with `char_spacing_shrink_mult = 0.80`.

## 5. Kept / Reverted Experiments
- **KEPT**: S1b (`heading_line_spacing_mb_em = 0.652` for `len(lines) >= 2`: `~-1.45M` px), S2 (spillover 2-digit `<ol>` shift: `~-320k` px).
- **REVERTED**: Unconditional S1b (hurt 1-line `Contents` on `Large p2` `+927k`), S4 hard stretch limits (`+289k..+1.98M`) and px-slack (`+79k..+638k`).

## 6. Remaining Worst 5 Pages Per Variable (Side-by-Side PNGs in `docs/hypotheses/spacing_fit3/`)
- **line**: `Com s3 p3 (156,533)`, `Com s3 p5 (145,464)`, `Com s3 p4 (111,752)`, `Com s2 p4 (111,752)`, `Com s1 p4 (111,752)` — `Compact p4` has 1-line break/justification drift (`dx0 = ±2 px`) and `Compact s3` has `1 px` `h1` `mt` offset.
- **paragraph**: `Com s5 p5 (111,752)`, `Com s4 p5 (111,752)`, `Com s3 p5 (111,752)`, `Com s2 p4 (111,752)`, `Com s1 p4 (111,752)` — identical inherited `Compact` body page `111,752` diff (Standard paragraph steps 1..5 are all `19k` underline-only!).
- **word**: `Com s5 p4 (431,441)`, `Sta s5 p4 (400,969)`, `Com s5 p3 (392,683)`, `Lar s3 p5 (358,322)`, `Lar s4 p5 (348,598)` — high-step stretch-vs-hyphenation break differences.
- **char**: `Lar s5 p5 (288,283)`, `Sta s5 p5 (285,980)`, `Com s5 p4 (248,066)`, `Lar s3 p5 (246,009)`, `Sta s3 p4 (241,255)` — ligature disabling (`fi/fl`) + high-step tracking break differences.

## 7. Gate Results (`KINDLE_RENDER_STRICT_HARFBUZZ=1`, HarfBuzz `6.0.0`)
- **Unit gates**: `check_imports` PASS, `test_harfbuzz_lock` (`6.0.0`) PASS, `test_bugfixes` PASS.
- **Size-notch smoke**: All 8 sizes (`34..55 px`) × line steps `1 & 5` PASS.
- **Goldens (`18/18` PASS, 100% bit-identical to `v1.11.16`, 0 golden updates)**: `probe`, `exam1`, `exam2`, `exam3_normal`, `exam3_small`, `e3_compact`, `e3_large`, `tables_images` (44p, 3-theme total `24,122,051`), `ti_compact` (35p), `ti_large` (57p), `sizes_00..sizes_07` (8/8).
