# `kindle_render` v1.11.10 — Mathematical EPUB Layout, Structured Text Layer & Rasterization Engine

`kindle_render` is a deterministic, self-contained Python EPUB layout, pagination, structured text-layer extraction, and glyph rasterization engine operating in 26.6 fixed-point coordinates (`1 px = 64 units`).

---

## Public Python API & CLI Usage

### Python API (`render_to_ir` & `rasterize`)
Layout (`render_to_ir`) and bitmap rasterization (`rasterize`) are cleanly separated across a versioned serializable intermediate representation (`PositionedDocument` -> `PositionedPage` -> `RenderCommand`):

```python
from kindle_render import Config, render_to_ir, rasterize, build_page_text_layer

cfg = Config(size26=2688, x0=79, right=1001, pitch=57, top=168, page_bottom=2203)

# 1. Pure layout (no FreeType calls): EPUB -> PositionedDocument IR
ir_doc = render_to_ir("book.epub", cfg, max_pages=10)

# 2. Rasterize individual IR pages (thread/process safe via instance-owned FreeType state)
first_page_img = rasterize(ir_doc.pages[0], cfg)
first_page_img.save("page_001.png")

# 3. Extract structured text layer (lines -> words -> glyph clusters with bounding boxes)
page_text = build_page_text_layer(ir_doc.pages[0])
print(page_text["logical_text"])
```

### Verification Gates (Clean Clone)
```bash
python3 tools/run_gates.py
```

### Command-Line Interface
```bash
# Render EPUB pages to PNG (and optionally emit structured text layer JSON)
python3 -m kindle_render epub input.epub out_dir/ --pages 10 --text-layer

# Extract structured text layer JSON only (page_001.json ..., document.json) without rasterizing
python3 -m kindle_render text input.epub out_dir/ --pages 10
```

---

## End-to-End Rendering Pipeline

### 1. EPUB & CSS Ingestion (`epub.py`)
1. **Container & Spine Traversal**: Reads `META-INF/container.xml`, resolves the OPF package manifest and reading spine, extracts any solitary cover image (`is_cover=True`), and parses each XHTML document in spine order.
2. **CSS Cascade & Specificity**: Parses `<style>` and linked `.css` stylesheets, scoring rules by selector specificity `(id, class, tag)` and merging inline `style="..."` declarations.
3. **Unit & Keyword Conversion (`_em`)**:
   - Font-size keywords map to exact scale ratios: `xx-small: 0.6`, `x-small: 0.75`, `small: 8/9`, `medium: 1.0`, `large: 1.2`, `x-large: 1.5`, `xx-large: 2.0`, `smaller: 5/6`, `larger: 1.2`.
   - Dimensional units (`em`, `rem`, `px`, `pt`, `%`) convert to relative `em` factors; margins with `|v| >= 2.0em` and negative `text-indent` evaluate against `base_root_em_sp = 10.97619` (`28.8125 px` at `2.625x`).
4. **Block Stream Construction**: Emits typed `Block` objects (`text`, `pre`, `table`, `image`, `hr`) with computed margins (`mt_em`, `mb_em`, `left_em`, `right_em`), signed `indent_em`, heading level (`1..6`), list markers (`bullet`, `ol_number`), table grid metadata (`table_rows` and `table_caption`), and inline `Run` trees (preserving `link_href` on `<a>` spans).

### 2. Font Metrics & Complex-Script Shaping (`fonts.py`)
1. **FontTools 26.6 Metrics**: Loads TrueType/OpenType faces at exact `size26` (`px * 64`), computing unhinted scalable advances (`adv26 = floor(raw_w * S)`), pair kerning (`kern`/`GPOS`), `liga` substitutions (`fi`, `fl`, `ff`, `ffi`, `ffl`), Arabic contextual joining, and HarfBuzz `hb_shape` for Devanagari, Thai, CJK/Hangul, and multi-codepoint emoji clusters while tracking source Unicode clusters.
2. **Layout-Only Bounding Boxes (`glyph_bbox_px`)**: Computes per-glyph pixel bounding boxes from `glyf` / `CFF` / `COLR` outline bounds without invoking FreeType.

### 3. Itemization, Hyphenation & Line Breaking (`hyphen.py`, `layout.py`)
1. **Liang Hyphenation Trie**: Evaluates odd pattern priorities across language dictionaries (`en`, `de`, `fr`, `es`, `it`, `pt`, `ru`, `nl`) with `left_hyphen_min = 2`, `right_hyphen_min = 3`, `min_word_length = 5` (`6` for non-English), mapping pattern indices to shaped glyph cluster boundaries and tagging line-break hyphens with `is_synthetic_hyphen = True`.
2. **Over-Wide Token Decomposition (`_split_overwide_boxes`)**: Splits any `Box` wider than $L_i$ into measure-fitting prefixes with trailing synthetic hyphens before invoking the line breaker.
3. **Line-Breaking Solvers**:
   - **Backward Dynamic Programming (`break_kp`)**: Minimizes quadratic stretch/shrink/ragged badness with an 8-bit consecutive/windowed hyphenation history mask (`TABLE_CONSEC`, `TABLE_WINDOW`), terminal-word hyphen guard, and runt-line linear penalty.
   - **Balanced Ragged DP (`break_balanced_ragged`)**: Minimizes squared relative shortfall $\sum (1 + w_i ((L_i - w_i)/L_i)^2)$ for headings and centered text.

### 4. Pagination, IR Emission & Structured Text Layer (`page.py`, `ir.py`, `text_layer.py`)
1. **Vertical Rhythm & Pagination (`layout_blocks_to_ir`)**: Tracks floating-point vertical cursor `y_float`, heading keep-with-next lookahead, widow/orphan protection (`widow_orphan = 2`), tables (`add_table`), preformatted blocks (`add_pre`), and images (`add_image`), emitting `PositionedDocument` / `PositionedPage` / `RenderCommand` objects.
2. **Structured Text Layer (`text_layer.py`)**: Extracts `blocks -> lines -> words -> clusters` with clamped pixel bounding boxes, logical reading order, ligature expansion, RTL logical ordering, and synthetic hyphen removal directly from the IR (`docs/text_layer_schema.md`).

### 5. Instance-Owned FreeType Rasterization (`raster.py`)
1. **`Rasterizer` & `GlyphCache`**: Each `Rasterizer(cfg)` instance owns an independent `FT_Library` handle and glyph bitmap cache, rendering `PositionedPage` commands with FreeType light autohinting (`FT_LOAD_TARGET_LIGHT`), anisotropic synthetic emboldening, separate-component lowercase tilde autohinting, and float32-to-uint8 alpha blending.
