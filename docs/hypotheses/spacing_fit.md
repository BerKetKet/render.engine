# Spacing Settings Device Fit — Experiments & Results (`v1.11.15`)

All runs measured under `KINDLE_RENDER_STRICT_HARFBUZZ=1` (HarfBuzz `6.0.0`) via `tools/lab_spacing/score_spacing.py` against `data/spacing_caps` (`theme_Standard`, `theme_Compact`, `theme_Large`, `kindle_exam_v2.epub`, pages 2–5 summed; page 1 title page ignored).

## S0 Baseline (`v1.11.14`) vs Final (`v1.11.15`)

- **S0 Baseline (`v1.11.14`)**: Standard `8,838,367`, Compact `7,715,466`, Large `9,753,605`, **GRAND TOTAL `26,307,438`**.
- **Final (`v1.11.15`)**: Standard `7,584,793` (`-1,253,574`), Compact `6,534,794` (`-1,180,672`), Large `6,909,148` (`-2,844,457`), **GRAND TOTAL `21,028,735` (`-5,278,703` px, `-20.1%`)**.

## Experiment Log (S0–S8)

| ID | Description | Key Result | Verdict |
| :--- | :--- | :--- | :--- |
| **S0** | Clean `v1.11.14` baseline across 60 runs | `26,307,438` (`Std 8.84M`, `Cmp 7.72M`, `Lrg 9.75M`) | Baseline |
| **S1** | Exact `LINE_SPACING_RATIOS = (1.353, 1.510, 1.635, 2.318, 2.977)` + `raw_pitch_px()` integer `pitch_fl = float(round(2*raw_pitch))` (30/30 body & heading pitches exact) + `heading_line_spacing_lead_k = 0.045` (gated on `line_spacing_step is not None and pitch == 0`) | `line` 3-theme total: `3,774,800 -> 2,454,789` (**`-1,320,011` px**); also improved `Large` step-1 across all 4 vars (`306k -> 139k` each). Variant with `min(extra_lead, 0.30*size_px)` gave `3,204,229` (worse by `+749k`, reverted). | **KEPT** (`0.045`) |
| **S2** | Swept `CHAR_SPACING_STEP_EM` `0.048..0.058` in `0.001` steps on Standard char 2..5: sharp V-minimum at `0.056` (`3,075,963` vs `0.055: 3,610,786`, `0.057: 3,178,514`). Measured TOC 13-glyph underline (`"X01 Victorian"`): `ol_number` marker (`"1."`) is tracked (`+trk`), text shifts right by `+trk` (marker start anchored to base `left_em`), and link underline trims trailing `trk` (`-trk`). | Standard char 2..5: `3,075,963 -> 2,864,755` (**`-211,208` px**); ~`-500k` across all 3 themes. | **KEPT** |
| **S3** | Verified paragraph spacing `(step - 1) * size_px` on all 3 themes × steps 1..5. Confirmed Compact step 5 (`p4 diff=0`, TOC `dy=209`) and Large step 4 (`p2/p3/p4` deltas match to 0–1 px) already match; earlier `122`/`106` readings were TOC-wrap band-mixing artifacts. | No code change needed; `(step - 1) * size_px` verified exact. | **VERIFIED** |
| **S4** | Swept `break_kp` variants (a)–(f) on Standard word 2..5 (`base 3,245,185`): (a) `max_sh` mult `0.0 -> 2,861,489`, `0.05 -> 2,722,384`, **`0.10 -> 2,637,178`**, `0.20 -> 2,701,639`, `0.50 -> 3,083,495`; (b) real glue `G` `0.5 -> 3,722,503`, `1.0 -> 3,858,426` (worse); (c) `G_real + sh_base -> 3,321,102` (worse); (d) `win 0.6..1.4 -> 3,245,185` (0 effect), `hyph 0.5 -> 3,322,195` (worse), `hyph 3.0 -> 3,241,867` (noise); (f) `g1+shm0 -> 3,006,971` (worse than `shm=0.10`); `STRK` `1.0/1.5 -> 2.87M/2.76M` (worse), `2.0/3.0/4.0 -> 2,637,178`. Confirmed across all 3 themes (word 2..5): `1.0 -> 9,175,632`, `0.0 -> 8,268,205`, **`0.10 -> 8,027,112`** (`-1,148,520`), `0.15 -> 8,295,325`, `0.20 -> 8,349,448`. | **`word_spacing_shrink_mult = 0.10`** (`-1,148,520` px across all 3 themes); all other variants reverted. | **KEPT** (`0.10`) |
| **S5** | Swept `max_sh` mult on all 3 themes × char 2..5: `1.0 -> 7,146,759`, `0.0 -> 7,870,895` (`+724k` worse), `0.1 -> 7,889,305` (`+742k` worse), `0.5 -> 7,257,833`, **`0.7 -> 6,963,169`** (`-183,590`). Standard hyphen penalty `0.5/3.0` regressed (`2.92M/2.99M`). | **`char_spacing_shrink_mult = 0.70`** (`-183,590` px across all 3 themes). | **KEPT** (`0.70`) |
| **S6** | Combined `word+char` smoke test (`word=3+char=3`, `word=5+char=5`) on `kindle_exam_v2.epub`. | Renders cleanly with `min(word_mult, char_mult)`. | **PASS** |
| **S7** | Exposed named `Config` fields (`word_spacing_step_em`, `char_spacing_step_em`, `word_spacing_shrink_mult`, `char_spacing_shrink_mult`, `heading_line_spacing_lead_k`); saved `docs/data/spacing_measurements.json` and worst-page side-by-side PNGs (`docs/hypotheses/spacing_fit/worst_*.png`). | Zero magic literals; all temporary env hooks removed. | **DONE** |
| **S8** | Full regression gate under `KINDLE_RENDER_STRICT_HARFBUZZ=1`. | `18/18` goldens bit-identical to `v1.11.14` (0 golden updates), `check_imports`/`test_harfbuzz_lock`/`test_bugfixes` PASS. | **PASS** |

## Open Items & Hypotheses
- **Step-1 1 px vertical offset on Standard (`p2/p3`)**: Standard `line=1` (`pitch=61`, `extra_lead=0`) still sits `1 px` above capture on `Contents`/`X01` (`mt = round(67.1) = 67` vs `68`), while Compact (`53`) and Large (`68`) are `0 px` — likely a subpixel half-leading rounding detail on `h1` when `extra_lead == 0`.
- **Remaining word/char line-break diffs at steps 3–5** (see `docs/hypotheses/spacing_fit/worst_word_Std_w5_p4.png` and `worst_char_Std_c5_p5.png`): Even with `word_spacing_shrink_mult = 0.10`, high-step word/char runs still differ on a handful of paragraph break choices (e.g. Standard word 5 p4, char 5 p5), pointing to a secondary stretch-vs-hyphenation weighting when slack exceeds `0.5 * L`.
