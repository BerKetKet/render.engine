# `kindle_render` v1.11.19 Report — Direct Line-Break Fitting (`spacing_fit5`)

## 1. Interpretation Choices
- **Autonomous defaults**: Followed all ground rules under `KINDLE_RENDER_STRICT_HARFBUZZ=1` (HarfBuzz `6.0.0`).
- **Dual metrics**: Added paragraph-level **LBA** (Line-Break Agreement against `docs/data/device_lines.jsonl`, 2,064 extracted device lines) and page-level **PAG** (Page-Start Agreement across all 240 pages) alongside the 60-run pixel diff metric (`pages 2–5`).
- **Default gating**: Neither kept improvement justifies altering default step-1 goldens (`word_spacing_hyph_k = 1.0` applies when `word_spacing_step > 1`; synthetic hyphen tracking subtraction applies when `cfg.user_char_spacing_26() > 0`). All **18/18 default goldens** remain 100% bit-identical to `v1.11.18`.

## 2. LBA / PAG & 60-Run Pixel Diff — Before (`v1.11.18`) vs After (`v1.11.19`)

| Metric / Theme | `v1.11.18` | `v1.11.19` | Delta |
| :--- | ---: | ---: | ---: |
| **Pixel Diff — Standard (20 runs, p2–5)** | 4,290,767 | **4,286,877** | **-3,890** |
| **Pixel Diff — Compact (20 runs, p2–5)** | 4,591,765 | **4,589,786** | **-1,979** |
| **Pixel Diff — Large (20 runs, p2–5)** | 5,211,916 | **5,175,484** | **-36,432** |
| **Pixel Diff — GRAND TOTAL (60 runs)** | **14,094,448** | **14,052,147** | **-42,301** (`-12,255,291` / `-46.6%` vs `v1.11.14`) |
| **LBA — `word 1..5` (15 cells)** | 505 / 1,039 (48.60%) | **509 / 1,039 (48.99%)** | **+4 lines** (`Compact.word2 +2`, `Large.word3 +2`) |
| **LBA — `char 1..5` (15 cells)** | 245 / 1,009 (24.28%) | 245 / 1,009 (24.28%) | 0 lines (`-9,997` px across 12/12 `char 2..5` cells) |
| **PAG — All 240 pages (`v18` baseline)** | 222 / 240 (92.5%) | — | `line 58/60`, `para 58/60`, `char 57/60`, `word 49/60` |
| **Cells worsened (> 0 px)** | — | **0 / 60** | Zero regressions |

## 3. Fitted Model, Parameters & Sensitivity
- **`Config.word_spacing_hyph_k: float = 1.0`** (`kindle_render/config.py`, `kindle_render/layout.py`):
  - When `word_spacing_step > 1`, `break_kp` scales consecutive/window hyphenation penalties by `word_spacing_hyph_k = 1.0` instead of `1.5`.
  - **Sensitivity (3-theme `word 2..5`, base `6,432,289`)**: `0.0 -> 6,597,305 (+165k)`, `0.5 -> 6,495,897 (+64k)`, **`1.0 -> 6,399,985 (-32,304)`**, `1.5 -> 6,432,289 (0)`, `2.5 -> 6,682,918 (+251k)`. Clear interior optimum at `1.0`.
  - Other `break_kp` knobs (`line_penalty` `1.0/3.0`, `window_weight` `0.5`, `stretch_k` `1.5/3.0`) were neutral (`0`) or regressed (`+19k` to `+295k`).
- **Tracked synthetic hyphen placement (`kindle_render/layout.py`, S6b)**:
  - In `layout_line`, when `hy` is emitted and `cfg.user_char_spacing_26() > 0`, `pen -= cfg.user_char_spacing_26()` removes the spurious trailing tracking advance before the synthetic hyphen `"-"` without altering `nat` or `Penalty.width` (`hw`). Improves all 12/12 `char 2..5` cells (`-9,997` px total).
- **S3(e) width-domain verification**: Confirmed device breaks using widened word/char widths (not step-1 widths stretched post-break).

## 4. Pagination Rule (S4)
- Across all 240 pages, baseline PAG is `96.7%` (`58/60`) on `line` and `paragraph` and `95.0%` (`57/60`) on `char`.
- The remaining `11/60` mismatches in `word` (`49/60 = 81.7%`) occur at wide `word` steps `3–5` where upstream paragraph line counts differ by `±1` line and shift page boundaries—not from an independent widow/orphan pagination rule defect. No pagination rule override was added.

## 5. S8 Default-Case Dividend
- Neither `word_spacing_hyph_k = 1.0` nor tracked hyphen shift alters default step-1 renders (`word_spacing_step` is `None`/1 and `user_char_spacing_26() == 0`).
- All **18/18 default goldens** (`probe`, `exam1` 99.10% / `1,465,320`, `exam2` 99.32%, `exam3_normal`, `exam3_small`, `e3_compact`, `e3_large`, `tables_images` 44p / `ti_compact` 35p / `ti_large` 57p with 3-theme total `24,122,051`, `sizes_00..sizes_07`) remain **100% bit-identical** to `v1.11.18`. No goldens regenerated.

## 6. Kept & Reverted Experiments (Full Log in `docs/hypotheses/spacing_fit5.md`)
- **KEPT**:
  - `word_spacing_hyph_k = 1.0` (`word_spacing_step > 1`): `-32,304` px (`6,432,289 -> 6,399,985`, `Large word 3 p3: 32,304 -> 0`, LBA `+4`, 0 regressions).
  - S6b synthetic hyphen tracking subtraction (`pen -= user_char_spacing_26()` in `layout_line`): `-9,997` px (`5,914,910 -> 5,904,913`, 12/12 `char 2..5` cells improved, 0 regressions).
- **REVERTED**:
  - S6a (`+extra_track26` on `Penalty.width` `hw`): `+1,334,091` px (`5,914,910 -> 7,249,001`).
  - `word_spacing_hyph_k` at `0.0` (`+165,016`), `0.5` (`+63,608`), `2.5` (`+250,629`).
  - `char` `hyph_k` at `0.5` (`+70,509`), `1.0` (`0`), `2.0` (`+87,740`).
  - `line_penalty` `1.0`/`3.0` (`0`), `window_weight` `0.5` (`0`), `stretch_k` `1.5` (`+295,033`) / `3.0` (`+19,204`).
  - S7 `h1` `mt` `0.045` audit: residuals `Std [0,0,0,-1,+2]`, `Cmp [0,+1,+1,0,+2]`, `Lrg [0,0,-1,0,+1]` px — Pareto-optimal, kept as-is.

## 7. Worst 5 Pages Per Variable (`v1.11.19`) & Hyphenation Dictionary Audit
- **`line`**: `Com s3 p3=156,533`, `Com s3 p5=145,464`, `Com s4 p3=91,762`, `Lar s3 p3=89,507`, `Com s5 p4=74,175`
- **`paragraph`**: `Lar s3 p5=31,369`, `Com s1 p5=29,317`, `Lar s4 p5=21,397`, `Lar s2 p4=21,397`, `Lar s1 p3=21,397`
- **`word`**: `Com s5 p4=431,441`, `Sta s5 p4=400,969`, `Com s5 p3=392,683`, `Lar s3 p5=358,810`, `Lar s4 p5=348,598`
- **`char`**: `Sta s5 p5=285,619`, `Lar s5 p5=265,382`, `Com s5 p4=249,417`, `Lar s3 p5=246,162`, `Com s4 p4=237,454`
- **Hyphenation dictionary audit**: All target device hyphenation points (`fu-neral`, `mis-un-der-stood`, `great-est`, `fea-tures`, `ar-range-ment`, `fam-ily`) are already present in `hyph_en_YJ.bin`.
- Side-by-side worst-page visual diagnostics saved under `docs/hypotheses/spacing_fit5/`.

## 8. Gate Results (`KINDLE_RENDER_STRICT_HARFBUZZ=1`)
- `tools/check_imports.py`: **PASS** (`errors=0`)
- `tools/test_harfbuzz_lock.py`: **PASS** (`version=6.0.0`, `locked=6.0.0`)
- `tools/test_bugfixes.py`: **PASS** (`ALL BUGFIX TESTS PASSED`)
- `tools/corpus.py --golden-only` (all **18/18** corpora: `probe`, `exam1`, `exam2`, `exam3_normal`, `exam3_small`, `e3_compact`, `e3_large`, `tables_images`, `ti_compact`, `ti_large`, `sizes_00..sizes_07`): **18/18 PASS** (`golden_passed=True`, `layout_golden_passed=True`, `deterministic=True` on `probe`).

## 9. Overlay Contents & Checksums
See `GATES.txt`, `VERSION.txt`, `DELETIONS.txt`, `COMMIT_MESSAGE.txt`, and the overlay manifest in `1.11.19_overlay_spacing5.zip`.
