# `kindle_render` v1.6.1 — Mathematical EPUB Layout & Rasterization Engine

`kindle_render` is a deterministic, self-contained Python EPUB layout, pagination, and glyph rasterization engine operating in 26.6 fixed-point coordinates (`1 px = 64 units`).

---

## End-to-End Rendering Pipeline

### 1. EPUB & CSS Ingestion (`epub.py`)
1. **Container & Spine Traversal**: Reads `META-INF/container.xml`, resolves the OPF package manifest and reading spine, extracts any solitary cover image (`is_cover=True`), and parses each XHTML document in spine order.
2. **CSS Cascade & Specificity**: Parses `<style>` and linked `.css` stylesheets, scoring rules by selector specificity `(id, class, tag)` and merging inline `style="..."` declarations.
3. **Unit & Keyword Conversion (`_em`)**:
   - Font-size keywords map to exact scale ratios: `xx-small: 0.6`, `x-small: 0.75`, `small: 8/9`, `medium: 1.0`, `large: 1.2`, `x-large: 1.5`, `xx-large: 2.0`, `smaller: 5/6`, `larger: 1.2`.
   - Dimensional units (`em`, `rem`, `px`, `pt`, `%`) convert to relative `em` factors; utility margin classes (`.hang`, `.lm3`, `.rm3`, `.both`, `.in2`, `.in4`) evaluate against the root CSS em (`28.8 px`).
4. **Block Stream Construction**: Emits typed `Block` objects (`text`, `pre`, `table`, `image`, `hr`) with computed margins (`mt_em`, `mb_em`, `left_em`, `right_em`), signed `indent_em`, heading level (`1..6`), list markers (`bullet`, `ol_number`), table grid metadata (`table_rows` with `(text, is_header, align, colspan, rowspan)` and `table_caption`), and inline `Run` trees.

### 2. Font Metrics, Shaping & Rasterization (`fonts.py`, `raster.py`)
1. **FreeType 26.6 Metrics & Hinting**: Loads TrueType/OpenType faces at exact `size26` (`px * 64`), applying FreeType normal hinting on the `y` axis while preserving unhinted scalable metrics on the `x` axis (`advance26 = round(hmtx_adv * size26 / upm)`).
2. **GPOS Kerning & Ligature Substitution**: Applies pair kerning from `kern`/`GPOS` tables, standard `liga` substitutions (`fi`, `fl`, `ffi`, `ffl`), Arabic contextual joining, and Devanagari half-form/matra reordering.
3. **Subpixel Positioning & Alpha Blending**: Positions glyphs at `x = floor((start26 + off26) / 64.0 + place_phase)` and blends 8-bit coverage bitmaps into a float32 page canvas before rounding to `uint8`.

### 3. Itemization, Hyphenation & Line Breaking (`hyphen.py`, `layout.py`)
1. **Liang Hyphenation Trie**: Evaluates odd pattern priorities across language dictionaries (`en`, `de`, `fr`) with `left_hyphen_min = 2`, `right_hyphen_min = 2`, `min_word_length = 5`, mapping pattern indices to shaped glyph cluster offsets (`curr_char == target_char`) and falling back to unligated halves when a break falls inside a ligature.
2. **Over-Wide Token Decomposition (`_split_overwide_boxes`)**: Splits any `Box` wider than $L_i$ into measure-fitting prefixes with trailing hyphens before invoking the line breaker.
3. **Line-Breaking Solvers**:
   - **Knuth-Plass (`break_kp`)**: Minimizes total demerits across justified and ragged paragraphs with asymmetric cubic badness ($100 r^3$ for stretch $r \ge 0$, $150 |r|^3$ for shrink $r < 0$), consecutive hyphen ladder penalties, fitness-class gap penalties, and linear shortfall cost $s_0 = ((L_i - w) / \text{size}_{26}) \times 0.61$ for ragged-right blocks. Falls back to greedy composition when item count exceeds $1000$.
   - **Balanced Ragged DP (`break_balanced_ragged`)**: Minimizes squared relative shortfall $\sum (1 + w_i ((L_i - w_i)/L_i)^2)$ for headings and centered text, using $w_{\text{last}} = 0.70$ for `h1..h3`, $0.62$ for `h4..h6`, and $0.15$ for all-caps or colon-terminated long-tail headings.

### 4. Pagination & Block Rendering (`page.py`)
1. **Vertical Rhythm & Margin Collapsing**: Tracks floating-point vertical cursor `y_float` with `gap = max(prev_mb, mt)`, heading keep-with-next lookahead, paragraph widow/orphan protection (`widow_orphan = 2`), and multi-line heading page splits.
2. **Tables, Preformatted Text & Images**:
   - `add_table`: Renders optional centered `<caption>`, resolves `colspan`/`rowspan` grid geometry, auto-scales wide $\ge 4$-column tables by $0.70\times$, aligns cells (`left`, `center`, `right`), and draws the bottom rule and expansion icon.
   - `add_pre`: Expands `\t` to 3-column tab stops, wraps space-containing lines at `max_cols` with full justification, and wraps underscore-delimited overflow lines via right-packed balanced splitting.
   - `add_image`: Resamples solitary covers with 16.16 fixed-point bilinear filtering and scales inline/block images to viewport constraints.
