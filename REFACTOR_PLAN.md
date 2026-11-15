# REFACTOR_PLAN.md — Layout/Raster Split & Structured Text Layer (`kindle_render` v1.6.1 → v1.7.0)

This plan specifies the boundary, dependency rules, pixel-snapping ownership, structured text layer schema, instance-owned raster state, and staged execution for splitting layout from rasterization while preserving 100% bit-for-bit identical output pixels on `probe`, `exam1`, `exam2`, and `synthetic`.

---

## 1. The Boundary (Versioned Serializable IR)

The layout engine (`epub.py`, `fonts.py`, `hyphen.py`, `layout.py`, `page.py`, `ir.py`) produces a serializable intermediate representation (`ir_version = "1.0"`) defined in `kindle_render/ir.py`. The rasterizer (`kindle_render/raster.py`) reads **only** `PositionedDocument` / `PositionedPage` / `RenderCommand` and never accesses `Block`, `Run`, `Box`, `Glue`, or `Penalty`.

### Data Model (`kindle_render/ir.py`)
- **`PositionedDocument`**:
  - `ir_version: str = "1.0"`
  - `engine_version: str`
  - `screen_w: int`, `screen_h: int`, `bg: Tuple[int, int, int]`, `fg: Tuple[int, int, int]`
  - `pages: List[PositionedPage]`
  - `chapter_errors: List[dict]`
- **`PositionedPage`**:
  - `ir_version: str = "1.0"`
  - `page_number: int` (1-based)
  - `chapter: str`
  - `width: int`, `height: int`, `bg: Tuple[int, int, int]`, `fg: Tuple[int, int, int]`
  - `commands: List[RenderCommand]` (exact drawing stream in painter's order)
  - `blocks: List[TextBlockMeta]` (structural metadata for the text layer: block index, kind, heading level `0..6`, list metadata, table grid metadata, and `lines: List[TextLineMeta]`)
- **`RenderCommand`** (discriminated union by `kind: str`):
  1. **`"glyph"`** (`GlyphCommand`):
     - `font_id: str` (relative/canonical font filename, e.g. `"Bookerly-Regular.ttf"`, plus `font_path: str`)
     - `glyph_id: int` (integer glyph index in the font's glyph order) and `glyph_name: str`
     - `size26: int` (26.6 fixed-point font size)
     - `boldness_level: int` (0–5)
     - `x: int`, `baseline: int` (exact integer pixel coordinates passed to `draw_glyph`, including `dx_px` and `dy_px`)
     - `start26: int`, `off26: int`, `adv26: int`, `dx_px: int`, `dy_px: int` (preserved 26.6 placement data)
     - `color: Tuple[int, int, int]` (resolved RGB foreground color)
     - `colr_layers: Optional[List[Tuple[str, int, Tuple[int, int, int]]]]` (for COLR/CPAL multi-layer color emoji: `(layer_glyph_name, layer_gid, (r, g, b))`)
     - `unicode_text: str` (the source Unicode cluster string for this glyph; `""` for non-first glyphs of a multi-glyph cluster)
     - `is_synthetic_hyphen: bool` (`True` if inserted by line breaking at a hyphen `Penalty` or table/pre soft-wrap hyphen; `False` if literal in source text)
     - `is_list_marker: bool`, `is_table_chrome: bool`
     - `block_idx: int`, `line_idx: int`, `word_idx: int`, `link_href: Optional[str]`
  2. **`"rect"`** (`RectCommand` — used for `<mark>` highlights, cover canvas clear, table expansion box, error border):
     - `x0: int`, `y0: int`, `x1: int`, `y1: int`, `color: Tuple[int, int, int]`
  3. **`"rule"`** (`RuleCommand` — used for `<hr/>`, table bottom rule, table icon diagonal strokes, and `<a>`/`<u>`/`<s>` link underlines and strikethroughs):
     - `x0: int`, `y0: int`, `x1: int`, `y1: int`, `color: Tuple[int, int, int]`, `role: str` (`"hr" | "table_rule" | "table_icon" | "underline" | "strike"`)
     - `link_href: Optional[str]` (for `"underline"` commands inside `<a href="...">`)
  4. **`"ring_bullet"`** (`RingBulletCommand` — level-2 `◦` procedural circle bullet):
     - `cx: int`, `cy: int`, `r: int`, `color: Tuple[int, int, int]`
  5. **`"image"`** (`ImageCommand` — cover image, block image, or inline image):
     - `x: int`, `y: int`, `width: int`, `height: int`, `image_sha256: str`, `role: str` (`"cover" | "block" | "inline"`), plus runtime `pixels: np.ndarray` (`uint8` RGB array `(H, W, 3)` excluded from JSON text, represented by `image_sha256`, `width`, `height` in canonical JSON).

### Canonical Layout Hash (`layout_pages` Golden)
Each `PositionedPage.canonical_json()` serializes the page IR to JSON with `sort_keys=True`, `separators=(",", ":")`, and any floating-point numbers formatted to fixed 6-decimal precision (`f"{v:.6f}"`). Its SHA-256 hex digest is stored in `tools/golden/<corpus>.json` under `"layout_pages"`.

---

## 2. Dependency Rule & HarfBuzz Ownership

- **Strict Import Boundary**:
  - **Layout modules** (`kindle_render/epub.py`, `kindle_render/fonts.py`, `kindle_render/hyphen.py`, `kindle_render/layout.py`, `kindle_render/page.py`, `kindle_render/ir.py`) **must not** import `kindle_render.raster`, `freetype`, or `libfreetype`.
  - **Metrics & Shaping module** (`kindle_render/fonts.py`): Owns `TTFont` table parsing (`cmap`, `hmtx`, `glyf` bounding boxes `xMin`/`yMin`/`xMax`/`yMax`, `kern`, `GPOS`, `GSUB`, `COLR`/`CPAL`) and **HarfBuzz (`libharfbuzz.so.0`)**.
  - **Where HarfBuzz lives and why**: HarfBuzz lives in `kindle_render/fonts.py` (the metrics/shaping layer) because `hb_shape` maps Unicode codepoint sequences to glyph IDs, cluster indices, `x_advance`, `x_offset`, and `y_offset` in design units (`upem`). Line breaking (`build_items` / `make_lines`) depends directly on shaped glyph advances (`x_adv26`) to compute token widths before pagination or rasterization ever runs. HarfBuzz never rasterizes bitmaps or calls FreeType.
  - **Raster module** (`kindle_render/raster.py`): Owns FreeType (`libfreetype.so.6` / `freetype-py`), `GlyphCache`, `Rasterizer` instance state, bitmap coverage extraction, and canvas compositing (`rasterize_page(ir_page, cfg)`).
- **Automated Gate (`G4`)**: `tools/check_imports.py` parses the AST of all layout modules (`epub.py`, `fonts.py`, `hyphen.py`, `layout.py`, `page.py`, `ir.py`) and asserts zero imports of `raster` or `freetype` and zero references to `libfreetype`.

---

## 3. Pixel-Snapping Ownership Table

To guarantee zero pixel changes on initial extraction (Rule 3), **layout computes and stores the exact integer pixel coordinates that `v1.6.1` passes to drawing**, alongside the 26.6 fixed-point values:

| Coordinate / Quantity | Formula in `v1.6.1` | Stored in IR | Owner |
|---|---|---|---|
| Unhinted advance `adv26` | `math.floor(raw_w * face.S)` (`fonts.py:381`) | `adv26: int` | **Layout** (`fonts.py`) |
| Pair kerning & `cpsp` | `math.floor(kern_units * face.S)` (`fonts.py:422`) | Included in `adv26: int` | **Layout** (`fonts.py`) |
| HarfBuzz `x_adv26`, `dx_px`, `dy_px` | `floor(x_adv * S)`, `round((x_off * S)/64)`, `round((y_off * S)/64)` | `adv26`, `dx_px`, `dy_px` | **Layout** (`fonts.py`, `layout.py`) |
| Line overhang shift | `start26 += max(0, -face.lsb26(name))` (`page.py:98, 102`) | `start26: int` (shifted) | **Layout** (`page.py`) |
| Glyph X pixel position | `x = math.floor((start26 + off) / 64.0 + place_phase) + dx_px` (`page.py:130`) | `x: int` (and `start26`, `off26`, `dx_px`) | **Layout** (`page.py`) |
| Baseline Y pixel position | `line_top + int(round((pitch - px)/2.0 + typo_ascender * px))` (`page.py:163`) | `baseline: int` (with `dy_px` added) | **Layout** (`page.py`) |
| Vertical cursor `y_float -> y` | `self.y = int(round(self.y_float))` (`page.py:224, 403, 484`) | Reflected in `baseline` & `y0/y1` | **Layout** (`page.py`) |
| `<mark>` highlight rect | `x0 = floor((start26+off)/64 + phase)`, `x1 = floor((start26+off+adv)/64 + phase) + 1`, `y0 = baseline - round(0.81*size_px)`, `y1 = baseline + round(0.33*size_px) + 1` | `RectCommand(x0, y0, x1, y1, bg)` | **Layout** (`page.py`) |
| Underline / Strikethrough | `x0 = x`, `x1 = floor((start26+off+adv26)/64 + phase) + 1`, `uy = baseline + dy_px + (7 - stroke_h)`, `sy = baseline + dy_px - int(0.21*pitch_px)` | `RuleCommand(x0, y0, x1, y1, col)` | **Layout** (`page.py`) |
| `<hr/>` & Table rules/icon | Integer `x0, y0, x1, y1` slices on `canvas` (`page.py:909-914, 989`) | `RuleCommand` / `RectCommand` | **Layout** (`page.py`) |
| Cover, Block & Inline Images | `_skia_bilerp_rgb` (cover) or `im.resize(..., BILINEAR)` at integer `(x, y_draw)` (`layout.py:312`, `page.py:121, 930, 958, 970`) | `ImageCommand(x, y, w, h, pixels)` | **Layout** (`page.py`) |
| FreeType outline dilation | `x_strength26 = int(round(dil_funits * face.S))`, `y_strength26 = int(round(0.80 * x_strength26))` (`raster.py:234`) | `size26`, `boldness_level` in `GlyphCommand` | **Raster** (`raster.py`) |
| Glyph bitmap placement & blend | `x0 = x + g.left`, `y0 = baseline - g.top`; float32 alpha blend; `np.clip(canvas + 0.5, 0, 255).astype(np.uint8)` | Executed in `Rasterizer.rasterize_page` | **Raster** (`raster.py`) |

---

## 4. The Structured Text Layer (`docs/text_layer_schema.md`)

Emitted directly from `PositionedDocument` / `PositionedPage` without recomputing layout:
- **Hierarchy**: `PageTextLayer` -> `blocks` (reading order `reading_order: int`, `kind`: `"paragraph" | "heading" | "list_item" | "pre" | "table" | "image"`, `heading_level`, `list_level`, `list_marker`, `table_meta`) -> `lines` (`bbox: [x0, y0, x1, y1]`, `baseline: int`) -> `words` (`text: str`, `bbox: [x0, y0, x1, y1]`, `direction: "ltr" | "rtl"`, `link_href: Optional[str]`) -> `clusters` (`text: str`, `glyph_name: str`, `glyph_id: int`, `bbox: [x0, y0, x1, y1]`, `is_synthetic_hyphen: bool`, `is_ligature: bool`).
- **Logical Text & Copy Fidelity**:
  - Soft hyphens (`U+00AD`) stripped during itemization and line-break hyphens (`Penalty(flagged=True)`) or soft-wrap hyphens in tables/`<pre>` are marked `is_synthetic_hyphen: true`. Joining words in reading order while omitting synthetic hyphens reproduces the source chapter's logical text.
  - Ligatures (`fi`, `fl`, `ffi`, `ffl`, etc.) carry their expanded source Unicode characters (`"fi"`, `"fl"`, etc.) in `cluster.text`.
  - RTL runs (`Arabic`, `Hebrew`): while visual glyph `RenderCommand`s remain in visual left-to-right order for identical pixel rendering, each glyph carries its logical character/word index so the text layer emits RTL words and characters in **logical reading order**.
  - Bounding boxes (`[x0, y0, x1, y1]`) are clamped to `[0, 0, page_width, page_height]` so every box lies strictly inside the page, and `len(glyph_boxes) == len(glyph_draw_commands)`.

---

## 5. Global State Elimination & Parallelism

- **Current Hazard**: `raster.py` initializes a module-level `_ft_lib_handle = ctypes.c_void_p()` at import time (`raster.py:124`). Sharing a single `FT_Library` across threads is unsafe in FreeType (`FT_New_Face` and `FT_Load_Glyph` mutate library/face state).
- **Target Design**:
  - Remove module-level `_ft_lib_handle` from the rendering call path.
  - Create a `Rasterizer(cfg)` class (and per-instance `GlyphCache`) in `kindle_render/raster.py` that initializes its own `FT_Library` handle (`FT_Init_FreeType`) on `__init__` and releases faces/library cleanly (`FT_Done_FreeType`) on close/destruction.
  - Each `Rasterizer` instance owns its `_ft_lib_handle`, `_ft` face map, and `_c` glyph bitmap cache, allowing any two threads or processes to rasterize `PositionedPage` objects concurrently with zero shared mutable state.
  - Layout of chapters stays sequential because vertical page fill and page numbering across spine documents depend on sequential pagination state (`Pager`).

---

## 6. Staged Execution Plan & Risk Estimates

| Step | Description | Gate Verification | Risk |
|---|---|---|---|
| **2.1** | Add `kindle_render/ir.py` (`PositionedDocument`, `PositionedPage`, `RenderCommand`s). Record IR commands in `Pager` alongside the existing canvas drawing path (dual path). Assert on every page that `Rasterizer(cfg).rasterize_page(ir_page)` equals the old canvas bytes. Populate `layout_pages` hashes in `tools/golden/*.json`. | G1, G2, G3, G5 | Low |
| **2.2** | Switch `Pager` / `render_blocks` / `render_lines` to build `PositionedDocument` only and delegate all pixel drawing to `Rasterizer.rasterize_page`. Delete old direct canvas drawing from `page.py`. | G1, G2, G3, G5 | Low |
| **2.3** | Isolate all FreeType and bitmap logic inside `raster.py`. Remove `from .raster import GlyphCache` and `_skia_bilerp_rgb` canvas blending from `page.py` (`page.py` only constructs IR). Add `tools/check_imports.py` and wire G4 into `tools/corpus.py`. | G1, G2, G3, G4, G5 | Low |
| **2.4** | Make `FT_Library` and `GlyphCache` strictly instance-owned on `Rasterizer`. Add `tools/test_parallel_raster.py` testing multi-thread and multi-process rasterization of identical IR pages. | G1–G5 + parallel test | Low |
| **2.5** | Add `kindle_render/text_layer.py`, `docs/text_layer_schema.md`, CLI `kindle_render text` + `epub --text-layer`, and `tools/test_text_layer.py` verifying tests (a)–(d) across all corpora. | G1–G5 + tests (a)–(d) | Medium |
| **2.6** | Expose public API `render_to_ir(book, cfg)` and `rasterize(ir_page, cfg)` in `kindle_render/__init__.py` with `README.md` example; keep all CLI flags unchanged. | G1–G5 | Low |
| **2.7** | Tidy dead code, update `ARCHITECTURE_NOTES.md`, bump version to `1.7.0`, run full gates into `tools/reports/after_refactor.*`, tag `refactor-1.7.0`, and package `kindle_render_v1.7.0.zip`. | G1–G5 | Low |

---

## 7. Out of Scope

- Fidelity fixes (1 px justified remainder, `pitch=68` heading transitions, apostrophe hyphenation, inline `<code>` scale, Thai segmentation, uppercase tilde autohinting, `<nav>` antialiased underlines).
- Table column width solver changes (including narrow header mid-word break).
- Hyphenation dictionary or algorithm changes.
- Rust port.
