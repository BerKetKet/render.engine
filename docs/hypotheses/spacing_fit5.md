# Spacing Fit v5 (`v1.11.19`) — Direct Line-Break Cost Fitting, LBA/PAG Ground Truth & Tracked Hyphen Placement

**Base**: `v1.11.18` (commit `589f38a`, 60-run spacing grand total **`14,094,448`** diff px across pages 2–5).  
**Result**: `v1.11.19` — 60-run spacing grand total **`14,052,147`** diff px (**`-42,301` px** vs `v1.11.18`; **`-12,255,291` px / `-46.6%`** vs `v1.11.14` `26,307,438`), **`0` cells worsened** across all 60 runs, **`18/18` default goldens 100% bit-identical** to `v1.11.18` under `KINDLE_RENDER_STRICT_HARFBUZZ=1`.

---

## 0. Interpretation Choices
- **Primary metrics**: Both **LBA** (paragraph-level Line-Break Agreement on `docs/data/device_lines.jsonl`, independent of pagination) and **PAG** (page-start agreement across all 240 pages of the 60 spacing runs) are measured alongside the 60-run pixel diff metric (`pages 2–5`).
- **Default renders**: No default-affecting change improved the 18-corpus aggregate without risking exact pages, so both kept changes are gated cleanly:
  1. `word_spacing_hyph_k = 1.0` (down from `1.5`) is gated on `word_spacing_step > 1`.
  2. Synthetic hyphen tracking compensation (`pen -= cfg.user_char_spacing_26()`) is gated on `cfg.user_char_spacing_26() > 0` (`char_spacing_step > 1`).
  All 18 default goldens (`probe`, `exam1`, `exam2`, `exam3_normal`, `exam3_small`, `e3_compact`, `e3_large`, `tables_images`, `ti_compact`, `ti_large`, `sizes_00..sizes_07`) remain 100% bit-identical to `v1.11.18`.

---

## 1. S1 — Device Line-Break Ground Truth (`device_lines.jsonl`), Baseline LBA & PAG

Built `tools/lab_spacing/extract_device_lines.py` to extract horizontal ink blobs and align body lines directly to EPUB tokens on `data/spacing_caps/` + `exam/v2/kindle_exam_v2.epub` without rasterizing the engine:
- Output: `docs/data/device_lines.jsonl` (**2,064** aligned device lines across all 30 `word`/`char` cells) and `docs/data/lba_baseline_1_11_18.json` / `docs/data/lba_v1_11_19.json`.
- **PAG (Page-Start Agreement across all 240 pages, `v1.11.18` baseline)**:
  - `line`: **58/60 (96.7%)**
  - `paragraph`: **58/60 (96.7%)**
  - `char`: **57/60 (95.0%)**
  - `word`: **49/60 (81.7%)**
  - **Total PAG**: **222/240 (92.5%)** — confirming that pagination mismatches are concentrated in wide `word` spacing (`steps 3–5`).

### Baseline (`v1.11.18`) vs Final (`v1.11.19`) LBA (30 `word`/`char` Cells)

| Theme | Variable | Step 1 | Step 2 | Step 3 | Step 4 | Step 5 | Total (`v18 -> v19`) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Standard | word | 45/63 (71.4%) | 36/69 (52.2%) | 37/74 (50.0%) | 31/79 (39.2%) | 29/83 (34.9%) | 178/368 -> 178/368 |
| Compact | word | 31/51 (60.8%) | **39 -> 41/56 (73.2%)** | 29/59 (49.2%) | 38/63 (60.3%) | 17/66 (25.8%) | 154/295 -> **156/295 (+2)** |
| Large | word | 49/77 (63.6%) | 22/75 (29.3%) | **45 -> 47/76 (61.8%)** | 30/74 (40.5%) | 27/74 (36.5%) | 173/376 -> **175/376 (+2)** |
| **All 3** | **word** | **125/191** | **97 -> 99/200** | **111 -> 113/209** | **99/216** | **73/223** | **505/1039 (48.60%) -> 509/1039 (48.99%) (+4)** |
| Standard | char | 45/63 (71.4%) | 13/69 (18.8%) | 3/72 (4.2%) | 5/76 (6.6%) | 2/77 (2.6%) | 68/357 -> 68/357 |
| Compact | char | 31/51 (60.8%) | 19/56 (33.9%) | 8/59 (13.6%) | 7/62 (11.3%) | 1/66 (1.5%) | 66/294 -> 66/294 |
| Large | char | 49/77 (63.6%) | 43/76 (56.6%) | 11/71 (15.5%) | 3/68 (4.4%) | 5/66 (7.6%) | 111/358 -> 111/358 |
| **All 3** | **char** | **125/191** | **75/201** | **22/202** | **15/206** | **8/209** | **245/1009 (24.28%) -> 245/1009 (24.28%) (0)** |

---

## 2. S2 — Fast Zero-Raster Harness (`break_lab.py`) & Hyphenation Dictionary Audit

- Built `tools/lab_spacing/break_lab.py` exposing `break_kp_param` with all cost-model knobs (`g_frac`, `sh_mult`, `str_k`, `sh_k`, `hyph_k`, `linep`, `win`).
- **Hyphenation dictionary audit (`hyph_en_YJ.bin`)**: Verified that every device hyphenation point observed in `v1.11.18` analysis (`fu-neral`, `mis-un-der-stood`, `great-est`, `fea-tures`, `ar-range-ment`, `fam-ily`) is already present in `hyph_en_YJ.bin`. The remaining break divergences at wide word/char spacing are therefore purely cost-model / glue-width / pagination effects, not missing dictionary patterns.

---

## 3. S3 — Direct Cost-Model Sweep (Word 2..5 & S3(e) Width-Domain Check)

- **S3(e) width-domain check**: Confirmed the device breaks paragraphs using **widened** word/character widths (not base step-1 widths stretched afterwards).
- **Knob sweep on 3-theme `word 2..5` (12 runs, `v1.11.18` baseline = `6,432,289` diff px)**:

| Experiment | Parameter / Variant | 3-Theme `word 2..5` Diff Px | Delta vs Base | Decision |
| :--- | :--- | ---: | ---: | :--- |
| Baseline | `v1.11.18` (`hyph_k=1.5`, `str_k=2.0`, `linep=2.0`, `win=1.0`) | `6,432,289` | `0` | base |
| S3-hyph0.0 | `word_spacing_hyph_k = 0.0` | `6,597,305` | `+165,016` | REVERTED (over-hyphenates) |
| S3-hyph0.5 | `word_spacing_hyph_k = 0.5` | `6,495,897` | `+63,608` | REVERTED |
| **S3-hyph1.0** | **`word_spacing_hyph_k = 1.0`** | **`6,399,985`** | **`-32,304`** | **KEPT** (`Large word 3 p3: 32,304 -> 0`, `0` regressions) |
| S3-hyph2.5 | `word_spacing_hyph_k = 2.5` | `6,682,918` | `+250,629` | REVERTED (under-hyphenates) |
| S3-linep1.0 | `line_penalty = 1.0` | `6,432,289` | `0` | REVERTED (neutral) |
| S3-linep3.0 | `line_penalty = 3.0` | `6,432,289` | `0` | REVERTED (neutral) |
| S3-win0.5 | `window_weight = 0.5` | `6,432,289` | `0` | REVERTED (neutral) |
| S3-strk1.5 | `stretch_k = 1.5` | `6,727,322` | `+295,033` | REVERTED |
| S3-strk3.0 | `stretch_k = 3.0` | `6,451,493` | `+19,204` | REVERTED |

- **Why `word_spacing_hyph_k = 1.0` works**: At wide word spacing (`word_spacing_step > 1`), natural space widths grow while stretch capacity stays tight; lowering the consecutive/window hyphen penalty multiplier from `1.5` to `1.0` brings the hyphenation threshold closer to the device without triggering over-hyphenation (`0.5` and `0.0` both regress). It improves LBA on both Compact (`word 2: +2`) and Large (`word 3: +2`), drops `Large word 3 p3` to `0` (`-32,304` px), and causes zero regressions on Standard or Compact.

---

## 4. S4 — Pagination & S6 — Tracked Synthetic Hyphen Placement (`char 2..5`)

- **S4 Pagination audit**: PAG is already `96.7%` on `line`/`paragraph` and `95.0%` on `char`; the `11/60` mismatches in `word` occur at `steps 3–5` where upstream paragraph line-count differences (`±1` line) shift the page break rather than a standalone widow/orphan rule bug. No artificial pagination override was added.
- **S6 Tracked synthetic hyphen bug**:
  - Inspecting `Standard char 5 p3 L00` ink blobs showed device hyphen placement at `[(945, 972), (976, 988)]` vs engine `[(945, 972), (986, 998)]` — the engine inserted an extra `+10 px` (`user_char_spacing_26()`) gap *before* the synthetic hyphen `"-"` because the trailing letter's advance already included `user_char_spacing_26()`.
  - **S6a (REVERTED)**: Adding `+extra_track26` to `Penalty.width` (`hw`) regressed 3-theme `char 2..5` by **`+1,334,091` px** (`5,914,910 -> 7,249,001`) because `break_kp` saw every hyphenated line `+10 px` wider and rejected valid breaks.
  - **S6b (KEPT)**: Subtracting `cfg.user_char_spacing_26()` from `pen` immediately before emitting `hy.glyphs` in `layout_line` (leaving `nat`/`hw` untouched) improved **12/12 `char 2..5` cells** by **`-9,997` px** (`5,914,910 -> 5,904,913`, zero regressions).
- **S6 `char` `hyph_k` sweep (3-theme `char 2..5`, post-S6b base = `5,904,913`)**:
  - `hyph_k = 0.5`: `5,975,422` (`+70,509`, REVERTED)
  - `hyph_k = 1.0`: `5,904,913` (`0`, neutral — not enabled for `char`)
  - `hyph_k = 1.5`: `5,904,913` (`0`, base)
  - `hyph_k = 2.0`: `5,992,653` (`+87,740`, REVERTED)

---

## 5. S7 — Residual `h1` `mt` Geometry Audit (`line 1..5`)

Audited `h1` top-margin (`mt`) residuals across all 15 `line` runs:
- Standard (`steps 1..5`): `[0, 0, 0, -1, +2]` px
- Compact (`steps 1..5`): `[0, +1, +1, 0, +2]` px
- Large (`steps 1..5`): `[0, 0, -1, 0, +1]` px
- Confirmed the existing `0.045` multiplier is Pareto-optimal across Compact and Large step 3 (`±1 px` trade-off); no change needed.

---

## 6. Final 60-Run Pixel Diff Summary (`v1.11.18 -> v1.11.19`, Pages 2–5)

| Theme | Variable | Step 1 | Step 2 | Step 3 | Step 4 | Step 5 | Theme Total (`v18 -> v19`) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Standard | line | 9,590 | 0 | 9,666 | 110,241 | 35,652 | |
| Standard | paragraph | 9,590 | 9,590 | 9,586 | 9,584 | 9,581 | |
| Standard | word | 9,590 | 60,146 | 583,090 | 446,452 | 880,352 | |
| Standard | char | 9,590 | 380,920 | 493,625 | 559,783 | 650,249 | **4,290,767 -> 4,286,877 (-3,890)** |
| Compact | line | 41,240 | 63,409 | 358,874 | 137,528 | 114,616 | |
| Compact | paragraph | 41,240 | 11,923 | 11,564 | 11,299 | 11,898 | |
| Compact | word | 41,240 | 31,260 | 227,257 | 457,433 | 1,095,905 | |
| Compact | char | 41,240 | 408,643 | 532,194 | 470,724 | 480,299 | **4,591,765 -> 4,589,786 (-1,979)** |
| Large | line | 32,090 | 32,007 | 182,800 | 116,910 | 31,528 | |
| Large | paragraph | 32,090 | 34,337 | 46,855 | 38,201 | 17,920 | |
| Large | word | 32,090 | 480,190 | **621,940** | 725,294 | 790,666 | |
| Large | char | 32,090 | 377,210 | 510,559 | 455,526 | 585,181 | **5,211,916 -> 5,175,484 (-36,432)** |
| **GRAND TOTAL** | **All 60** | | | | | | **14,094,448 -> 14,052,147 (-42,301)** |

- **Cells worsened**: **0 / 60**.
- **Worst 5 pages per variable (`v1.11.19`)** (side-by-side PNGs saved in `docs/hypotheses/spacing_fit5/`):
  - `line`: `Com s3 p3=156,533`, `Com s3 p5=145,464`, `Com s4 p3=91,762`, `Lar s3 p3=89,507`, `Com s5 p4=74,175`
  - `paragraph`: `Lar s3 p5=31,369`, `Com s1 p5=29,317`, `Lar s4 p5=21,397`, `Lar s2 p4=21,397`, `Lar s1 p3=21,397`
  - `word`: `Com s5 p4=431,441`, `Sta s5 p4=400,969`, `Com s5 p3=392,683`, `Lar s3 p5=358,810`, `Lar s4 p5=348,598`
  - `char`: `Sta s5 p5=285,619`, `Lar s5 p5=265,382`, `Com s5 p4=249,417`, `Lar s3 p5=246,162`, `Com s4 p4=237,454`
