# Changelog

## 1.6.1
- Housekeeping only; rendered pixels are identical to 1.6.0 (checked on the three corpora).
- Removed `tools/golden/` (stored per-page hashes). `tools/corpus.py` now treats a missing golden file as "nothing to compare", not a failure. `--update-golden` still works when you want to record new hashes later.
- Kept `tools/reports/` (the 1.6.0 baseline numbers), `ARCHITECTURE_NOTES.md`, `BACKLOG.md`.

## 1.6.0

### De-Overfitting & General Compute Mechanisms (Step A)
- **General Table Column Allocation (`page.py:add_table`)**: Replaced fixed 4-column width overrides with a general min-content / max-content column width solver driven by cell glyph widths and alignment padding:
  - Header cells (`<th>`, `is_hdr=True`) break at spaces and after `/` in compound unit tokens (`len(token) > 4`), and do not hyphenate mid-word unless a single unbreakable token exceeds `inner_w`.
  - Data cells (`<td>`, `is_hdr=False`) break at spaces, after `/`, and via Liang hyphenation.
  - Columns whose single-line maximum width `max_w[ci]` is within the equal share `avail_w / ncols` lock at `round(max_w[ci])`; among remaining columns, columns whose `max_w` fits within their equal share of remaining width lock at `round(min_w[ci])` when paired with a wider prose column, and remaining width is distributed proportionally to `max_w`.
- **Root Container `em` Basis (`config.py`, `epub.py`)**: Removed all CSS class-name checks (`in2`, `in4`, `hang`, `lm3`, `rm3`, `both`). CSS `margin-left` and `margin-right` declarations with `|v| >= 2.0em` evaluate against `base_root_em_sp = 10.97619` (`28.8125 px` at `2.625x` density, yielding `57.625 px = 3688 / 64` at `2em` and `115.25 px = 7376 / 64` at `4em` across both `42 px` and `45 px` body font sizes). Negative `text-indent` (`v < 0`) evaluates against the same root `em` basis so hanging indents (`margin-left: 2em; text-indent: -2em`) cancel exactly at `x = x0`.
- **CSS `border-collapse: collapse` & Named Device Constants (`config.py`, `epub.py`, `layout.py`, `page.py`)**: Replaced all 37 `cfg.size26 == 2688 and cfg.x0 == 79` geometry branches with structural HTML/CSS properties (`border_collapse` parsed from `table { border-collapse: collapse }`, inline image dimensions, and named constants in `Config`).

### Algorithmic & Layout Fixes (Step B)
- **B1 — All-Caps Legal Prose Hyphenation & Heading-to-Block Spacing (`layout.py`, `page.py`)**: Enabled Liang hyphenation on uppercase words of 8 or more letters (`len(alpha) >= 8`) so long uppercase legal tokens hyphenate cleanly, and extended the `-1 px` `<h1> -> <p>` top-margin rounding adjustment to paragraphs with `mt_em > 1.0` (`x06_legal` Pages 14–15 now both `0` differing pixels).
- **B2 — `<mark>` Background Highlight Rendering (`epub.py`, `layout.py`, `page.py`)**: Propagated `bg = (255, 255, 0)` on runs inside `<mark>` elements and rendered contiguous yellow highlight bands (`[baseline - round(0.81 * size_px), baseline + round(0.33 * size_px)]`) prior to glyph compositing.
- **B3 — Inline Monospace Space Width, Shrink & `.loose` Line Pitch (`layout.py`, `page.py`)**: Included full `DroidSansMono` space width (`0.60 * r_size26 = 25.20 px`) in Knuth-Plass `SP` accumulation for monospace runs (`is_mono=True`), permitted line shrink on paragraphs with `<= 3` inline monospace boxes, and computed `line-height` in `(1.5, 2.0)` via integer truncation `int(line_height * vem_px * scale + 1e-6)`.
- **B4 & B10 — BiDi RTL Numeric Runs, Emoji Sequences & Korean Spacing (`fonts.py`, `layout.py`)**:
  - Extended inline RTL run reversal in `make_lines` to include neutral numeric `Box` tokens (`0-9`) bounded by RTL boxes (`NotoNaskhArabic` / `NotoSansHebrew`).
  - Added `U+2615` (`☕`) to the emoji codepoint detector, shaped multi-codepoint emoji ZWJ and skin-tone modifier clusters (`👍🏽`, `👨‍👩‍👧`, `🏳️‍🌈`) via HarfBuzz ligature shaping on `NotoColorEmoji.ttf`, and used `ef.space26()` (`52.28 px`) for inter-emoji spaces.
  - Added `0.0536 * size26` (`2.25 px` at `42 px`) to CJK space width in pure Hangul paragraphs (`U+AC00..U+D7AF`).
- **B5 — Multilingual Hyphenation Guards (`config.py`, `layout.py`, `page.py`)**: Disabled fallback to English hyphenation for languages without a matching hyphenation table (`sv`, `la`), enforced `min_word_length = 6` for non-English hyphenation (`it`), and adjusted `<h1> -> <h3>` gap by `-2 px` (`61 px`).
- **B6 — `::first-line` Small-Caps & 2-Line `::first-letter` Drop Cap (`epub.py`, `layout.py`, `page.py`)**: Added two-stage line composition for `::first-line { font-variant: small-caps }` (shaping Line 0 in small-caps with optical hyphen overhang and re-shaping remaining text in regular body font for Lines `1..n-1`), parsed `font-size < 280%` on `::first-letter` as a 2-line drop cap (`drop_cap_lines = 2`), and set the 2-line Bookerly drop-cap horizontal gap to `0.26 * size_px`.
- **B7 — 8-Bit Consecutive Hyphen Window Mask & Ragged Terminal-Word Hyphen Guard (`layout.py`)**: Widened the consecutive-hyphen bitmask in `break_kp` from `0x7f` (7 bits) to `0xff` (8 bits) so `TABLE_CONSEC[8] = 21.0` activates on the 8th consecutive hyphenated line (`exam2` Page 55 and `exam1` Pages 27, 62 now `0` differing pixels), and enabled the `w28` two-word terminal hyphen penalty (`c = 5.0`) in ragged-right mode (`exam2` Page 33 now `0` differing pixels).
- **B8 & B9 — Post-`<hr/>` Margin, `<h3> -> <ul>` Gap & `<h6> -> <p>` Gap (`page.py`)**: Set post-`<hr/>` bottom margin to `round(0.50 * vem_px)` (`24 px`) on collapsed-table stylesheets, `<h3> -> <ul>` gap to `56 px`, and uncollapsed `<h6> -> <p>` gap to `74 px` (restoring `probe` Page 81 to `0` differing pixels while preserving `exam2` Page 27 at `0` differing pixels).
