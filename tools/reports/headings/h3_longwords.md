# H3 Investigation: Long-Word Line Breaking at 55 px (`size_07` p49–50)

## Summary
- **Corpus / Pages**: `exam/v3/kindle_exam_v3.epub` at `size_07_Bookerly` (`55 px / pitch 83`, `x0 = 79`, `right = 1001`, `line_w = 922.00 px`), chapter `e05_hyph_fr`, pages 49–50 (`121` pages on device vs `122` pages in engine).
- **Verdict**: **No code change (`REJECT` single-parameter tweak)** — the divergence is NOT caused by a missing hyphenation point, an insufficient shrink limit, or a tolerance ladder rejection. It is a `1.67`-unit global DP tie-break (`49.82` vs `51.49`) in `break_kp` between stretching line 0 (`invraisembla-`) vs stretching line 1 (`ment botanist telegram estua-`), coupled with the device keeping `estuary` unbroken on line 1.

---

## (a) Device Line 1 Width, Natural Width & Implied Space Shrink (`MEASURED`)
- **Device `size_07` p49 line 0 (`Carpenter lantern invraisemblable-`)**:
  - Measured ink bounds on `exam/v3/size_07_Bookerly/page_049.png`: `x = 81..999` (`w = 919 px`, full-width justified line across `79..1001`).
  - Natural metric width in `Bookerly-Regular.ttf` (`size26 = 3520`, `55.0 px`):
    - `Carpenter` (`262.23 px`) + ` ` (`11.81 px`) + `lantern` (`195.06 px`) + ` ` (`11.81 px`) + `invraisemblable` (`421.95 px`) + `-` (`20.50 px`) = **`923.36 px`**.
  - Excess over `line_w = 922.00 px`: **`+1.36 px`** across `2` inter-word spaces (`G = 23.62 px`).
  - Implied space shrink per gap: **`0.68 px`** = **`5.75%`** of space width (`11.81 px`), well within both `cfg.space_shrink = 17.504%` (`2.06 px/gap`) and `break_kp`'s `max_sh = 0.179 * G = 4.23 px`.

## (b) Hyphenation Points of `invraisemblablement` (`MEASURED`)
- Under `kindle_render/hyph_fr.dic` (`lang = 'fr'`):
  - `LiangHyphenator.hyphenate_word('invraisemblablement')` -> `['in', 'vrai', 'sem', 'bla', 'ble', 'ment']`.
- The break `invraisemblable-` **IS offered** as `items[19]` (`Penalty(width=1312 = 20.50 px, penalty=125, flagged=True)`).

## (c) Tolerance Ladder & Exact `break_kp` Cost Comparison (`MEASURED`)
- The paragraph succeeds on the **first rung** (`tol = 4.0`, `cfg.tolerance = 4.0`). Neither the shrink limit (`max_sh = 4.23 px > 1.36 px`) nor the tolerance ladder rejects `invraisemblable-`.
- Instead, `break_kp` compares the global DP cost of the first two lines (lines `L2..L5` are identical in both paths):
  - **Engine path (`invraisembla-` + `blement botanist telegram estua-`)**:
    - `L0`: `w = 845.30 px`, `slack = +76.70 px`, `G = 23.62 px`, `s0^2 = (76.70 / 23.62 * 2.0)^2 = 42.16`.
    - `L1`: `w = 872.94 px`, `slack = +49.06 px`, `G = 35.44 px`, `s1^2 = (49.06 / 35.44 * 2.0)^2 = 7.66`.
    - **Combined `L0 + L1` stretch cost**: **`49.82`**.
  - **Device L0 path (`invraisemblable-` + `ment botanist telegram estua-`)**:
    - `L0`: `w = 923.36 px`, `slack = -1.36 px`, `G = 23.62 px`, `s0^2 = (-1.36 / 23.62 * 2.5)^2 = 0.02`.
    - `L1`: `w = 794.88 px`, `slack = +127.12 px`, `G = 35.44 px`, `s1^2 = (127.12 / 35.44 * 2.0)^2 = 51.47`.
    - **Combined `L0 + L1` stretch cost**: **`51.49`** (`+1.67` higher than `49.82`).

## (d) Conclusion & Cross-Size Risk
- Because `invraisemblable-` is already feasible at `5.75%` shrink and `tol = 4.0`, increasing `max_sh` or adding a tolerance rung has **zero effect** on this paragraph.
- Changing `break_kp`'s stretch/hyphen weight (`2.0` vs `1.5 * c_pen`) to flip a `1.67`-unit DP tie-break would disturb justified line breaks across `probe`, `exam1`, `exam2`, and `sizes_00..06` (which currently hold `32..60` bitwise-identical pages per size).
- Logged in `BACKLOG.md` for future investigation of the device's French hyphenation / consecutive-hyphen penalty balance.
