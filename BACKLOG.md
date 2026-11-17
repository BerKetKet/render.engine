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
