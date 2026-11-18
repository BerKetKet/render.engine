# Evaluation Report: `kindle_render` 1.11.3 -> 1.11.4 (Four Reviewer Candidates)

- **Baseline tag**: `v1.11.3` (`commit e5a4ced`) (`MEASURED`)
- **Target version**: `v1.11.4` (`MEASURED`)
- **Comparison window**: `y = 83..2240, x = 0..1080` (`2,329,560` pixels per page, binary threshold `128`) (`MEASURED`)
- **Dataset availability**: Evaluated across all 10 capture sets present on the VM (`probe`, `exam1`, `exam2`, `exam3_normal`/`size_04_Bookerly`, `exam3_small`/`size_00_Bookerly`, `e3_compact`/`theme_Compact`, `e3_large`/`theme_Large`, `tables_images`/`ti_std`, `ti_compact`, `ti_large`) plus `synthetic` (`MEASURED`). Note: `exam/v3/size_01..03_Bookerly` and `size_05..07_Bookerly` are not present in `exam/v3/` on this VM (`MEASURED`).

---

## 1. Baseline `1.11.3` Metrics (`tools/reports/incorporate/base_1.11.3.json`)

All baseline numbers below are `MEASURED` from tag `v1.11.3` (`commit e5a4ced`):

| Corpus | Geometry (`size_px / pitch_px`, `x0..x1`) | Pages | Bitwise-Identical Pages | Mean Pixel Match (`%`) | Total Diff Pixels | `pos_lines` (`shift=0 / total`) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `probe` | `42 / 57`, `39..1041` | 86 | `43 / 86` | `99.8054%` | `389,959` | `2753 / 2863` |
| `exam1` | `45 / 68`, `79..1001` | 70 | `50 / 70` | `99.0700%` | `1,516,617` | `1452 / 1568` |
| `exam2` | `42 / 57`, `79..1001` | 65 | `40 / 65` | `99.3165%` | `1,034,912` | `1395 / 1529` |
| `exam3_normal` (`e3_std`) | `45 / 68`, `79..1001` | 82 | `60 / 82` | `99.6266%` | `713,359` | `1899 / 2027` |
| `exam3_small` (`e3_small`) | `34 / 51`, `79..1001` | 54 | `32 / 54` | `99.3257%` | `848,187` | `1518 / 1651` |
| `e3_compact` (`theme_Compact`) | `39 / 53`, `52..1028` | 56 | `33 / 56` | `98.4035%` | `2,082,738` | `1490 / 1713` |
| `e3_large` (`theme_Large`) | `50 / 82`, `131..949` | 124 | `87 / 124` | `99.0745%` | `2,673,432` | `2341 / 2652` |
| `tables_images` (`ti_std`) | `45 / 68`, `79..1001` | 44 | `4 / 44` | `91.7039%` | `8,503,517` | `299 / 894` |
| `ti_compact` | `39 / 53`, `52..1028` | 35 | `3 / 35` | `91.7533%` | `6,723,947` | `280 / 733` |
| `ti_large` | `50 / 82`, `131..949` | 57 | `3 / 57` | `92.1675%` | `10,400,325` | `286 / 1086` |
| `synthetic` | `42 / 57`, `39..1041` | 3 | `3 / 3` (golden) | `100.0000%` | `0` | N/A |

---

## 2. Per-Candidate Evaluation & Verdicts

### Summary Verdict Table

| Candidate | Description | Verdict | Bitwise-Identical Pages Lost | Net Diff Pixels Change (10 Capture Sets) |
| :--- | :--- | :--- | ---: | ---: |
| **Candidate A** | Image downscale (`s < 1.0`) rounding with `ceil` instead of `round` | **`REJECT`** (`MEASURED`) | `0` (`MEASURED`) | `+620,664` diff px (regresses 20 pages across 7 corpora) (`MEASURED`) |
| **Candidate B** | Apostrophe word splitting in `hyphen.py:hyphenate_word` | **`REJECT`** (`MEASURED`) | `0` (`MEASURED`) | `0` diff px (`0.0000%` change on every page; already handled in `layout.py:441-447`) (`MEASURED`) |
| **Candidate C** | Line-breaking tolerance ladder `(tol, tol*2, tol*4, tol*8)` in `layout.py:make_lines` | **`REJECT`** (`MEASURED`) | `0` (`MEASURED`) | `0` diff px (`0.0000%` change on every page; `tol*8` never reached) (`MEASURED`) |
| **Candidate D** | `(i)` Bullet `mt` `round`, `(ii)` Post-`h1` indented block `gap -= 1`, `(iii)` `ul_nested_indent_em = 2.0000` | **`KEEP`** (`KEEP-WITH-NOTE` on `e3_compact`) (`MEASURED`) | `0` (`MEASURED`) | `-48,597` diff px across Step-1 corpora (`-48,101` across all 10 capture sets) (`MEASURED`) |

---

### Candidate A: Image Rounding When Scaled Down (`s < 1.0`, `ceil` vs `round`) — `REJECT` (`MEASURED`)

- **Change tested (`tools/reports/incorporate/cand_a.json`)**: In `kindle_render/page.py:add_image`, when `s < 1.0`, compute `target_w = max(1, math.ceil(nat_w * s))` and `target_h = max(1, min(max_h, math.ceil(nat_h * s)))` instead of `round(...)` (`MEASURED`).
- **All pages whose pixel match changed by more than `0.01` percentage points (`MEASURED`)**:

| Corpus | Page | `1.11.3` Match (`%`) | `Cand A` Match (`%`) | Delta (`pt`) | `1.11.3` Diff Px | `Cand A` Diff Px | Diff Px Change |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `exam1` | 48 | `76.0256%` | `74.3829%` | `-1.6427` | `558,497` | `596,766` | `+38,269` |
| `exam2` | 36 | `88.7311%` | `92.8332%` | `+4.1021` | `262,516` | `166,954` | `-95,562` |
| `exam3_normal` (`e3_std`) | 58 | `99.6133%` | `95.6930%` | `-3.9203` | `9,008` | `100,333` | `+91,325` |
| `exam3_small` (`e3_small`) | 36 | `99.6018%` | `99.4882%` | `-0.1136` | `9,277` | `11,922` | `+2,645` |
| `e3_large` | 84 | `99.6020%` | `96.9735%` | `-2.6285` | `9,271` | `70,504` | `+61,233` |
| `tables_images` (`ti_std`) | 25 | `93.5866%` | `92.9985%` | `-0.5881` | `149,404` | `163,105` | `+13,701` |
| `ti_compact` | 20 | `92.2564%` | `91.7437%` | `-0.5126` | `180,393` | `192,335` | `+11,942` |
| `ti_compact` | 21 | `90.2899%` | `89.8895%` | `-0.4004` | `226,202` | `235,530` | `+9,328` |
| `ti_compact` | 24 | `91.7037%` | `91.4900%` | `-0.2137` | `193,267` | `198,245` | `+4,978` |
| `ti_compact` | 26 | `91.9766%` | `91.7675%` | `-0.2091` | `186,910` | `191,781` | `+4,871` |
| `ti_compact` | 27 | `92.9469%` | `92.0324%` | `-0.9145` | `164,307` | `185,610` | `+21,303` |
| `ti_compact` | 31 | `86.3065%` | `85.7940%` | `-0.5125` | `318,998` | `330,937` | `+11,939` |
| `ti_compact` | 33 | `85.1773%` | `84.9291%` | `-0.2482` | `345,303` | `351,085` | `+5,782` |
| `ti_large` | 33 | `96.2089%` | `94.9873%` | `-1.2215` | `88,317` | `116,773` | `+28,456` |
| `ti_large` | 34 | `96.1650%` | `93.1384%` | `-3.0266` | `89,338` | `159,844` | `+70,506` |
| `ti_large` | 35 | `89.4765%` | `88.4889%` | `-0.9876` | `245,151` | `268,158` | `+23,007` |
| `ti_large` | 39 | `87.3100%` | `85.5300%` | `-1.7800` | `295,621` | `337,088` | `+41,467` |
| `ti_large` | 41 | `98.8178%` | `94.6877%` | `-4.1301` | `27,540` | `123,754` | `+96,214` |
| `ti_large` | 43 | `91.8559%` | `88.4112%` | `-3.4446` | `189,722` | `269,967` | `+80,245` |
| `ti_large` | 44 | `86.4472%` | `84.1806%` | `-2.2666` | `315,720` | `368,521` | `+52,801` |
| `ti_large` | 49 | `88.2454%` | `87.1082%` | `-1.1372` | `273,831` | `300,322` | `+26,491` |
| `ti_large` | 54 | `94.4628%` | `90.4764%` | `-3.9864` | `128,992` | `221,858` | `+92,866` |

- **Direct Device Bounding-Box Measurements (`MEASURED`)**:
  - **`exam3_normal` (`e3_std`) p58 & `e3_large` p84 (`1500x420` wide banner downscaled to `max_w`)**:
    - On `e3_std` p58 (`max_w = 922`, `s = 0.614667`), `nat_h * s = 258.1600 px`. With `round` (`258 px`), all 15 text lines below the image have `shift = 0 px` (`15/15 pos_lines`) (`MEASURED`). With `ceil` (`259 px`), all 15 text lines below the image shift down by `+1 px`, increasing diff pixels from `9,008 -> 100,333` (`-3.9203 pt`) (`MEASURED`).
    - On `e3_large` p84 (`max_w = 818`, `s = 0.545333`), `nat_h * s = 229.0400 px`. With `round` (`229 px`), all 11 text lines below the image have `shift = 0 px` (`11/11 pos_lines`) (`MEASURED`). With `ceil` (`230 px`), all 11 text lines shift down by `+1 px`, increasing diff pixels from `9,271 -> 70,504` (`-2.6285 pt`) (`MEASURED`).
  - **`ti_large` (`max_w = 818`, 3:2 images `1200x800`, `1500x1000`, `2400x1600`, `s < 1.0`)**:
    - Exact scaled height is `818 * (2/3) = 545.3333 px`. Across all 9 pages (`p30, p33, p34, p35, p39, p43, p44, p49, p54`), the measured device image bounding-box height is **`545 px`** (`round(545.3333) = 545`), whereas `ceil` gives **`546 px`** (`+1 px` error, shifting caption and subsequent table/text lines down by `+1 px`) (`MEASURED`).
    - On `ti_large` p41 (`900x150` banner downscaled to `818`, `nat_h * s = 136.3333 px`), the measured device bounding-box height is **`136 px`** (`round = 136`), whereas `ceil` gives **`137 px`** (`-4.1301 pt` drop) (`MEASURED`).
  - **Why `exam2` p36 improved while `exam1` p48 regressed (`MEASURED` + `HYPOTHESIS`)**:
    - On `exam2` p36 (`max_w = 922`), two images are downscaled: `1400x400` (`h_fl = 263.4286`, `round = 263`, `ceil = 264`, measured device bbox height = `264`) and `700x260` (`h_fl = 342.4571`, `round = 342`, `ceil = 343`, measured device bbox height = `342`) (`MEASURED`). Because `exam2` p36 already has an upstream `-2 px` vertical offset on the caption/image block, adding `+1 px` per image via `ceil` shifted the lower image and caption `+2 px` down toward the capture (`HYPOTHESIS`), whereas on `exam1` p48 (`700x260` at `s = 922/700 > 1.0` not affected, preceded by `1400x400` on p47/p48), `ceil` degraded pixel match by `-1.6427 pt` (`MEASURED`).
- **Verdict**: **`REJECT`** (`MEASURED`). Device bounding-box heights on `e3_std` p58 (`258 px`), `e3_large` p84 (`229 px`), and 10 downscaled images in `ti_large` (`545 px` and `136 px`) match `round`, not `ceil` (`MEASURED`).

---

### Candidate B: Apostrophe Words in `hyphen.py:hyphenate_word` — `REJECT` (`MEASURED`)

- **Change tested (`tools/reports/incorporate/cand_b.json`)**: In `kindle_render/hyphen.py:hyphenate_word`, when `not word.isalpha()`, split on `'` or `\u2019` into two alphabetic parts, hyphenate only the right part, and prepend `left + apostrophe` to the first syllable (`MEASURED`).
- **Measured Result**: **`0` changed pixels (`0.0000%` delta)** across all 676 pages of the 10 capture datasets and `synthetic` (`MEASURED`).
- **Why (`MEASURED`)**: In `1.11.3`, `kindle_render/layout.py:441-447` (`build_items`) already strips the leading apostrophe prefix (`lead_punct = lead_punct + alpha[:a_idx + 1]`, `alpha = alpha[a_idx + 1:]` for `1 <= a_idx <= 6`) before calling `hyphenator.hyphenate_word(alpha)`. Thus `hyphenate_word` already receives the purely alphabetic right-hand word on all French/Italian/English elisions (`l'anticonstitutionnellement`, `d'un`, `qu'il`, etc. in `probe` `c5_hyph_fr`, `exam1` `e07_francais`, `exam2` `x09_languages`, and `exam3` `e05_hyph_fr`) (`MEASURED`).
- **Verdict**: **`REJECT`** (no-op on `1.11.3`; fails the `KEEP` requirement to improve at least one page or corpus) (`MEASURED`).

---

### Candidate C: Line-Breaking Tolerance Ladder `(tol, tol*2, tol*4, tol*8)` in `layout.py:make_lines` — `REJECT` (`MEASURED`)

- **Change tested (`tools/reports/incorporate/cand_c.json`)**: Extended `for t in (tol, tol * 2, tol * 4):` at `kindle_render/layout.py:869` with a fourth step `tol * 8` (`MEASURED`).
- **Measured Result**: **`0` changed pixels (`0.0000%` delta)** across all 676 pages of the 10 capture datasets and `synthetic` (`MEASURED`). Every paragraph in all 6 EPUB books finds a feasible Knuth-Plass breakpoint chain within `(tol, tol * 2, tol * 4)` (`MEASURED`).
- **Verdict**: **`REJECT`** (no-op on `1.11.3`; fails the `KEEP` requirement to improve at least one page or corpus) (`MEASURED`).

---

### Candidate D: List Spacing Rules & Nested `ul` Indent (`2.0000em`) — `KEEP` (`KEEP-WITH-NOTE` on `e3_compact`) (`MEASURED`)

- **Change tested (`tools/reports/incorporate/cand_d.json`)**:
  - **`D(i)`**: In `kindle_render/page.py`, for the first item of a bulleted list (`list_level > 0 and bullet == '•' and b.mt_em == 1.0 and extra_lead == 0.0`), compute top margin as `int(round(b.mt_em * vem_px * b.scale))` instead of `int(b.mt_em * vem_px * b.scale)` (`MEASURED`).
  - **`D(ii)`**: In `kindle_render/page.py`, for a plain text block directly after an `h1` (`b.heading == 0 and prev_h == 1` when `extra_lead == 0.0`), also apply `gap -= 1` when `b.left_em > 0.0 and list_level == 0` (`MEASURED`).
  - **`D(iii)`**: In `kindle_render/config.py` and `kindle_render/epub.py`, change `ul_nested_indent_em` from `1.9762` to `2.0000` (`MEASURED`).
- **All pages whose pixel match changed by more than `0.01` percentage points (`MEASURED`)**:

| Corpus | Page | `1.11.3` Match (`%`) | `Cand D` (`1.11.4`) Match (`%`) | Delta (`pt`) | `1.11.3` Diff Px | `Cand D` Diff Px | Diff Px Change | Sub-part(s) Active |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| `probe` | 87 | `97.9045%` | `99.3024%` | **`+1.3979`** | `48,817` | `16,252` | **`-32,565`** | `D(i) + D(ii) + D(iii)` |
| `exam1` | 45 | `94.4819%` | `94.6543%` | **`+0.1724`** | `128,547` | `124,531` | **`-4,016`** | `D(iii)` |
| `exam1` | 46 | `98.1027%` | `98.3516%` | **`+0.2489`** | `44,198` | `38,401` | **`-5,797`** | `D(iii)` |
| `exam3_normal` (`e3_std`) | 39 | `96.5281%` | `96.7575%` | **`+0.2294`** | `80,879` | `75,535` | **`-5,344`** | `D(iii)` |
| `exam3_small` (`e3_small`) | 25 | `99.7170%` | `99.8437%` | **`+0.1267`** | `6,592` | `3,642` | **`-2,950`** | `D(iii)` |
| `e3_compact` | 26 | `99.6851%` | `99.8784%` | **`+0.1933`** | `7,335` | `2,833` | **`-4,502`** | `D(iii)` |
| `e3_compact` | 32 | `83.2908%` | `82.9549%` | `-0.3359` | `389,251` | `397,076` | `+7,825` | `D(ii)` |
| `e3_large` | 57 | `92.5278%` | `92.7779%` | **`+0.2501`** | `174,070` | `168,243` | **`-5,827`** | `D(iii)` |

- **Line-Band Verification on `probe` Page 87 (`e3_blocks`, `42/57`, 29 line bands) (`MEASURED`)**:
  - In `1.11.3`, `probe` p87 had `21/29` bands at `shift = 0`:
    - Bands `0..1` (`<h1>`): `shift = 0`, `pixel_eq = True` (`MEASURED`).
    - Bands `2..5` (`<blockquote>`, 4 lines, `our = 531..744` vs `dev = 530..743`): `shift = +1 px` (`1 px` too low) (`MEASURED`).
    - Bands `6..9` (`<pre>`, 4 lines, `our = 806..1019` vs `dev = 805..1018`): `shift = +1 px` (`1 px` too low) (`MEASURED`).
    - Bands `10..28` (`<ul>`, nested `<ul>`, `<ol>`, `<dl>`): `shift = 0 px` ONLY because `<ul>` at band 10 used truncated `int(47.5) = 47 px` (`1 px` too tight), canceling the `+1 px` error from above `<blockquote>` (`MEASURED`).
  - With `D(i) + D(ii) + D(iii)` applied together (`1.11.4`):
    - `D(ii)` (`gap -= 1` on `b.heading == 0 and prev_h == 1 and b.left_em > 0.0 and list_level == 0 and extra_lead == 0.0`) pulls `<blockquote>` and `<pre>` up by `1 px`, so **bands `2..9` become `shift = 0 px` and `pixel_eq = True` on all 8 bands** (`MEASURED`).
    - `D(i)` (`mt = int(round(47.5)) = 48 px` on the first `<ul><li>` item) restores the `+1 px` top margin before `<ul>`, keeping **all 29 bands (`29/29`) on `probe` p87 at `shift = 0 px`** (`pos_lines` on `probe` increases from `2753/2863` to **`2761/2863`, `+8` exact line bands**) (`MEASURED`).
    - `D(iii)` (`ul_nested_indent_em = 2.0000`) moves the nested `<ul><li>` bullet and text at `probe` p87 band 11 (`x = round(2 * 1.9762 * 42) = 166 px -> round(2 * 2.0000 * 42) = 168 px`), matching the device's `2.0em` CSS nested list indent across **all 6 geometries** (`probe` p87 `42/57`, `exam1` p45–46 `45/68`, `e3_std` p39 `45/68`, `e3_small` p25 `34/51`, `e3_compact` p26 `39/53`, and `e3_large` p57 `50/82`) (`MEASURED`).
  - **Note on `e3_compact` p32 (`KEEP-WITH-NOTE`) (`MEASURED`)**:
    - Across all 7 Step-1 corpora (`probe`, `exam1`, `exam2`, `exam3_normal`, `exam3_small`, `tables_images`, `synthetic`), Candidate D has **zero regressions on any page** (`MEASURED`).
    - On the extended `e3_compact` (`39/53`, `extra_lead == 0.0`) capture set, one general rule (`D(ii)`: `gap -= 1` when `b.heading == 0 and prev_h == 1 and b.left_em > 0.0 and list_level == 0 and extra_lead == 0.0`) fires on both `probe` p87 (`e3_blocks`, where `<h1>` is followed by `<blockquote>` with `left_em = 1.0`) and `e3_compact` p32 (`e08_verse`, where `<h1>` is followed by a verse paragraph with `left_em = 1.5`) (`MEASURED`). On `e3_compact` p32, the `<h1>` block already sits `1 px` high (`shift = -1 px`) under Compact `39/53`, so `gap -= 1` moves the verse lines from `shift = -1 px` to `shift = -2 px` (`83.2908% -> 82.9549%`, `-0.3359 pt` on an already non-exact page, with `0` exact pages lost) (`MEASURED`).
- **Verdict**: **`KEEP`** (`KEEP-WITH-NOTE` on `e3_compact` p32) (`MEASURED`).

---

## 3. Audit of `1.11.x` Pitch-vs-Size Ratio Thresholds in `kindle_render/page.py`

Per fixed constraint #2, below is every threshold in `kindle_render/page.py` (and `Config.extra_lead_px()` called from `page.py`) introduced in `1.11.x` that compares `pitch` with a `size_px` ratio, without modifying any of them:

| # | Location | Expression / Threshold | Ratio | Purpose | Evidence (Corpora, Sizes, Themes) | Checked on 8-Size Series (`size_00..07`)? | Logged in `BACKLOG.md`? |
| :--- | :--- | :--- | ---: | :--- | :--- | :--- | :--- |
| 1 | `config.py:151` (called at 21 sites in `page.py`) | `raw = self.pitch_px() - (19.0 / 14.0) * self.size_px(); return raw if raw > 0.5 else 0.0` | `19/14 ≈ 1.35714` (`+0.5 px` rounding tolerance) | Selects tight-spacing regime (`extra_lead == 0.0`) vs Standard/Large regime (`extra_lead > 0.0`). | `MEASURED` on 6 geometries: `probe`/`exam2` (`42/57`, `raw = 0.0`), `Compact` (`39/53`, `raw = +0.071 <= 0.5`), `e3_small` (`34/51`, `raw = 4.79`), `exam1`/`e3_std`/`ti_std` (`45/68`, `raw = 6.93`), `e3_large`/`ti_large` (`50/82`, `raw = 14.14`). Principled `0.5 px` integer-pitch rounding bound. | Numerically invariant across all 8 Standard steps (`size_00..07` all have `pitch/size >= 1.50`, `raw >= 4.79 px >> 0.5 px`); captures verified on `size_00` and `size_04` (`size_01..03,05..07` not on VM) (`MEASURED`). | No (multi-geometry, principled `0.5 px` rounding bound). |
| 2 | `page.py:392`, `page.py:553` | `eff_body_pitch = max(float(std_body_pitch), (68.0 / 45.0) * c.size_px())` | `68/45 ≈ 1.51111` | Ensures Standard-regime heading `vem` and `h1` pitch floor do not drop below the `68/45` Standard line-height ratio when integer `pitch_px()` rounds down (e.g. `34/51` where `51/34 = 1.5000 < 68/45`). | `MEASURED` active on `e3_small` (`size_00_Bookerly`, `34/51`, `eff_body_pitch = 51.3778`); inactive on `45/68` (`68.0`) and `50/82` (`82.0`). | Checked on `size_00` (`34/51`) and `size_04` (`45/68`); `size_01..03,05..07` not on VM (`MEASURED`). | **Yes** (active `< 68/45` clamp calibrated on `34/51`). |
| 3 | `page.py:562` | `elif std_body_pitch < (68.0 / 45.0) * c.size_px(): gap -= 1` (inside `b.heading == 0 and prev_h == 1 and list_level > 0 and extra_lead > 0.0`) | `68/45 ≈ 1.51111` | Subtracts `1 px` from post-`h1` list gap in Standard regime when `std_body_pitch / size_px < 68/45`. | `MEASURED` active on `e3_small` (`34/51`, p25 `e04_blocks`) vs inactive on `exam1`/`e3_std` (`45/68`) and `e3_large` (`50/82`). | Checked on `size_00` (`34/51`) and `size_04` (`45/68`); rests on one active geometry (`34/51`) (`MEASURED`). | **Yes** (rests on `34/51`). |
| 4 | `page.py:547` | `is_tall_lead = std_body_pitch < 3 * (std_body_pitch - c.size_px())` (algebraically `std_body_pitch > 1.5 * c.size_px()`) | `3/2 = 1.50000` | Selects `h5`/`h6` `mt_lead_k` and `mb_lead_k` slopes (`h_idx == 4, 5`) between `pitch/size <= 1.50` (`34/51`) and `pitch/size > 1.50` (`45/68`, `50/82`). | `MEASURED` on `e3_small` (`34/51`, `51/34 = 1.5000 -> False`) vs `exam1`/`e3_std` (`45/68`, `68/45 = 1.5111 -> True`) and `e3_large` (`50/82`, `82/50 = 1.6400 -> True`). | Checked on `size_00` (`34/51`) and `size_04` (`45/68`); boundary between `1.5000` and `1.5111` rests on `34/51` vs `45/68` (`MEASURED`). | **Yes** (boundary rests on `34/51` vs `45/68`). |

---

## 4. Final `1.11.3 -> 1.11.4` Before / After Summary (`MEASURED`)

| Corpus | `1.11.3` Exact | `1.11.4` Exact | Lost Exact | `1.11.3` Mean Match | `1.11.4` Mean Match | `1.11.3` Diff Px | `1.11.4` Diff Px | Diff Px Delta | `pos_lines` (`1.11.3 -> 1.11.4`) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| `probe` | `43 / 86` | `43 / 86` | `0` | `99.8054%` | **`99.8217%`** | `389,959` | **`357,394`** | **`-32,565`** | `2753 -> 2761 / 2863` (`+8`) |
| `exam1` | `50 / 70` | `50 / 70` | `0` | `99.0700%` | **`99.0760%`** | `1,516,617` | **`1,506,804`** | **`-9,813`** | `1452 -> 1452 / 1568` |
| `exam2` | `40 / 65` | `40 / 65` | `0` | `99.3165%` | `99.3165%` | `1,034,912` | `1,034,912` | `0` | `1395 -> 1395 / 1529` |
| `exam3_normal` (`e3_std`) | `60 / 82` | `60 / 82` | `0` | `99.6266%` | **`99.6294%`** | `713,359` | **`708,015`** | **`-5,344`** | `1899 -> 1899 / 2027` |
| `exam3_small` (`e3_small`) | `32 / 54` | `32 / 54` | `0` | `99.3257%` | **`99.3281%`** | `848,187` | **`845,237`** | **`-2,950`** | `1518 -> 1518 / 1651` |
| `e3_compact` | `33 / 56` | `33 / 56` | `0` | `98.4035%` | `98.4009%` | `2,082,738` | `2,086,061` | `+3,323` | `1490 -> 1485 / 1713` |
| `e3_large` | `87 / 124` | `87 / 124` | `0` | `99.0745%` | **`99.0766%`** | `2,673,432` | **`2,667,605`** | **`-5,827`** | `2341 -> 2341 / 2652` |
| `tables_images` (`ti_std`) | `4 / 44` | `4 / 44` | `0` | `91.7039%` | `91.7039%` | `8,503,517` | `8,503,517` | `0` | `299 -> 299 / 894` |
| `ti_compact` | `3 / 35` | `3 / 35` | `0` | `91.7533%` | `91.7533%` | `6,723,947` | `6,723,947` | `0` | `280 -> 280 / 733` |
| `ti_large` | `3 / 57` | `3 / 57` | `0` | `92.1675%` | `92.1675%` | `10,400,325` | `10,400,325` | `0` | `286 -> 286 / 1086` |
