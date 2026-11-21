# BACKLOG.md — Deferred Fidelity & Architecture Items

Per the prep handoff rules, no fidelity tuning was performed after freezing the baseline. All remaining fidelity items and refactoring tasks are recorded below for future sessions:

## 1. Architecture & Refactoring (Next Session Target)
- **Split Layout from Rasterization**:
  - Move all pixel-snapping (`math.floor((start26 + off) / 64.0 + place_phase)`, baseline integer rounding, underline/strikethrough pixel coordinates, and `y_float -> int(round(y_float))` cursor snapping) behind a clean `PositionedPage` / `RenderCommand` boundary while preserving 100% golden SHA-256 compatibility across `probe`, `exam1`, and `exam2`.
- **Structured Text Layer**:
  - Emit glyph/word/line bounding boxes and Unicode text spans per page alongside the rasterized bitmap without altering layout coordinates.
- **Eliminate Process-Global FreeType Singleton Hazard**:
  - Encapsulate `_ft_lib_handle` per worker or guard `FT_Library` calls so chapters can be rasterized in parallel threads.

## 2. Fidelity Backlog (Do Not Touch During Refactor)
1. **Justified Line Last-Glyph 1 px Remainder Alignment (`layout.py:layout_line`, `fonts.py:adv26`)**:
   - Investigate device fixed-point space remainder distribution on justified lines to eliminate the 1 px right offset on the final word (`probe` pages 6–9, 16–18, 22–24, 28–30).
2. **`pitch = 68` Heading Ladder Transitions (`page.py:add_text_block`)**:
   - Measure and port the `std_body_pitch == 57` heading transition rules (`h1->h2`, `h2->h2`, `p->h1`, `h3->p`, multi-line `h2/h3` pitch) to the `45 px / pitch 68` preset (`exam1` E09 pages 34–38).
4. **Inline `<mark>` Highlight, Inline `<code>` Scale & Thai Segmentation (`epub.py`, `layout.py`, `page.py`)**:
   - Render `<mark>` background highlight rectangles (`exam2` X13 page 41).
   - Measure inline `<code>` advance scaling inside serif paragraphs (`exam2` X13 page 40).
   - Add dictionary-based Thai word segmentation for space-free Thai text (`exam2` X14 page 43).
5. **Uppercase Tilde Composites & Extended Latin Diacritics (`raster.py:_ft_glyph`)**:
   - Extend separate-component light autohinting to uppercase tilde glyphs (`Atilde`, `Ntilde`, `Otilde`, `Itilde`, `Utilde`) and inspect remaining diacritic differences on `exam2` X09 (pages 19, 21).
6. **Nav/TOC Antialiased Underlines & `<figure>/<figcaption>` (`page.py:draw_line`, `epub.py`)**:
   - Replace solid integer-height link underlines in `<nav>` with fractional-coverage antialiased underlines (`probe` p.2, `exam1` p.2, `exam2` p.2).
   - Measure `<figure>/<figcaption>` vertical margins in `exam1` E11 (page 48).

- Table solver: a column narrower than its longest header word makes the header break mid-word (seen on a 4-column table with "Recovery (min)"). Min-content width should not go below the longest unbreakable word.

- **`epub.py:_collapse` Drops `run.bg` on `<mark>` Runs (`epub.py:668`)**:
  - `_collapse(runs)` constructs `r_copy = Run(...)` without passing `bg=getattr(r, 'bg', None)`, causing `<mark>` background highlights parsed in `walk()` (`new_inline["bg"] = (255, 255, 0)`) to be silently dropped before `build_items`. Preserved in v1.7.0 per zero-pixel-change rule (`exam2` p.40 and `synthetic` p.3 depend on this).


## 8. v1.11.4 Candidate Evaluation — Rejected Candidates & Pitch-Ratio Threshold Audit

### Rejected Reviewer Candidates (Measured on `v1.11.3`)
- **Candidate A (`REJECT`, `MEASURED`) — Downscaled image (`s < 1.0`) `ceil` rounding in `page.py:add_image`**:
  - Replacing `round(nat_w * s)` / `round(nat_h * s)` with `ceil(...)` when `s < 1.0` improved `exam2` p36 (`88.7311% -> 92.8332%`, `+4.1021 pt`, `-95,562` diff px) only by accidentally compensating for an upstream `-2 px` vertical offset on that page (`HYPOTHESIS`), while regressing **20 pages across 7 corpora** (`+620,664` net diff pixels): `exam1` p48 (`-1.6427 pt`), `exam3_normal` p58 (`99.6133% -> 95.6930%`, `-3.9203 pt`, `+91,325` diff px), `exam3_small` p36 (`-0.1136 pt`), `e3_large` p84 (`99.6020% -> 96.9735%`, `-2.6285 pt`, `+61,233` diff px), `tables_images` p25 (`-0.5881 pt`), 7 pages of `ti_compact` (`+70,146` diff px), and 9 pages of `ti_large` (`+512,053` diff px, up to `-4.1301 pt` on p41) (`MEASURED`).
  - Direct device image bounding-box measurements confirm the device uses `round`, not `ceil`: `e3_std` p58 (`258.16 -> 258 px`), `e3_large` p84 (`229.04 -> 229 px`), `ti_large` 3:2 images (`545.33 -> 545 px` across 9 pages), and `ti_large` p41 (`136.33 -> 136 px`) (`MEASURED`).
- **Candidate B (`REJECT`, `MEASURED`) — Apostrophe word splitting in `hyphen.py:hyphenate_word`**:
  - `0` changed pixels (`0.0000%` delta) across all 10 capture datasets and `synthetic` (`MEASURED`). `kindle_render/layout.py:441-447` (`build_items`) already separates leading apostrophe prefixes (`1 <= a_idx <= 6`) into `lead_punct` and passes the purely alphabetic right-hand word to `hyphenate_word`.
- **Candidate C (`REJECT`, `MEASURED`) — Line-breaking tolerance ladder `tol * 8` in `layout.py:make_lines`**:
  - `0` changed pixels (`0.0000%` delta) across all 10 capture datasets and `synthetic` (`MEASURED`). Every paragraph in all 6 EPUB corpora breaks within `(tol, tol * 2, tol * 4)`.

### `1.11.x` Pitch-vs-Size Ratio Thresholds in `page.py` Resting on One Active Geometry (Requires 8-Size Series `size_01..03, 05..07` Verification)
- **`eff_body_pitch = max(float(std_body_pitch), (68.0 / 45.0) * c.size_px())` (`page.py:392, 553`)**:
  - Active when `extra_lead > 0.0` and `std_body_pitch / size_px < 68/45` (`1.5111`). Currently rests on `size_00_Bookerly` (`34/51`, ratio `1.5000`) vs `size_04_Bookerly` (`45/68`, ratio `1.5111`) and `theme_Large` (`50/82`, ratio `1.6400`) (`MEASURED`). Must be verified on `size_01..03` and `size_05..07` once those capture sets are uploaded.
- **`elif std_body_pitch < (68.0 / 45.0) * c.size_px(): gap -= 1` (`page.py:562`)**:
  - Post-`h1` list gap `-1 px` adjustment in the `extra_lead > 0.0` regime. Active branch (`< 68/45`) rests on `size_00_Bookerly` (`34/51`, p25 `e04_blocks`) (`MEASURED`). Must be checked on `size_01..03, 05..07`.
- **`is_tall_lead = std_body_pitch < 3 * (std_body_pitch - c.size_px())` (`page.py:547`, equivalent to `std_body_pitch > 1.5 * c.size_px()`)**:
  - Switches `h5`/`h6` `mt_lead_k` and `mb_lead_k` slopes between `size_00_Bookerly` (`34/51`, `pitch/size = 1.5000`) and `size_04_Bookerly` (`45/68`, `pitch/size = 1.5111`) / `theme_Large` (`50/82`, `pitch/size = 1.6400`) (`MEASURED`). Boundary rests on `34/51` vs `45/68`; must be checked across `size_01..03, 05..07`.
- **`D(ii)` Interaction on `e3_compact` p32 (`e08_verse`, `39/53`)**:
  - Under `extra_lead == 0.0`, `gap -= 1` on `b.heading == 0 and prev_h == 1 and b.left_em > 0.0 and list_level == 0` brings `probe` p87 `<blockquote>` and `<pre>` (`band 2..9`) to `0 px` residual (`-32,565` diff px), while shifting `e3_compact` p32 (`e08_verse`, where `<h1>` already has a `-1 px` residual under Compact `39/53`) from `-1 px` to `-2 px` (`+7,825` diff px). Once the Compact `h1` `-1 px` top-margin residual is resolved, `e3_compact` p32 will align automatically (`HYPOTHESIS`).


## 9. v1.11.5 Port-Ready Housekeeping Notes

### Largest Remaining Fidelity Gap: `tables_images` (`4/44` Exact, `91.7039%` Mean Match)
- **Measured at `v1.11.4` / `v1.11.5`**: `tables_images` (`45/68`, `Standard`) has `4/44` bitwise-identical pages (`91.7039%` mean pixel match, `8,503,517` diff px, `0.5836` mean ink IoU, `299/894` pos-exact lines).
- **Non-exact pages (`40` pages)**: `[2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 29, 30, 31, 32, 33, 34, 35, 36, 37, 39, 40, 42, 43, 44]`.
- **Root causes (logged for future work, untouched in `v1.11.5`)**: Table cell vertical padding/line-height, multi-page table chunking, and image/caption vertical spacing.

### Geometry-Keyed Conditionals & Tooling Cleanup Candidates
- **`c.pitch_px() < 55` (`page.py:870`)** and **`c.size_px() == 42.0` / `!= 42.0` (`page.py:1021, 1215, 1434`)**: Legacy geometry-keyed branches in `add_table` that should be unified into a physical table-padding model when `tables_images` is worked on.
- **Standalone / legacy scripts in `tools/`**: `tools/score_dir.py` was already removed; `tools/rhythm.py`, `tools/compare_reports.py`, `tools/score_all.py`, `tools/ab_diff.py`, `tools/block_residuals.py`, and `tools/fit_geometry.py` remain useful diagnostic utilities and are retained untouched.


## 10. v1.11.7 Heading Wrapping (H2) & Long-Word Line Breaking (H3) Notes
- **H2 (`REJECT` — Multi-Line Heading Break Cost)**: On `sizes_06` p44 (`"Heading 1: the generous barley of Merrow and its long wandering title"`, `lw = 922 px`), device breaks (`Heading 1: / the generous / barley of Merrow / and its long / wandering title`, widths `[533.7, 640.7, 855.2, 581.4, 771.5]`, `max = 855.2`, `sum_sq_slack = 373,027`, `var = 14,335`) have higher max width, higher sum-of-squared slack, and higher variance than engine breaks (`Heading 1: the / generous barley / of Merrow / and its long / wandering title`, widths `[718.4, 794.1, 517.0, 581.4, 771.5]`, `max = 794.1`, `sum_sq_slack = 360,495`, `var = 11,819`). No `w_last` in `[0.15..1.00]` reproduces the device break; likely requires a post-colon punctuation break bonus, left unimplemented until validated across all sizes.
- **H3 (`INVESTIGATED` — `tools/reports/headings/h3_longwords.md`)**: On `sizes_07` (`55/83`) p49–50, `Carpenter lantern invraisemblable-` (`923.36 px`, `+1.36 px` excess, `5.75%` shrink) is already offered by `hyph_fr.dic` and feasible at `tol = 4.0`, but `break_kp` chooses `invraisembla-` by `1.67` DP cost units (`49.82` vs `51.49`), causing `122` vs `121` pages.

- **Step B (`REVERTED` at `v1.11.9`, revisit after Step D)**: Mid-row table split policy `orphan_min = 2, widow_min = 1` reproduces Compact row-boundary splits (`+0` diff) and improves Large (`-10,830` diff px), but regresses Standard by `+80,068` px (`+69,238` net) because Standard p15 starts `+21 px` too low and its bottom split rule lands at `y = 2116` vs device `y = 2031` (`+85 px`) until scaled-table row pitch (`Step D`) is fixed.

## Remaining Table Model M Residuals (v1.11.13, see docs/hypotheses/tables_v3.md)
- **E8 (`exam2` 42 px Table 3.1 gating)**: Removing `size_px() != 42.0` with proportional max/min sharing regressed `exam2` (`1,385,821` diff px vs `~1.04M`) and 3-theme tables (`+212,971`, lost Standard p5 exact page). Needs a hybrid wrap/width-sharing rule that preserves both `exam2` (`>=99.32%` / `40` exact) and `tables_images`.
- **E7 (Table split policy `orphan=2, widow=1`)**: Regressed Standard p19 by `+158,395` px (`+43,510` net) even on top of Model M; investigate why Standard Table 5.1 splits 1 row earlier on device.
- **E9 (Split icon `103×57` vs `95×52`)**: `_render_table_icon_rgb` (`95×52`) is shared with `exam2` (Galaxy M30 density) whereas `tables_images_exam` (Galaxy M32) uses `103×57`; needs density-aware icon sizing.
- **T3 Span tables (E6) & small 2/3-col Large tables (`k16/k19/k22/k23`)**: `cs > 1` cells in `T3` were narrower than spanned columns (`0` px change); remaining diffs on `Standard p22/23`, `Large p46/47/51` are image-heavy pages (`i1_pct`, `i3_shapes`, `i5_flow`).
