# Pre-Registered Hypotheses: Heading Pagination, Heading Wrapping & Long-Word Line Breaking (`headings_v1.md`)

- **Baseline**: `kindle_render` `v1.11.6` (`commit 6a1a960`, HarfBuzz `6.0.0`, FreeType `2.12.1`)
- **8-Size Baseline (`exam/v3/size_00..07_Bookerly`)**:
  - `sizes_00` (`34/51`): `54/54` pages, `32/54` exact, `99.3281%`, `845,237` diff px
  - `sizes_01` (`37/56`): `59/59` pages, `34/59` exact, `99.3268%`, `925,292` diff px
  - `sizes_02` (`39/59`): `69/69` pages, `30/69` exact, `97.6582%`, `3,764,175` diff px
  - `sizes_03` (`42/63`): `73/73` pages, `46/73` exact, `99.4240%`, `979,588` diff px
  - `sizes_04` (`45/68`): `82/82` pages, `60/82` exact, `99.6294%`, `708,015` diff px
  - `sizes_05` (`47/71`): `89/89` pages, `54/89` exact, `99.3155%`, `1,419,163` diff px
  - `sizes_06` (`50/76`): `101/100` pages, `39/100` exact, `93.7172%`, `14,636,123` diff px
  - `sizes_07` (`55/83`): `122/121` pages, `17/121` exact, `94.5318%`, `15,413,474` diff px
  - **Total 8-size diff**: `38,691,067` px

---

## H1 — Full-Height Heading Keep-Together Across Page Boundaries
- **Statement**: A heading block (`b.heading > 0`) is never split across a page boundary when `not self.page_empty`: if `self.y + gap + len(lines) * pitch_fl > c.page_bottom` (full heading height exceeds remaining page height), start a new page before placing the heading (`page.py:add_text_block`), regardless of `b.mt_em` or whether `len(lines) == 2` vs `>= 3`.
- **Evidence**: Across all 8 sizes of `exam/v3`, our engine currently splits 4 headings across page boundaries (`sizes_02` p29->30, `sizes_05` p39->40, `sizes_06` p44->45 and p45->46). On `sizes_06` p44, the device capture has `13` ink bands ending at `y=1870..1920` (blank space below, moving the 4-line `h2` whole to p45 `20` bands `y=268..2161`), and moves `h4` whole to p46 (`20` bands `y=265..2140`).
- **Prediction**: Replacing `not b.mt_em and len(lines) == 2 and self.y + gap + 2 * pitch_fl > c.page_bottom` with `len(lines) >= 2 and self.y + gap + len(lines) * pitch_fl > c.page_bottom` will eliminate all 4 split headings, align `sizes_06` p44/45/46 structure with the device (`last-ink row` within `2 px`, same ink-row count), reduce total 8-size diff pixels substantially (especially on `sizes_02`, `sizes_05`, `sizes_06`), and cause `0` lost exact pages and `0` regressions on `probe`, `exam1`, `exam2`, `exam3_normal`, `exam3_small`, `e3_compact`, `e3_large`, `tables_images`, `ti_compact`, `ti_large`.
- **Pass/Fail Criterion**: `PASS` iff `sizes_06` p44/45/46 structure matches device (`last-ink row` within `2 px`, same ink-row count), zero lost exact pages, zero page-count worsening, total diff improves, and zero unexpected golden changes.

---

## H2 — Multi-Line Heading Line Breaking (`make_lines(is_heading=True)`)
- **Statement**: Device multi-line heading breaks (e.g., `size_06` p44 `"Heading 1: / the generous / barley of Merrow / and its long / wandering title"` vs engine `"Heading 1: the / generous barley / of Merrow / and its long / wandering title"`) follow a different cost function in `break_balanced_ragged` (e.g., minimizing sum of squared slack, minimizing max line width, or a different `w_last` / target width).
- **Evidence**: Measured table of all multi-line headings across `probe`, `exam1`–`exam3`, `sizes_00..07`, `e3_compact`, `e3_large` where engine and device break positions differ.
- **Prediction**: A single general cost rule in `make_lines(is_heading=True)` will reproduce both currently matching headings and currently mismatching headings across sizes without losing any exact page.
- **Pass/Fail Criterion**: `PASS` iff a single general cost rule reproduces both existing exact headings and mismatching headings with zero lost exact pages and lower total diff; otherwise `REJECT` (no code change) and log the full comparison table in `BACKLOG.md`.

---

## H3 — Long-Word Line Breaking at 55 px (`size_07` p49–50)
- **Statement**: Investigate why the device packs `Carpenter lantern invraisemblable-` onto line 1 of `size_07` p49 (`121` pages total) while our engine breaks `invraisembla- / blement` and overflows to `122` pages.
- **Evidence**: Direct measurements of (a) device line width vs natural metric width and implied space shrink per gap, (b) `invraisemblablement` hyphenation points and break cost, (c) `break_kp` shrink limit / tolerance ladder rung that rejected the device's line, and (d) 6 additional tight-line cases (3 where device packs and we don't, 3 where we pack and device doesn't).
- **Pass/Fail Criterion**: Implement only if one general rule explains all measured cases without regressing any size; otherwise document findings in `tools/reports/headings/h3_longwords.md` and `BACKLOG.md`.


---

## Measured Results (`v1.11.7`)
- **H1 (`PASS` — refined to `widow_orphan = 2`, kept)**:
  - Full-height keep-together (`len(lines) * pitch_fl > c.page_bottom`) improved `sizes_02` (`-557,767`) and `sizes_06` (`-1,508,004`), but regressed `sizes_05` (`54 -> 53` exact, `+1,301,304` diff px) because on `sizes_05` p39->40 the device **splits** the 4-line `h2` `2 + 2` (`band 13..14` on p39, `band 0..1` on p40).
  - Using `c.widow_orphan * pitch_fl` (`2 * pitch_fl`, `len(lines) >= 2`, removing `not b.mt_em`) matches **all 4 boundary headings** across all 8 sizes (`sizes_02` p29->30 moves whole, `sizes_05` p39->40 splits `2+2`, `sizes_06` p44->45 and p45->46 move whole): **`-2,065,771` diff px** across `sizes_00..07` + **`-233,081` diff px** on `e3_compact` (**`-2,298,852` diff px total**), `0` lost exact pages, `0` regressions on any other corpus.
  - Note on `sizes_06` p44–46: band counts match device `13/13` (p44), `20/20` (p45), `20/20` (p46); `dy_last` is `+8` (p44), `+10` (p45), `0` (p46) — the `+8/+10 px` vertical offset on p44–45 is due to `h1` heading wrap / spacing, not the page-break rule.
- **H2 (`REJECT` — logged in `BACKLOG.md`)**:
  - On `sizes_06` p44 (`"Heading 1: the generous barley of Merrow and its long wandering title"`), device breaks (`[533.7, 640.7, 855.2, 581.4, 771.5]`, `max=855.2`, `sum_sq_slack=373,027`, `var=14,335`) are strictly worse on `max`, `sum_sq_slack`, and `var` than engine breaks (`[718.4, 794.1, 517.0, 581.4, 771.5]`, `max=794.1`, `sum_sq_slack=360,495`, `var=11,819`) across all `w_last in [0.15..1.00]`. No pure slack/balance cost reproduces both existing exact headings and the device's colon-break preference -> no code change.
- **H3 (`INVESTIGATED` — `tools/reports/headings/h3_longwords.md`, logged in `BACKLOG.md`)**:
  - `Carpenter lantern invraisemblable-` (`923.36 px` vs `922.00 px`, `0.68 px/gap = 5.75%` shrink) IS offered by `hyph_fr.dic` and IS feasible on rung 1 (`tol = 4.0`). `break_kp` prefers `invraisembla-` by `1.67` cost units (`49.82` vs `51.49`). No code change to avoid disturbing justified line breaks across `probe`/`exam1`/`exam2`/`sizes_00..06`.
