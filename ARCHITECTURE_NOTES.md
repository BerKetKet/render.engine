# ARCHITECTURE_NOTES.md — `kindle_render` v1.7.0 Reference

This document maps the architecture, intermediate representation (IR) contract, coordinate rounding/snapping ownership, calibration constants, configuration dependencies, instance-owned state, known failure modes, and binary dependencies of `kindle_render` at tag `refactor-1.7.0`.

---

## 1. Pipeline & Module Map

```text
EPUB Archive (.epub)
  │
  ▼  [kindle_render/epub.py: load_epub -> _doc_blocks]
List[Block]  (Block dataclass: epub.py; Run dataclass: layout.py)
  │
  ▼  [kindle_render/page.py: layout_blocks_to_ir -> Pager.add_*]
  │  [kindle_render/layout.py: build_items]
  │  [kindle_render/fonts.py: Face.shape_with_clusters / shape_arabic_word_with_clusters / shape_devanagari_word_with_clusters]
List[Box | Glue | Penalty]  (layout.py, 26.6 fixed-point units, Unicode cluster metadata attached)
  │
  ▼  [kindle_render/layout.py: make_lines -> _split_overwide_boxes -> break_balanced_ragged / break_kp / _orig_break_kp / break_greedy]
List[Tuple[List[Box | Glue], Optional[Penalty]]]  (line segments + terminal hyphen penalty)
  │
  ▼  [kindle_render/layout.py: layout_line]
Tuple[List[Tuple], int, int]  (placements: (Face, glyph_name, off26, adv26, style_meta), nat26, hang_left)
  │
  ▼  [kindle_render/page.py: Pager.draw_line -> kindle_render/ir.py: PositionedDocument / PositionedPage / RenderCommand]
PositionedDocument  (ir_version="1.0"; pages: List[PositionedPage]; commands: List[RenderCommand])
  │
  ├──► [kindle_render/text_layer.py: build_document_text_layer / build_page_text_layer]
  │    Structured Text Layer JSON (page_NNN.json, document.json; validated against docs/text_layer_schema.md)
  │
  └──► [kindle_render/raster.py: Rasterizer(cfg).rasterize_document / rasterize_page -> GlyphCache.get_by_params]
       List[PIL.Image.Image]  (RGB uint8 page bitmaps, 1080×2340)
```

### Module Ownership & Dependency Boundary (Enforced by `tools/check_imports.py`, Gate G4)

1. **`kindle_render/config.py` (Configuration & Palettes)**:
   - Owns `Config`, `PALETTES`, `BOLDNESS_FUNITS_RAMP`, font/hyphenation dictionary path resolution, and viewport unit conversions (`size_px()`, `pitch_px()`, `vem_px()`, `base_root_em_px()`).
   - Imports: Python standard library only.
2. **`kindle_render/epub.py` (EPUB & CSS Ingestion)**:
   - Entry point: `load_epub(path, cfg) -> List[Block]`.
   - Parses OPF spine, CSS rules (`_parse_css`, `_matches`, `_style`, `_em`), cover/block/inline images, tables, `<pre>`, lists, drop caps, `::first-line` small-caps, and `<a href="...">` links (`Run.link_href`).
   - Imports: `PIL.Image`, `bs4`, `kindle_render.layout.Run`. Zero raster or FreeType imports.
3. **`kindle_render/fonts.py` (Font Metrics, OpenType Tables, HarfBuzz Shaping & Bounding Boxes)**:
   - Owns `Family` and `Face` (`TTFont` `cmap`, `hmtx`, `glyf`, `GSUB`, `GPOS`, `COLR`/`CPAL`), cluster-preserving shaping (`shape_with_clusters`, `shape_arabic_word_with_clusters`, `shape_devanagari_word_with_clusters`), and layout-only glyph bounding boxes (`glyph_bbox_px` via `glyf` / `BoundsPen`).
   - **HarfBuzz (`libharfbuzz.so.0`) Ownership**: Lives in `fonts.py` because complex-script glyph substitution and GPOS advance calculation (`x_adv26`, `x_off_px`, `y_off_px`) are required by `build_items` prior to line breaking.
   - Imports: `fontTools`, `ctypes` (`libharfbuzz.so.0`), `kindle_render.config`. Zero raster or FreeType imports.
4. **`kindle_render/hyphen.py` (Liang Hyphenation Trie)**:
   - Owns `LiangHyphenator` supporting compiled Kindle binary tries (`hyph_*.bin`) and standard TeX/Libhyphen dictionaries (`hyph_*.dic`).
   - Imports: Python standard library only.
5. **`kindle_render/layout.py` (Itemization, Line Breaking & Justification)**:
   - Owns `Run`, `Box`, `Glue`, `Penalty`, `build_items`, `_split_overwide_boxes`, `break_balanced_ragged`, `break_kp`, `_orig_break_kp`, `break_greedy`, `make_lines`, and `layout_line`.
   - Attaches source Unicode cluster text (`cluster_text`), word index (`word_idx`, `logical_word_idx`), character index (`logical_char_idx`), BiDi direction (`"ltr" | "rtl"`), ligature flag (`is_ligature`), and synthetic hyphen flag (`is_synthetic_hyphen`) to each placed glyph.
   - Imports: `PIL.Image` (inline image scaling), `kindle_render.fonts`, `kindle_render.hyphen`. Zero raster or FreeType imports.
6. **`kindle_render/ir.py` (Serializable Intermediate Representation)**:
   - Owns `IR_VERSION = "1.0"`, `PositionedDocument`, `PositionedPage`, `GlyphCommand`, `RectCommand`, `RuleCommand`, `RingBulletCommand`, `ImageCommand`, and `TextBlockMeta`.
   - Provides deterministic canonical JSON serialization (`PositionedPage.canonical_json()`, `sort_keys=True`, 6-decimal float formatting) and SHA-256 layout hashing (`PositionedPage.layout_sha256()`).
   - Imports: `numpy` and Python standard library only.
7. **`kindle_render/page.py` (Pagination & IR Construction)**:
   - Owns `Pager`, `layout_blocks_to_ir(blocks, cfg, family, max_pages)`, `layout_lines_to_ir(lines, cfg, family, bold, italic)`, and convenience wrappers `render_blocks` / `render_lines`.
   - `Pager` and `layout_*_to_ir` construct `PositionedDocument` / `PositionedPage` without importing `raster` or `freetype`.
8. **`kindle_render/text_layer.py` (Structured Text Layer & Schema Validator)**:
   - Owns `build_page_text_layer`, `build_document_text_layer`, `validate_page_text_layer`, `validate_document_text_layer`, and `write_text_layer_files`.
   - Consumes `PositionedDocument` / `PositionedPage` directly without recomputing layout or touching `raster.py`.
9. **`kindle_render/raster.py` (Instance-Owned FreeType Bitmap Rasterizer)**:
   - Owns `Rasterizer`, `GlyphCache`, `Glyph`, `rasterize(ir_page_or_doc, cfg)`, and `get_freetype_version()`.
   - Reads **only** `PositionedDocument` / `PositionedPage` / `RenderCommand` objects.

---

## 2. Intermediate Representation (`IR_VERSION = "1.0"`) Specification

| IR Class | Fields | Description |
|---|---|---|
| `PositionedDocument` | `ir_version`, `engine_version`, `screen_w`, `screen_h`, `bg`, `fg`, `pages: List[PositionedPage]`, `chapter_errors` | Full document layout output returned by `render_to_ir(book, cfg)` |
| `PositionedPage` | `ir_version`, `page_number`, `chapter`, `width`, `height`, `bg`, `fg`, `commands: List[RenderCommand]`, `blocks: List[TextBlockMeta]` | Single page IR; `layout_sha256()` hashes `canonical_json()` |
| `GlyphCommand` (`kind="glyph"`) | `font_id`, `font_path`, `glyph_id`, `glyph_name`, `size26`, `boldness_level`, `x`, `baseline`, `start26`, `off26`, `adv26`, `dx_px`, `dy_px`, `color`, `colr_layers`, `bbox`, `unicode_text`, `is_synthetic_hyphen`, `is_list_marker`, `is_table_chrome`, `is_drop_cap`, `is_ligature`, `block_idx`, `line_idx`, `word_idx`, `logical_word_idx`, `logical_char_idx`, `direction`, `link_href` | Single positioned glyph draw command with both snapped pixel coordinates (`x`, `baseline`) and 26.6 placement values (`start26`, `off26`, `adv26`) plus Unicode cluster provenance |
| `RectCommand` (`kind="rect"`) | `x0`, `y0`, `x1`, `y1`, `color`, `role` (`"mark_bg" \| "square_bullet" \| "table_icon_box" \| "cover_bg" \| "error_box"`) | Solid filled rectangle in integer page pixels |
| `RuleCommand` (`kind="rule"`) | `x0`, `y0`, `x1`, `y1`, `color`, `role` (`"underline" \| "strike" \| "hr" \| "table_rule" \| "table_icon_arrow"`), `link_href` | Horizontal, vertical, or diagonal rule stroke in integer page pixels |
| `RingBulletCommand` (`kind="ring_bullet"`) | `cx`, `cy`, `r`, `color` | Level-2 `◦` ring bullet (`r - 0.8 <= hypot(dx, dy) <= r + 0.8`) |
| `ImageCommand` (`kind="image"`) | `x`, `y`, `width`, `height`, `pixels` (`uint8` RGB array), `image_sha256`, `role` (`"cover" \| "block" \| "inline"`) | Pre-resampled RGB image placed at integer `(x, y)` |
| `TextBlockMeta` | `block_idx`, `chapter`, `kind`, `heading_level`, `list_level`, `list_marker`, `table_caption`, `table_rows`, `bbox` | Per-page structural block descriptor used by `text_layer.py` |

---

## 3. Final Pixel-Snapping and Rounding Map (`owned by layout` vs. `owned by raster`)

Every coordinate, advance, baseline, margin, and coverage rounding step in `kindle_render` v1.7.0, with explicit boundary ownership:

| # | Stage & Location | Quantity / Formula | Stored in IR | Ownership |
|---|---|---|---|---|
| 1 | `fonts.py:Face.__init__` | Scale factor `self.S = (size26 / float(self.upem)) - 1e-9` | Used to compute `adv26` | **owned by layout** |
| 2 | `fonts.py:Face.adv26` | Unhinted glyph advance `math.floor(raw_w * self.S)` (with `raw_w += dilation_funits()` when `boldness_level > 0`) | `GlyphCommand.adv26` | **owned by layout** |
| 3 | `fonts.py:Face.shape_with_clusters` | Pair kerning `math.floor(kern_units * self.S)` and all-caps `cpsp` `math.floor(cpsp_xadv * self.S)` | Included in `GlyphCommand.adv26` | **owned by layout** |
| 4 | `fonts.py:Face.lsb26` | Left side bearing `int(math.floor(gl.xMin * self.S))` | Included in `GlyphCommand.start26` | **owned by layout** |
| 5 | `fonts.py:Face.shape_devanagari_word_with_clusters` | HarfBuzz `x_adv26 = int(math.floor(x_advance * self.S))`, `x_off_px = int(round((x_offset * self.S) / 64.0))`, `y_off_px = int(round((y_offset * self.S) / 64.0))` | `GlyphCommand.adv26`, `dx_px`, `dy_px` | **owned by layout** |
| 6 | `fonts.py:Face.glyph_bbox_px` | Glyph bounding box `gx0 = x + floor(xMin * sp)`, `gx1 = max(gx0+1, x + ceil(xMax * sp), x + round(adv26/64))`, `gy0 = baseline - ceil(yMax * sp)`, `gy1 = baseline - floor(yMin * sp)`, clamped to `[0..W, 0..H]` | `GlyphCommand.bbox` | **owned by layout** |
| 7 | `layout.py:_shape_token_with_fallbacks` | Baseline shift `dy_px = int(round(run.baseline_shift_em * (size26 / 64.0)))`; small-caps size `int(round(size26 * 0.70))` | `GlyphCommand.dy_px`, `size26` | **owned by layout** |
| 8 | `layout.py:build_items` | Inline image scale `w_sc = max(1, int(round(im.width * dpi_scale)))`, `h_sc = max(1, int(round(im.height * dpi_scale)))`, `w26 = int(round(w_sc * 64))`; space shrink `math.floor(sp * cfg.space_shrink)` | `ImageCommand.width`, `height` | **owned by layout** |
| 9 | `layout.py:layout_line` | Optical overhang `math.floor(optical_margin_ratio * w)`; Bresenham / proportional integer glue distribution `((j + 1) * delta) // k - (j * delta) // k`; post-hyphen kerning `math.floor(kern_units * face.S)` | `GlyphCommand.off26` | **owned by layout** |
| 10 | `page.py:Pager.draw_line` | Line left overhang shift `start26 += max(0, -face.lsb26(name))` | `GlyphCommand.start26` | **owned by layout** |
| 11 | `page.py:Pager.draw_line` | **Glyph X pixel snapping**: `x = math.floor((start26 + off) / 64.0 + self.cfg.place_phase) + dx_px` | `GlyphCommand.x` | **owned by layout** |
| 12 | `page.py:Pager.baseline_in` | **Baseline Y pixel snapping**: `line_top + int(round((pitch - px) / 2.0 + self.cfg.typo_ascender * px))` (`+ dy_px` per glyph) | `GlyphCommand.baseline` | **owned by layout** |
| 13 | `page.py:Pager.add_text_block` | Vertical cursor `self.y_float` accumulation and integer snapping `self.y = int(round(self.y_float))` | Reflected in `baseline`, `y0`, `y1` | **owned by layout** |
| 14 | `page.py:Pager.draw_line` | `<mark>` highlight rect `x0 = floor((start26+off)/64 + phase)`, `x1 = floor((start26+off+adv)/64 + phase) + 1`, `y0 = baseline - round(0.81*size_px)`, `y1 = baseline + round(0.33*size_px) + 1` | `RectCommand(x0, y0, x1, y1)` | **owned by layout** |
| 15 | `page.py:Pager.draw_line` | Underline & strikethrough `x_end = floor((start26+off+adv26)/64 + phase)`, `stroke_h = int(size_px // 22.5) + 1`, `uy = baseline + dy_px + (7 - stroke_h)`, `sy = baseline + dy_px - int(0.21 * pitch_px)` | `RuleCommand(x0, y0, x1, y1)` | **owned by layout** |
| 16 | `page.py:Pager.add_table` / `add_hr` | Table column widths `col_ws`, cell baselines, bottom rule, expansion icon, and `<hr/>` coordinates | `GlyphCommand`, `RuleCommand`, `RectCommand` | **owned by layout** |
| 17 | `page.py:Pager.add_image` | Cover `_skia_bilerp_rgb` (16.16 fixed-point bilinear resampling) and block `im.resize(..., Image.BILINEAR)` at integer `(x, y_draw)` | `ImageCommand(x, y, width, height, pixels)` | **owned by layout** |
| 18 | `raster.py:GlyphCache._ft_glyph_params` | FreeType anisotropic outline emboldening `x_strength26 = int(round(dil_funits * S))`, `y_strength26 = int(round(0.80 * x_strength26))`; lowercase tilde component offset `dx26 = int(round(c1.x * S))` | Computed from `GlyphCommand.size26`, `boldness_level` | **owned by raster** |
| 19 | `raster.py:Rasterizer._draw_glyph_on_canvas` | Bitmap bearing offset `x0 = cmd.x + g.left`, `y0 = cmd.baseline - g.top` and float32 alpha blending `reg * (1.0 - a) + fg * a` | Executed on `canvas` buffer | **owned by raster** |
| 20 | `raster.py:Rasterizer.rasterize_page` | Final canvas float32-to-uint8 quantization `np.clip(canvas + 0.5, 0, 255).astype(np.uint8)` | Output `PIL.Image` | **owned by raster** |

---

## 4. Calibration Inventory (v1.7.0)

Every calibration constant, lookup table, and conditional formula in `kindle_render` v1.7.0, classified as `measured`, `fitted`, `guessed`, or `unknown` with its source:

| Location | Symbol / Mechanism | Value(s) | Where It Came From | Classification |
|---|---|---|---|---|
| `config.py:31-38` | `screen_w`, `screen_h`, `x0`, `right`, `top`, `page_bottom`, `dpi_scale` | `1080`, `2340`, `39`/`79`, `1041`/`1001`, `168`, `2203`, `2.625` | `probe`, `exam1`, and `exam2` device screenshot dimensions and margins | `measured` |
| `config.py:39` | `img_px_scale` | `1.80` (`28.8 / 16.0`) | Block image dimensions on `probe` p.88 & `exam2` X12/X16 | `measured` |
| `config.py:42` | `size26` | `2688` (`42 px`), `2880` (`45 px`) | `probe`/`exam2` (`42 px`) and `exam1` (`45 px`) body font sizes | `measured` |
| `config.py:45-49` | `pitch_ratio`, `typo_ascender`, `body_cap_height`, `display_cap_height` | `57 / 42`, `0.802`, `0.693`, `0.762` | Bookerly `OS/2` `sTypoAscender` (`+802` FUnits) and cap heights in `probe` p.1 / `exam1` p.3 | `measured` |
| `config.py:24, 59-61` | `BOLDNESS_FUNITS_RAMP`, `boldness_anisotropic_y` | `(0, 12, 24, 38, 52, 68)`, `0.80` | Boldness slider levels `0..5` FUnits dilation and vertical ratio | `measured` |
| `config.py:64` | `place_phase` | `0.5` | Subpixel 26.6-to-pixel rounding phase across all captures | `measured` |
| `config.py:73-74` | `space_stretch`, `space_shrink` | `0.75`, `101 / 577.0` (`0.17504`) | Space stretch/shrink bounds in justified paragraphs (`probe` C1–C2, `exam1` E03–E05) | `measured` |
| `config.py:75` | `runt_min_chars` | `7` | Heading last-word non-breaking tie threshold (`exam2` X10) | `fitted` |
| `config.py:78-81` | `micro_tracking`, `tracking_min_em`, `tracking_max_em` | `False`, `-0.005`, `0.005` | Dormant Tier-2 inter-character tracking bounds | `fitted` |
| `config.py:92-94` | `left_hyphen_min`, `right_hyphen_min`, `min_word_length` | `2`, `3`, `5` (`6` for non-EN in `layout.py:255`) | `probe` C3–C5, `exam1` E05–E07, `exam2` X09/X11 hyphenation | `measured` |
| `config.py:95-100` | `hyphen_penalty`, `ragged_hyphen_penalty`, `ladder2`, `ladder3`, `fitness_gap`, `tolerance`, `ragged_shortfall` | `125`, `50`, `3000`, `10000`, `1000`, `4.0`, `100.0` | Fallback `_orig_break_kp` parameters (used on drop-cap and forced-break paragraphs) | `fitted` |
| `config.py:109-111` | `heading_scale`, `heading_margin_top_em`, `heading_margin_bottom_em` | `(2.0, 1.5, 1.17, 1.0, 0.83, 0.67)`, `(0.67, 0.82, 0.96, 1.33, 1.67, 2.33)`, `(0.67, 0.84, 1.0, 1.33, 1.67, 2.35)` | `exam1` E02, `probe` E1, and `exam2` X10 heading ladders (`h1..h6`) | `measured` |
| `config.py:118` | `base_root_em_sp` | `10.97619` (`28.8125 px` at `2.625x`) | Root CSS `em` basis for `|margin| >= 2em` and negative `text-indent` (`exam1` p.25–26, `exam2` p.14–15, 40–41) | `measured` |
| `config.py:119` | `blockquote_margin_ratio` | `0.04725` | `blockquote` and `<dd>` margin ratio of container width (`probe` p.52, 87; `exam1` p.44) | `measured` |
| `config.py:120-125` | `collapsed_table_*` (`margin_px`, `scale`, `line_pitch`, `rule_h`, `pad_1x`, `pad_scaled`) | `36`, `0.70`, `55`, `4`, `34`, `24` | `border-collapse: collapse` table geometry (`exam2` p.8, 13, 35) | `measured` |
| `config.py:126` | `pre_hr_top_gap_px` | `50` | Vertical gap from `<pre>` to `<hr/>` on collapsed stylesheet (`exam2` p.36) | `measured` |
| `config.py:129-131` | `ul_indent_em`, `ul_nested_indent_em`, `ol_indent_em` | `2.0000`, `1.9762`, `2.0952` | Unordered and ordered list left indents (`probe` p.87, `exam1` E11, `exam2` X12) | `measured` |
| `epub.py:108` | `::first-letter` 2-line vs 3-line threshold | `font-size < 280.0% -> 2 lines else 3 lines` | `exam2` X15 (`260%` -> 2-line drop cap) vs `exam1` E01 (`320%` -> 3-line drop cap) | `measured` |
| `epub.py:140-150` | `CSS_FONT_SIZE_KEYWORDS` | `0.6, 0.75, 8/9, 1.0, 1.2, 1.5, 2.0, 5/6, 1.2` | CSS keyword font scales (`exam2` X08, X13) | `measured` |
| `epub.py:363-366` | `sup` / `sub` `baseline_shift_em` | `(-0.21 * pitch_px) / (size_px * 5/6)`, `13.0 / (size_px * 5/6)` | Superscript/subscript vertical shifts (`probe` D1, `exam1` E10, `exam2` X04/X13) | `measured` |
| `epub.py:576, 579` | Roman `<ol>` gutter width | `132.0 / cfg.size_px()` | Lower/upper-roman list indent (`exam2` X12 p.35) | `measured` |
| `fonts.py:66` | `Face.S` IEEE-754 float32 quantization adjustment | `(size26 / float(upem)) - 1e-9` | Matches 32-bit float advance floor boundary on Bookerly/Noto glyphs | `measured` |
| `layout.py:86, 333` | Small-caps scale factor | `0.70` | `.sc` and `::first-line` small-caps glyph size (`exam1` E10, `exam2` X13/X15) | `measured` |
| `layout.py:345` | Hangul inter-word space adjustment | `+ int(round(0.0536 * r_size26))` | Pure Hangul paragraph space width (`exam1` E12 p.51) | `measured` |
| `layout.py:422` | All-caps hyphenation length guard | `len(alpha) >= 8` hyphenates | All-caps legal prose hyphenation (`exam2` X06 `"FRAUDU-/LENT"`) | `measured` |
| `layout.py:560` | `break_balanced_ragged` after-comma bonus | `-0.05` | Multi-line heading break after comma (`exam2` X10) | `fitted` |
| `layout.py:701-702` | `TABLE_CONSEC`, `TABLE_WINDOW` | `(0, 1, 1.5, 2, 3, 5, 8, 13, 21)`, `(0, 0, 0, 1, 3, 8, 9, 10, 10)` | 8-bit sliding-window hyphenation penalty tables in `break_kp` | `measured` |
| `layout.py:837-908` | `break_kp` cost coefficients | `G + 0.1`, shrink `2.5` (`max_sh = 0.179G` / `0.099G`), stretch `2.0`, ragged `0.61`, runt `(0.2 - fill) * 4.2`, terminal hyphen `c = 5.0`, ladder scale `1.5` | Backward DP paragraph line breaking across `probe`, `exam1`, `exam2` | `measured` |
| `layout.py:1062` | Heading `w_last_hd` weights | `0.15` (all-caps / colon-long), `0.7` (`size26 > body`), `0.62` (`h4..h6`) | Heading line balance in `exam1` E02 and `exam2` X10 (`7/7` exact pages) | `measured` |
| `page.py:21-26` | `_skia_bilerp_rgb` phase & scale | `x0 = -0.009802`, `y0 = -0.041117`, `sx = sy = 60680 / 65536.0` | Cover image bilinear resampling on `probe` p.1 | `fitted` |
| `page.py:135, 195-215` | `<mark>` band & underline/strike offsets | `<mark>`: `[-0.81*size_px, +0.33*size_px]`; `stroke_h = int(size_px // 22.5) + 1`, `uy = base + (7 - stroke_h)`, `sy = base - int(0.21 * pitch_px)` | Underline, strikethrough, and highlight bands (`exam1` E10, `exam2` X13) | `measured` |
| `page.py:302` | Spacer paragraph (`\u00a0`) height | `std_body_pitch - 4.04124 * max(0, std_body_pitch - (19/14)*size_px)` | Spacer paragraphs in `exam1` (`40 px`) vs `exam2` (`57 px`) | `measured` |
| `page.py:355` | Drop-cap horizontal gap | `0.26 * size_px` (2-line regular), `0.18 * size_px` (3-line regular), `0.15 * size_px` (display) | Drop-cap horizontal clearance (`probe` E3, `exam1` E01, `exam2` X15) | `measured` |
| `page.py:444-471` | Heading vertical margins & `pitch == 57` transition adjustments | `mt_base_em = (0.6632, 0.8140, 0.9717, 1.3263, 1.6487, 2.2938)`, `mb_base_em = (0.6632, 0.8281, 0.9717, 1.3263, 1.6487, 2.2938)`, `mt_lead_k`, `mb_lead_k`, `h1->h2: -1`, `h1->h3: -2`, `h2->h2: 58`, `p->h1: +1`, `h1->p: -1`, `h3->ul: +2`, `h3->p: +1`, `h6->p: +1` | `exam2` X10 & `exam1` E02 heading ladders and transitions | `measured` / `fitted` |
| `raster.py:294, 314` | Anisotropic emboldening & lowercase tilde split | `y_strength26 = int(round(0.80 * x_strength26))`; split `('atilde', 'ntilde', 'otilde', 'itilde', 'utilde')` | `exam2` X09 lowercase tilde glyphs (`ã, ñ, õ, ĩ, ũ`) | `measured` |

---

## 5. Instance-Owned State, Caches & Parallelism

1. **Zero Process-Global FreeType State (`kindle_render/raster.py`)**:
   - Module-level `_ft_lib_handle` has been removed.
   - Each `Rasterizer(cfg)` / `GlyphCache(exact)` instance initializes its own private `FT_Library` handle (`self._ft_lib`) via `FT_Init_FreeType` and releases all `FT_Face` handles and the `FT_Library` in `close()`.
   - Two or more threads (`ThreadPoolExecutor`) or processes (`ProcessPoolExecutor`) can rasterize `PositionedPage` objects concurrently with zero shared mutable state (verified across all 233 corpus pages by `tools/test_parallel_raster.py`).
2. **Read-Only Hyphenation Cache (`kindle_render/hyphen.py`)**:
   - `LiangHyphenator._CACHE` is keyed on `(abs_path, left_min, right_min, min_word_len)` and is strictly read-only after loading.
3. **Sequential Chapter Pagination (`kindle_render/page.py`)**:
   - `layout_blocks_to_ir` processes spine chapters sequentially because page numbering (`page_number = 1..N`) and `max_pages` truncation depend on cumulative page count across chapters.

---

## 6. Known Failure Modes (Unchanged from v1.6.1; Logged in `BACKLOG.md`)

1. **Justified Line Last-Glyph 1 px Remainder Alignment (`probe`, `exam1`, `exam2`)**.
2. **`pitch = 68` Heading Transition Adjustments (`exam1` E08/E11)**.
3. **Hyphenation of Apostrophe Words & Long-Word Tie-Breaking (`exam2` X11, X16)**.
4. **`epub.py:_collapse` Dropping `run.bg` on `<mark>` Runs & Inline `<code>` Scale (`exam2` X13, X14)**.
5. **Uppercase Tilde Composites & Extended Latin Diacritics (`exam2` X09 Pages 19, 21)**.
6. **Nav/TOC Antialiased Underlines (`probe` p.2, `exam1` p.2, `exam2` p.2)**.
7. **Table Header Mid-Word Break in Narrow Columns (`page.py:add_table`)**.


## Stage G Boundary Hardening (`kindle_render/ir.py`, `tools/test_boundary.py`)
- **Round-Trip IR Deserialization (`from_dict` / `from_json`)**: `PositionedDocument.from_dict`, `PositionedPage.from_dict`, and `_cmd_from_dict` reconstruct all IR commands (`GlyphCommand`, `RectCommand`, `RuleCommand` including subpixel `link_underline` coordinates, `RingBulletCommand`, and `ImageCommand` via `image_store`) from canonical JSON/dict representations while preserving identical `layout_sha256()` digests across all 369 rendered pages.
- **IR Schema & Coordinate Invariant Validation (`validate_ir_page` / `validate_ir_document`)**: Validates schema version (`1.0`), positive page dimensions, monotonic page numbering, valid command discriminators, non-negative bounds (`x1 >= x0`, `y1 >= y0`), RGB channels in `[0, 255]`, and finite subpixel coordinates.
- **Boundary Test Suite (`tools/test_boundary.py`)**: Enforces `check_imports()`, zero IR validation errors, 100% `layout_sha256()` round-trip preservation on all 369 pages across all 5 corpora, and 100% pixel SHA-256 identity when rasterizing deserialized IR pages.
