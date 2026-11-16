# Stage D — Page-Break Divergences & Keep-With-Next Audit

## 1. `exam3_normal` p.36 (`h2` at Page Bottom vs Keep-With-Next)
- **MEASURED**: Device capture `exam_v3_screen_36.png` keeps the 3-line `h2` (`Section two heading that is long enough to wrap onto a second line on a narrow screen`) at the bottom of page 36 (`y = 1869..1939`, `1971..2041`, `2072..2124`; block bottom `y = 2201 <= page_bottom = 2203`), while the following `<p>` starts at the top of page 37 (`y = 191..235`, making page 37 `100%` bitwise exact!).
- **CONCLUSION**: Kindle does NOT pull a multi-line `h2` to the next page when the entire heading fits within `page_bottom` (`2201 <= 2203`) even if the following paragraph overflows to the next page (`H09_HEADING_KEEP_WITH_NEXT` applies only when the heading itself overflows `page_bottom`).
- **EVIDENCE CROPS**: `tools/reports/stage_d/exam3_normal_p36_h2_keep_device.png` vs `tools/reports/stage_d/exam3_normal_p36_h2_keep_rendered.png`.

## 2. `exam3_normal` p.39 (Page-Top `<ul><li>` Margin Retention)
- **MEASURED**: When `<ul><li>First item of an unordered list` overflows from page 38 to the top of page 39 (`i == 0`), device capture `exam_v3_screen_39.png` retains `mt = int(round(1.0 * vem_px)) = 57 px`, placing line 1 at `y = 237..282` (`y_cursor = 168 + 57 = 225`).
- **FIX**: Retained `top_mt = int(round(b.mt_em * vem_px * b.scale))` when `i == 0` overflows to a new page and `b.list_level > 0 and b.mt_em`.
- **EVIDENCE CROPS**: `tools/reports/stage_d/exam3_normal_p39_list_top_device.png` vs `tools/reports/stage_d/exam3_normal_p39_list_top_rendered.png`.

## 3. `exam3_normal` p.41 (Page-Top `<table>` Offset & `_mark_page_non_empty()`)
- **MEASURED**: When the 4-row table overflows from page 40 to the top of page 41, device capture `exam_v3_screen_41.png` places row 1 text at `y = 191..223` (`y_cursor = 168 + 8 = 176`). In addition, `add_table` calls `self._mark_page_non_empty()` so the following chapter (`E07 Inline Styles`, `page_break_before=True`) starts on page 42.
- **EVIDENCE CROPS**: `tools/reports/stage_d/exam3_normal_p41_table_top_device.png` vs `tools/reports/stage_d/exam3_normal_p41_table_top_rendered.png`.

## 4. `exam3_small` p.25–26 (`<hr/>` Page Break Instead of Silent Clip)
- **MEASURED**: On `exam3_small` page 25, `<pre>` ends at `y = 2162`. Adding `<hr/>` (`top_gap = 41 px`, rule height `3 px`) reaches `2206 > page_bottom = 2203`. Previously `add_hr` did not call `self.new_page()` and silently dropped the `<hr/>` rule when `self.y + 3 >= c.page_bottom`. Device capture `exam_v3_screen_smallfont_26.png` breaks to page 26 and draws `<hr/>` at `y = 209..211` (`168 + 41 = 209`), followed by the 4-row table (`20/20` positional-exact lines on page 26!).
- **EVIDENCE CROPS**: `tools/reports/stage_d/exam3_small_p25_hr_break_device.png`, `tools/reports/stage_d/exam3_small_p26_hr_top_device.png`.
