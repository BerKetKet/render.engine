# Table Scale Model M — Pre-Registered Experiments (`v1.11.13`, `tables_v3`)

All experiments are evaluated under `KINDLE_RENDER_STRICT_HARFBUZZ=1` (HarfBuzz `6.0.0`) using `tools/lab_tables/score_tables.py` (3-theme sum of per-page diff pixels over window `y=83..2240` on `tables_images`, `ti_compact`, `ti_large`).

- **Baseline (`v1.11.12`, bit-identical to `v1.11.11` on tables)**: Standard `8,183,519` (4 exact, 44p), Compact `6,747,943` (3 exact, 35p), Large `10,279,117` (3 exact, 57p), **Total `25,210,579`**, exact `10`.
- **Global Keep Rule**: Keep an experiment iff (a) 3-theme total diff pixels strictly improves, (b) zero exact pages lost, (c) page counts stay `44 / 35 / 57`, and (d) zero golden changes outside the table corpora (and for E8, `exam2` stays `>= 99.32%` / `>= 40` exact pages).

---

## E0 — Verify Model M Candidate As Merged
- **Hypothesis**: Applying the reviewer's Model M (`tbl_pad_em=1.37`, `tbl_cap_em=7.5`, uniform layout, 42 px gated) on top of `v1.11.12` reproduces the reviewer's `~24.42M` total diff (`-788k` px) with `0` regressions outside the table corpora.
- **Prediction**: Total diff `~24,422,069` (`-788,510`), exact pages `5 / 3 / 3` (`11`), page counts `44 / 35 / 57`, all non-table goldens unchanged.
- **Result**: _pending_

## E1 — Coordinate-Descent Parameter Sweep (`KR_PAD`, `KR_CAP`, `KR_CAPW`, `KR_LP0`, `KR_LPM`, `KR_RPF`)
- **Hypothesis**: Jointly tuning `KR_PAD` (`1.25..1.5`), `KR_CAP` (`6.5..9.0`), `KR_CAPW` (widths-only cap), `KR_LP0`/`KR_LPM` (first/other column left padding), and `KR_RPF` (row pad factor) around `(1.37, 7.5, 0.845, 0.567, 0.28)` can further reduce 3-theme diff pixels without adding per-theme branches.
- **Prediction**: Small-to-moderate improvement (`-50k` to `-300k` px) from decoupling width cap or tuning cell/row padding.
- **Result**: _pending_

## E2 — Residual 1: Long 3-Column Table (`Table 5.1`, `long_table_5_1`)
- **Hypothesis**: A structural wrap/width rule in `em / pitch / avail` terms reproduces `long_table_5_1` device scales (`0.967 / 0.967 / 0.816` for Std/Cmp/Lrg) without the legacy `0.96 / 0.81` 3-column branch.
- **Prediction**: Either a clean cross-theme rule matches all 3 scales within `<= 2%` and improves 3-theme diff, or the residual is documented and the legacy branch is retained.
- **Result**: _pending_

## E3 — Residual 2: Data-Cell Unbreakable Min-Content Contribution
- **Hypothesis**: Adding a weighted data-cell min-content floor (`f * max_piece_px` after splitting at `-`) reproduces the Key/Value `"supercalifragilistic..."` table device scales (`0.971 / 0.914 / 0.99`) and improves 3-theme diff.
- **Prediction**: Small improvement on the Key/Value table pages across themes without degrading other tables.
- **Result**: _pending_

## E4 — Unscaled Tables (`scale == 1.0`) Width & Em-Based Padding
- **Hypothesis**: For unscaled tables (`sc_tbl == 1.0`), using natural 1x column widths with consistent em-based padding matches device ink extents better than stretched/legacy padding.
- **Prediction**: Reduced diff on unscaled table pages (`Std p6, p10..14`, `Cmp p7..9`, `Lrg p10..13`).
- **Result**: _pending_

## E5 — Uniform Layout Row Metrics (Float Pitch Accumulation, Header vs Body Pad, Top Pad)
- **Hypothesis**: Float accumulation of `std_pitch * sc_eff` per row (instead of per-row integer rounding) and/or tuned header/top row padding reduces vertical drift on tall scaled tables (9-col and 6-col).
- **Prediction**: Lower vertical drift and diff pixels on `Std p7, p15`, `Cmp p4, p6`, `Lrg p4, p16`.
- **Result**: _pending_

## E6 — Colspan Width Distribution (`cs > 1`)
- **Hypothesis**: Distributing `cs > 1` cell widths proportionally across their spanned columns improves scale and column widths on `T3` span tables.
- **Prediction**: Improved diff on span-table pages without regressing non-span tables.
- **Result**: _pending_

## E7 — Table Split Policy (`orphan=2, widow=1`) on Final Model M Layout
- **Hypothesis**: With Model M's improved vertical pitches, changing table split policy to `orphan=2, widow=1` may now pass where it previously regressed `+69k` on `1.11.9`.
- **Prediction**: Test cleanly; keep only if 3-theme total strictly improves with unchanged page counts `44 / 35 / 57`.
- **Result**: _pending_

## E8 — `exam2` (42 px) Gating Removal via Proportional Max/Min Width Sharing
- **Hypothesis**: Replacing the hard `CAP_EM` clamp with proportional sharing between max-content and min-content when `sum(w_c) > avail` reproduces both `exam2` p8 (`Table 3.1`: wide col 0, wrapped `Flow (L/min)` header, scale `~0.72`) and the 3 `tables_images` themes, allowing removal of the `size_px() == 42.0` gate while keeping `exam2 >= 99.32%` / `>= 40` exact pages.
- **Prediction**: Either reproduces both `exam2` and `tables_images` (gate removed), or `42 px` gating is kept and documented as a residual.
- **Result**: _pending_

## E9 — Split Icon (`103×57`) & Image Details (Step C / E / F)
- **Hypothesis**: Updating the split-table icon dimensions/placement (`103×57`) or image alignment improves 3-theme diff without affecting non-table corpora.
- **Prediction**: Test if budget allows; keep only if 3-theme total improves and all gates pass.
- **Result**: _pending_
