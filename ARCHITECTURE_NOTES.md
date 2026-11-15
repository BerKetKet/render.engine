# ARCHITECTURE_NOTES.md — `kindle_render` v1.5.0 Handoff Reference

This document maps the architecture, coordinate rounding/snapping boundaries, calibration constants, configuration dependencies, mutable state, known failure modes, and binary dependencies of `kindle_render` at tag `prep-baseline-1.5.0`. It is written for the refactoring session that will split layout from rasterization and add a structured text layer while preserving rendered pixels.

---

## 1. Pipeline Map

```text
EPUB Archive (.epub)
  │
  ▼  [kindle_render/epub.py: load_epub (L183), _doc_blocks (L227)]
List[Block]  (Block dataclass: epub.py L22-L55; Run dataclass: layout.py L47-L63)
  │
  ▼  [kindle_render/page.py: render_blocks (L958) -> Pager.add_* (L203, L460, L568, L838, L900)]
  │  [kindle_render/layout.py: build_items (L269)]
List[Box | Glue | Penalty]  (layout.py L26-L45)
  │
  ▼  [kindle_render/layout.py: make_lines (L1059) -> _split_overwide_boxes (L1029)
  │   -> break_balanced_ragged (L550) / break_kp (L728) / _orig_break_kp (L595) / break_greedy (L982)]
List[Tuple[List[Box | Glue], Optional[Penalty], bool, bool]]  (line segments + terminal penalty)
  │
  ▼  [kindle_render/layout.py: layout_line (L1161)]
Tuple[List[Tuple], int]  (placements: (Face, glyph_name, x_off26[, adv26, style_meta]), nat_width26)
  │
  ▼  [kindle_render/page.py: Pager.add_text_block (L340-L458) -> Pager.draw_line (L101) -> Pager.draw_glyph (L78)]
  │  [kindle_render/raster.py: GlyphCache.get (L174) -> _ft_glyph (L230) / _own_glyph (L274)]
List[PIL.Image.Image]  (RGB uint8 page bitmaps, 1080x2400)
```

### Stage-by-Stage Ownership and Boundary Contracts

1. **Stage 1 — EPUB & CSS Parsing (`kindle_render/epub.py`)**:
   - **Entry point**: `load_epub(path, cfg) -> List[Block]` (`epub.py:183`).
   - **Internal helpers**: `_parse_css(text)` (`L64`), `_matches(sel, el)` (`L82`), `_style(el, rules)` (`L109`), `_em(val, cfg, pct_base_px, use_root_em)` (`L138`), `_doc_blocks(z, href, html, cfg)` (`L227`), `_collapse(runs)` (`L619`), `_load_img(z, href, tag)` (`L659`).
   - **Boundary output**: `List[Block]` (`epub.py:22-55`). Each `Block` carries:
     - `kind`: `"text" | "pre" | "table" | "image" | "hr"`
     - `runs`: `List[Run]` (`layout.py:47-63`), where each `Run` holds `text`, `bold`, `italic`, `image`, `scale`, `baseline_shift_em`, `small_caps`, `underline`, `strike`, `code`, `letter_spacing_em`, `word_spacing_em`, `fg`, `nowrap`, `from_text_transform`
     - Block geometry & metadata: `align`, `indent_em`, `left_em`, `right_em`, `scale`, `line_height`, `display`, `mt_em`, `mb_em`, `heading` (`0..6`), `next_is_heading`, `bullet`, `ol_number`, `list_level`, `page_break_before`, `hyphenate`, `lang`, `drop_cap_*`, `table_rows`, `table_caption`, `pre_lines`, `chapter` (spine document stem).

2. **Stage 2 — Itemization & Shaping (`kindle_render/layout.py` & `kindle_render/fonts.py`)**:
   - **Entry point**: `build_items(runs, family, cfg, size26, display, hyphenator, allow_hyphenation, lang) -> List[Box | Glue | Penalty]` (`layout.py:269`).
   - **Font shaping**: Calls `Face.shape(text, extra_track26)` (`fonts.py:406`), `Face.shape_arabic_word` (`fonts.py:232`), `Face.shape_devanagari_word` (`fonts.py:270`), and `_shape_token_with_fallbacks` (`layout.py:65`).
   - **Hyphenation**: Queries `LiangHyphenator.hyphenate_word(word)` (`hyphen.py:205`) and maps character break offsets `target_char` to shaped glyph cluster boundaries (`curr_char == target_char`, `layout.py:495-525`).
   - **Boundary output**: `List[Box | Glue | Penalty]` (`layout.py:26-45`) with all horizontal widths, stretches, and shrinks expressed in **26.6 fixed-point units** (`1 px = 64 units`). Each `Box.glyphs` element is a 3-tuple `(face, gname, adv26)` or 4-tuple `(face, gname, adv26, style_meta)`.

3. **Stage 3 — Line Breaking (`kindle_render/layout.py`)**:
   - **Entry point**: `make_lines(items, line_w, cfg, ragged, is_heading=False, align=None)` (`layout.py:1059`).
   - **Pre-pass**: `_split_overwide_boxes(items, line_w, cfg)` (`layout.py:1029`) splits any `Box` wider than `line_w(0)` into measure-fitting chunks separated by hyphen `Penalty` items.
   - **Solvers**:
     - Headings (`is_heading=True`) and centered blocks (`align="center"`): `break_balanced_ragged(items, line_w, w_last)` (`layout.py:550`), with fallback to `break_greedy` (`layout.py:982`).
     - Right-aligned blocks (`align="right"`): `break_greedy(items, line_w, cfg, ragged=False, allow_shrink=True)` (`layout.py:982`).
     - Body paragraphs (justified and `align="left"` ragged): `break_kp(items, line_w, tol, cfg, ragged)` (`layout.py:728`, bottom-up dynamic programming over break nodes with `TABLE_CONSEC`/`TABLE_WINDOW` hyphen ladder tables; delegates to `_orig_break_kp` at `L595` or `break_greedy` at `L753` when `n_items > 1000`).
   - **Boundary output**: List of `(seg, hy, is_last, is_forced)` tuples (`layout.py:1110-1160`), where `seg` is the slice of `Box`/`Glue` items on the line and `hy` is the terminal `Penalty` if broken at a penalty.

4. **Stage 4 — Line Justification & Placement (`kindle_render/layout.py`)**:
   - **Entry point**: `layout_line(seg, hy, width26, justify, last, cfg) -> Tuple[List[Tuple], int]` (`layout.py:1161`).
   - **Computation**: Computes optical margin overhang (`hang_left`, `hang_right`), micro-tracking adjustment (`tracking26`), and integer space distribution (`extra + (1 if idx < rem else 0)` or negative remainder from right to left), returning `placements` in 26.6 relative offsets from the line start `off26 = 0` and natural width `nat26`.

5. **Stage 5 — Pagination & Vertical Block Layout (`kindle_render/page.py`)**:
   - **Entry point**: `render_blocks(blocks, cfg, family, max_pages=None, return_meta=False)` (`page.py:958`) driving `Pager` (`page.py:37`).
   - **Block handlers**: `Pager.add_text_block` (`L203`), `Pager.add_pre` (`L460`), `Pager.add_table` (`L568`), `Pager.add_image` (`L838`), `Pager.add_hr` (`L900`), `Pager.add_error_placeholder_page` (`L913`).
   - **Boundary to raster**: Calls `Pager.draw_line(placements, start26, baseline)` (`page.py:101`) with `start26` in 26.6 fixed-point units and `baseline` in integer pixels.

6. **Stage 6 — Glyph Rasterization & Canvas Compositing (`kindle_render/page.py` & `kindle_render/raster.py`)**:
   - **Entry point**: `Pager.draw_line` (`page.py:101`) -> `GlyphCache.get(face, name)` (`raster.py:174`) -> `Pager.draw_glyph(g, x, baseline, fg_override)` (`page.py:78`).
   - **Canvas**: `self.canvas` is a `float32` array of shape `(screen_h, screen_w, 3)` converted to `uint8` via `np.clip(self.canvas + 0.5, 0, 255).astype(np.uint8)` in `Pager._to_image()` (`page.py:56`).

---

## 2. Pixel-Snapping and Rounding Map (26.6 <-> Pixel Boundary)

Every location where coordinates, advances, baselines, or margins are rounded, floored, ceiled, or converted between 26.6 fixed-point units (`1 px = 64 units`) and pixels:

### A. Font Advance & Shaping Quantization (`kindle_render/fonts.py`)
1. `Face.__init__` (`fonts.py:64`): Scale factor `self.S = size26 / self.upem` (float 26.6 units per font design unit).
2. `Face.adv26` (`fonts.py:375`): Unhinted glyph advance is floored to integer 26.6 units:
   `a = self._adv[name] = math.floor(raw_w * self.S)`
3. `Face.shape` (`fonts.py:411, 416`):
   - All-caps `cpsp` spacing: `cpsp_add26 = math.floor(self.cpsp_xadv * self.S)` (`L411`).
   - Pair kerning: `adv += math.floor(self.kern_units(n, g[i + 1]) * self.S)` (`L416`).
4. `Face.lsb26` (`fonts.py:428`): Left side bearing in 26.6: `int(math.floor(gl.xMin * self.S))`.
5. `Face.shape_arabic_word` (`layout.py:120`): Arabic pair kerning `adv += math.floor(ar_face.kern_units(gn, g_names[i_g + 1]) * ar_face.S)`.
6. `Face.shape_devanagari_word` (`fonts.py:290-292`): HarfBuzz positions converted via:
   - `x_adv26 = int(math.floor(poss[i].x_advance * self.S))` (`L290`)
   - `x_off_px = int(round((poss[i].x_offset * self.S) / 64.0))` (`L291`)
   - `y_off_px = int(round((poss[i].y_offset * self.S) / 64.0))` (`L292`).

### B. Itemization & Line-Justification Quantization (`kindle_render/layout.py`)
1. `_shape_token_with_fallbacks` (`layout.py:74, 82`):
   - Baseline shift: `dy_px = int(round(run.baseline_shift_em * (size26 / 64.0)))` (`L74`, also `L337`).
   - Small-caps font size: `int(round(size26 * 0.70))` (`L82`, also `L357`).
2. `build_items` (`layout.py:289-308, 373, 378`):
   - Inline image scaling: `w_sc = max(1, int(round(im.width * sc)))`, `h_sc = max(1, int(round(im.height * sc)))`, `w26 = int(round(im_scaled.width * 64))` (`L289-L293`).
   - Run font size: `r_size26 = int(round(size26 * getattr(run, 'scale', 1.0)))` (`L297`).
   - Letter/word spacing: `extra_track26 = int(round(run.letter_spacing_em * r_size26))` (`L307`), `extra_word26 = int(round(run.word_spacing_em * r_size26))` (`L308`).
   - Inter-word glue shrink: `sh_u = math.floor(sp * cfg.space_shrink)` (`L373, L378`).
3. `_hanging_overhang` (`layout.py:543, 547`) and `layout_line` (`layout.py:1176, 1180, 1184`):
   - Right/left optical overhang: `math.floor(cfg.optical_margin_ratio * width)`.
4. `layout_line` (`layout.py:1197-1271`):
   - `max_stretch = int(round(sum(seg[gi].stretch for gi in glues)))` (`L1197`).
   - `max_shrink = int(round(sum(seg[gi].shrink for gi in glues)))` (`L1198`).
   - Micro-tracking bounds: `min_t = int(round(cfg.tracking_min_em * ref_size26))`, `max_t = int(round(cfg.tracking_max_em * ref_size26))` (`L1210-L1211`), `tracking26 = max(min_t, -(need // n_Track))` (`L1220`), `tracking26 = min(max_t, need // n_Track)` (`L1225`).
   - Integer space distribution across `n_g` glues (`L1230-L1242`):
     - When `need >= 0`: `extra, rem = divmod(need, n_g)`; glue `idx` gets `extra + (1 if idx < rem else 0)` (left-to-right remainder).
     - When `need < 0`: `extra, rem = divmod(-need, n_g)`; glue `idx` gets `-(extra + (1 if (n_g - 1 - idx) < rem else 0))` (right-to-left remainder).
   - Post-hyphen kerning (`L1271`): `pen += math.floor(face.kern_units(name, nxt_g[1]) * face.S)`.

### C. Pagination, Baseline & Horizontal Placement Snapping (`kindle_render/page.py`)
1. `Pager.draw_line` (`page.py:102, 111, 120, 135`):
   - Line left overhang shift: `start26 += self.overhang(placements)` where `overhang = max(0, -face.lsb26(name))` (`L92-L102`).
   - **Glyph X pixel snapping (`L120`)**:
     `x = math.floor((start26 + off) / 64.0 + self.cfg.place_phase) + dx_px` (where `place_phase = 0.5`, equivalent to `floor(x_px + 0.5)`).
   - Inline image X/Y snapping (`L111-L112`):
     `x = math.floor((start26 + pen_off) / 64.0 + self.cfg.place_phase)`, `y = (baseline - im.height + 1) if (size26 == 2688 and x0 == 79) else (baseline - im.height + 6)`.
   - Underline / strikethrough X/Y snapping (`L135-L146`):
     `x_end = math.floor((start26 + off + adv26) / 64.0 + self.cfg.place_phase)`, `uy = baseline + dy_px + (5 if size26 <= 2688 else 4)`, `sy = baseline + dy_px - (11 if size26 <= 2688 else 14)`.
2. `Pager.pitch_for` & `Pager.baseline_in` (`page.py:148-154`):
   - `pitch_for(size26)`: `int(round(c.pitch_px() * (size26 / float(c.size26))))` (`L150`).
   - `baseline_in(line_top, pitch, size26)`: `line_top + int(round((pitch - px) / 2.0 + self.cfg.typo_ascender * px))` where `px = size26 / 64.0` (`L152-L154`).
3. `Pager.add_text_block` (`page.py:203-458`):
   - Block `size26 = int(c.size26 * b.scale + 1e-6)` (`L206`).
   - Custom `line-height` pitch: `pitch = int(round(b.line_height * vem_px * b.scale))`, `lh_top_delta = (lead_diff // 2) if (lead_diff >= 0 or std_body_pitch != 57) else -((-lead_diff) // 2)` (`L219-L223`).
   - Standard block pitch (`L226-L227`): `pitch = int(round(float(std_body_pitch) * b.scale))`, `pitch_fl = float(int(std_body_pitch * b.scale))` for `h2/h3` at `pitch=57`, `float(pitch)` for `b.heading == 0` or `std_body_pitch != 57`, and `float(std_body_pitch) * b.scale` for `h1, h4, h5, h6` at `pitch=57`.
   - Left margin & measure (`L240-L242`): `left_px = round(b.left_em * c.size_px())` when `list_level == 0 and b.left_em > 0` else `b.left_em * c.size_px()`; `width26 = int(round((c.right - c.x0 - left_px - b.right_em * c.size_px()) * 64))`.
   - First-line indent (`L288`): `indent26 = int(indent_em * size_px * 64)` when `indent_em > 0`, `int(round(indent_em * size_px * 64))` when `indent_em < 0`.
   - Center/right line offset (`L311-L314`): `off26 += int((line_w(i) - nat) / 2)` for `"center"`, `off26 += int(line_w(i) - nat)` for `"right"`.
   - Block top/bottom margins (`L329-L330`): `mt` and `mb_est` truncated via `int(val + 1e-6)` or rounded via `int(round(val))`.
   - Vertical cursor snapping (`L357, L362, L381, L395, L438, L448, L453`): `self.y_float` accumulates `gap` and `cur_pitch_fl`, snapping to integer `self.y = int(round(self.y_float))` after each line/gap.

### D. FreeType Outline Dilation & Bitmap Rounding (`kindle_render/raster.py`, `kindle_render/page.py`)
1. `GlyphCache._ft_glyph` (`raster.py:233-234, 256`):
   - Boldness dilation: `x_strength26 = int(round(dil_funits * face.S))`, `y_strength26 = int(round(0.80 * x_strength26))`.
   - Tilde component offset: `dx26 = int(round(getattr(c1, 'x', 0) * face.S))`.
2. `Pager._to_image` (`page.py:56`):
   - Final canvas float-to-uint8 conversion: `np.clip(self.canvas + 0.5, 0, 255).astype(np.uint8)`.

---

## 3. Calibration Inventory

Every hardcoded constant, table, or conditional branch in the engine:

| Location | Symbol / Branch | Value(s) | Derived From (Capture / Chapter) | Provenance |
|---|---|---|---|---|
| `config.py:40-44` | `size26`, `pitch_ratio` | `2688` (`42 px`), `57 / 42` | `probe` & `exam2` body text captures | `measured` |
| `config.py:46` | `typo_ascender` | `0.79` | Baseline position inside `57 px` / `68 px` line boxes (`probe` p.1, `exam1` p.2) | `measured` |
| `config.py:51-53` | `space_Stretch`, `space_shrink` | `0.50`, `0.34` | Justified prose line breaks in `probe`, `exam1`, `exam2` (`X11`, `X16`) | `fitted` |
| `config.py:57-59` | `tolerance`, `hyphen_penalty`, `ragged_hyphen_penalty` | `2.0`, `50`, `100` | Knuth-Plass break decisions across `probe` and `exam2` `X11`/`X16` | `fitted` |
| `config.py:60` | `ragged_shortfall` | `140.0` | Ragged-right paragraph wrapping (`exam1` E03, `exam2` X02/X11) | `fitted` |
| `config.py:63` | `place_phase` | `0.5` | Subpixel 26.6-to-integer pixel rounding phase across all captures | `measured` |
| `config.py:65-75` | `heading_scale`, `heading_margin_*` | `(1.5, 1.3, 1.15, 1.0, 0.83, 0.75)` | `exam1` E09 & `exam2` X10 heading ladders (`h1..h6`) | `measured` |
| `config.py:92-94` | `left_hyphen_min`, `right_hyphen_min`, `min_word_length` | `2`, `2`, `5` | `exam1` E04 & `exam2` X11 hyphenation sections | `measured` |
| `config.py:99-101` | `micro_tracking`, `tracking_min_em`, `tracking_max_em` | `False`, `-0.014`, `0.0` | Disabled by default (`False`); bounds fitted on tight lines | `fitted` |
| `config.py:113` | `img_px_scale` | `1.80` (`28.8 / 16.0`) | Block image dimensions in `probe` p.88 & `exam2` X12/X16 | `measured` |
| `config.py:121-123` | `ul_indent_em`, `ul_nested_indent_em`, `ol_indent_em` | `2.0`, `1.9762`, `2.0952` | `exam1` E11, `probe` p.87, `exam2` X03/X12 list gutters | `measured` |
| `config.py:143` | `vem_px()` | `self.pitch_px() / 1.2` | Vertical CSS `em` unit at pitch `57` (`47.5 px`) and pitch `68` (`56.67 px`) | `measured` |
| `config.py:147` | `base_root_em_px()` | `32.0` (`size26==2880`) else `28.8` | `.in2`/`.in4` in `exam1` and `.hang`/`.lm3`/`.rm3` in `exam2` X06/X13 | `measured` |
| `config.py:151-153` | `boldness_dilation_funits()` | `(0, 12, 24, 38, 52, 68)` | FreeType outline emboldening table across boldness levels | `fitted` |
| `epub.py:126-136` | `CSS_FONT_SIZE_KEYWORDS` | `0.6, 0.75, 8/9, 1.0, 1.2, 1.5, 2.0, 5/6, 1.2` | `exam2` X08 (p.18) and X13 (p.40) relative/keyword font sizes | `measured` |
| `epub.py:349-352` | `sup` / `sub` `baseline_shift_em` | `-14/37.5` or `-12/35`; `13/37.5` or `13/35` | `exam1` E08 & `exam2` X04/X13 superscript/subscript baselines | `measured` |
| `epub.py:464-465` | `.in2`, `.in4` at `size26 == 2880` | `3688 / 2880`, `7376 / 2880` | `exam1` indented blocks (`57.625 px`, `115.25 px`) | `measured` |
| `epub.py:471, 525` | `blockquote` / `dd` indent | `1.0 em` (`42 px`) vs `0.04725 * box_w` | `exam2` X12 p.35–36 (`42 px`) vs `probe` p.87 (`47.3 px`) | `measured` |
| `epub.py:553-556` | `lower-roman` / `upper-roman` `<ol>` indent | `132.0 / cfg.size_px()` | `exam2` X12 p.35 (`i., ii., iii., iv.` right-aligned at `x=200`, text at `x=211`) | `measured` |
| `layout.py:82, 357` | Small-caps scale factor | `0.70` | `exam1` E08 & `exam2` X13 `.sc` / `::first-line` small caps | `measured` |
| `layout.py:288` | Inline image scale factor | `2.625` (`42/16`) vs `img_px_scale` | `exam2` X12 p.39 (`i24.png -> 63x63`, `i60.png -> 158x158`) | `measured` |
| `layout.py:583` | `break_balanced_ragged` comma bonus | `-0.05` | Heading line breaks after comma in `exam2` X10 | `fitted` |
| `layout.py:725-726` | `TABLE_CONSEC`, `TABLE_WINDOW` | `(0, 1, 1.5, 2, 3, 5, 8, 13, 21)`, `(0, 0, 0, 1, 3, 8, 9, 10, 10)` | Consecutive/windowed hyphen penalties in `break_kp` | `measured` |
| `layout.py:884, 916-940` | `break_kp` constants | `G + 0.1`, shrink `150 * |r|^3`, stretch `100 * r^3`, ragged `0.61` | Justified and ragged line-breaking across `probe`, `exam1`, `exam2` | `measured` / `fitted` |
| `layout.py:1087` | `w_last_hd` heading weights | `0.15` (all-caps/colon-long), `0.7` (`h1..h3`), `0.62` (`h4..h6`) | `exam2` X10 heading ladders (`pages 22-28`, `106/106` lines) | `measured` |
| `page.py:15-21` | `_skia_bilerp_rgb` phase & scale | `x0=-0.009802, y0=-0.041117, 60680/65536` | Solitary cover image bilinear resampling on `probe` p.1 | `fitted` |
| `page.py:137-143` | Underline & strikethrough offsets | `uy = base + (5 or 4)`, `sy = base - (11 or 14)`, thickness `2 or 3` | `exam1` E08 & `exam2` X13 underline/strikethrough bands | `measured` |
| `page.py:213` | `is_spacer` (` ` paragraph) height | `40.0` (`pitch == 68`) else `std_body_pitch` | `exam1` spacer paragraphs vs `probe` | `measured` |
| `page.py:251-266` | Drop-cap geometry | `body_cap_h = 0.695` (`0.68` display), `gap = 0.18` (`0.15` display) | `exam1` & `exam2` X13 `.ini::first-letter` / `.dc::first-letter` | `measured` |
| `page.py:319-325` | `mt_tab57`/`mb_tab57`, `mt_tab`/`mb_tab` | `(63,58,54,63,65,73)` / `(63,59,54,63,65,73)` at pitch 57; `(76,71,66,75,79,88)` / `(75,70,67,75,79,89)` at pitch 68 | `exam2` X10 (`pages 22-28`) and `exam1` E09 (`pages 34-38`) heading ladders | `measured` |
| `page.py:334-345, 360` | Heading transition & page-top adjustments | `h1->h2: -1`, `h2->h2: 58`, `p->h1: +1`, `h3->p: +1`, `2-line h5: -1`, `3-line h3 top: +4` | `exam2` X04, X08, X10 (`pages 22-28`) | `measured` |
| `page.py:568-837` | `add_table` geometry & `0.70x` scale | `avail_w = right-x0-36`, `sc_tbl = 0.70` (`ncols>=4`), `col_ws=[363,163,165,195]`, `rule_w=887`, icon `95x53` | `exam2` X03 `Table 3.1` (p.8), `exam2` X12 table (p.36), `probe` table (p.88) | `measured` |
| `page.py:888` | `add_image` `y_draw = y - 1` | `y - 1` when `im.height < 2000` and `pitch == 57` | `exam2` X16 mid-page images (`pages 49, 53, 57, 61`) & X12 (`pages 36-38`) | `measured` |
| `raster.py:234, 242` | Anisotropic dilation & tilde split | `y_strength = 0.80 * x_strength`; `atilde, ntilde, otilde, itilde, utilde` | `exam2` X09 tilde glyphs (`ã, ñ, õ, ĩ, ũ`) | `measured` |

---

## 4. Config Dependency Map

Classification of `Config` fields (`kindle_render/config.py:28-131`) into **Device Constants** (fixed properties of the 1080×2400 capture device), **User Settings** (reader menu settings such as font size, line pitch, page margins, boldness, color theme), and **Engine Constants** (layout/shaping parameters):

| `Config` Field | Category | Default | Where Read |
|---|---|---|---|
| `screen_w`, `screen_h` | **Device Constant** | `1080`, `2400` | `page.py`: `Pager.new_page` (`L68`), `_draw_list_marker` (`L179, L185`), `add_image` (`L845-L850`) |
| `size26` | **User Setting** | `2688` (`42 px`) | `config.py:134`, `epub.py:148, 349, 463, 471, 507, 525, 565`, `page.py:137, 149, 206, 462, 571, 650, 888` |
| `pitch`, `pitch_ratio` | **User Setting** | `0`, `57 / 42` | `config.py:136-139, 143`, `cli.py:78-80`, `page.py:150, 208` |
| `x0`, `right` | **User Setting** | `39`, `1041` | `epub.py:245, 471, 525, 565`, `layout.py:288, 315`, `page.py:159, 242, 434, 465, 538, 579, 861, 905` |
| `top`, `page_bottom` | **User Setting** | `168`, `2203` | `page.py:70-71, 349, 375, 383, 540, 629, 783, 879, 904, 1006` |
| `boldness_level` | **User Setting** | `0` | `config.py:150`, `fonts.py:473, 487, 513` |
| `bg`, `fg`, `palette` | **User Setting** | `(255,255,255)`, `(0,0,0)`, `"default"` | `config.py:155`, `page.py:69, 88, 136, 179, 185` |
| `typo_ascender` | **Engine Constant** | `0.79` | `page.py:154` (`Pager.baseline_in`) |
| `fractional_pitch_snapping` | **Engine Constant** | `True` | `page.py:436, 1014` |
| `space_Stretch`, `space_shrink` | **Engine Constant** | `0.50`, `0.34` | `layout.py:372-378` (`build_items`) |
| `breaker`, `tolerance`, `hyphen_penalty`, `ragged_hyphen_penalty`, `ragged_shortfall`, `ragged_greedy` | **Engine Constant** | `"kp"`, `2.0`, `50`, `100`, `140.0`, `False` | `layout.py:674, 679, 919, 1051, 1100-1102` |
| `ladder2`, `ladder3`, `fitness_gap` | **Engine Constant** | `3000.0`, `10000.0`, `1000.0` | `layout.py:691-697` (`_orig_break_kp`) |
| `place_phase`, `overhang_shift`, `exact_raster` | **Engine Constant** | `0.5`, `False`, `True` | `page.py:42, 92, 111, 120, 135` |
| `heading_scale`, `heading_margin_top_em`, `heading_margin_bottom_em`, `heading_top_extra_px`, `heading_right_margin_em`, `margin_at_page_top` | **Engine Constant** | tuples / `7` / `0.0` / `True` | `epub.py:500, 507-508, 514`, `page.py:359-360, 378-379, 392-393` |
| `optical_sizing`, `display_threshold_px`, `use_display_for_headings` | **Engine Constant** | `True`, `52.0`, `False` | `epub.py:501-502`, `page.py:249` |
| `hyphenate`, `left_hyphen_min`, `right_hyphen_min`, `min_word_length`, `hyphen_dic_path` | **Engine Constant** | `True`, `2`, `2`, `5`, `None` | `config.py:159`, `page.py:232-238, 709` |
| `micro_tracking`, `tracking_min_em`, `tracking_max_em` | **Engine Constant** | `False`, `-0.014`, `0.0` | `layout.py:1208-1211` (`layout_line`) |
| `widow_orphan`, `para_gap_em`, `indent_em` | **Engine Constant** | `2`, `0.0`, `0.0` | `page.py:282, 386-388, 455` |
| `optical_margin_alignment`, `optical_margin_ratio` | **Engine Constant** | `True`, `0.35` | `layout.py:540-547, 1173-1184` |
| `css_px_scale`, `img_px_scale` | **Engine Constant** | `1.80`, `1.80` | `epub.py:154, 156`, `layout.py:288`, `page.py:857` |
| `ul_indent_em`, `ul_nested_indent_em`, `ol_indent_em` | **Engine Constant** | `2.0`, `1.9762`, `2.0952` | `epub.py:564, 568-569` |
| `liga`, `kern`, `cpsp` | **Engine Constant** | `True`, `True`, `True` | `fonts.py:472` (`Family.face`) |

---

## 5. Global/Mutable State, Caches, and Chapter-Independence Hazards

When refactoring toward chapter-independent or parallel layout, account for the following caches and stateful dependencies:

1. **Process-Global Caches & Native Handles**:
   - `LiangHyphenator._cache: Dict[Tuple[str, int, int, int], LiangHyphenator]` (`hyphen.py:20`): Class-level dictionary keyed on `(abs_path, left_min, right_min, min_word_len)`. Read-only after initialization; thread-safe for concurrent reads once populated.
   - `_ft_lib_handle` and `_ft_cdll` (`raster.py:23, 124`): Module-level ctypes `FT_Library` singleton. **Not thread-safe**: `FT_New_Face`, `FT_Set_Pixel_Sizes`, and `FT_Load_Glyph` mutate the shared `FT_Library` / `FT_Face` slot if called concurrently across threads without a lock or per-thread `FT_Library`.
   - `_hb_cdll` (`fonts.py:9`): Module-level HarfBuzz ctypes handle; creates and destroys per-call `hb_blob_t`/`hb_face_t`/`hb_font_t`/`hb_buffer_t` in `Face.shape_devanagari_word` (`fonts.py:276-309`).
2. **Per-`Family` and Per-`Pager` Caches**:
   - `Family.cache: Dict[Tuple, Face]` (`fonts.py:461`) and `Face._adv: Dict[str, int]` (`fonts.py:66`): Per-`Family` instance cache of loaded `TTFont` tables and glyph advances.
   - `Pager.cache: GlyphCache` (`page.py:42`, `raster.py:168`): Per-`Pager` cache keyed on `(face.path, face.size26, face.boldness_level, gname)`.
3. **Cross-Block & Cross-Chapter State in `Pager` (`page.py:37-76`)**:
   - In `epub.py:602`: Each spine XHTML file sets `out[0].page_break_before = True`. Because every spine document forces a page break before its first block (`page.py:276, 879`), layout and pagination are **naturally chapter-independent across spine documents**, provided each chapter starts on a fresh page (`self.page_empty = True`, `self.prev_mb = 0`, `self.prev_kind = None`, `self.prev_heading = 0`, `self.prev_heading_lines = 0`).
   - **Hazard**: If a spine document has `out[0].page_break_before == False` (currently never happens in `load_epub`), `self.y`, `self.y_float`, `self.prev_mb`, `self.prev_kind`, `self.prev_heading`, and `self.prev_heading_lines` carry across blocks.
   - **In-place `Run` / `Glue` Mutation**:
     - `epub.py:261`: `flush()` mutates `runs[0].text = first_txt[1:]` when extracting a `::first-letter` drop cap.
     - `layout.py:1072, 1077`: `make_lines()` mutates `items[-2].non_breaking = True` and `items[idx + 1].non_breaking = True` in place on the `items` list.

---

## 6. Known Failure Modes (Ordered by Evidence)

1. **Last-Glyph 1 px Horizontal Offset on Justified Lines (`probe`, `exam1`, `exam2`)**:
   - **Evidence**: On non-exact pages of `probe` (e.g., pages 6–9, 11, 16–18, 22–24, 28–30 where `diff_pixels` is `460..1680`) and across multiple lines in `exam1` and `exam2`, the last word or glyph on a justified line sits `1 px` to the right (or `1 px` to the left) of the device capture.
   - **Mechanism**: In `layout_line` (`layout.py:1230-1242`), integer remainder `rem = need % n_g` distributes `+1` unit (`1/64 px`) strictly left-to-right across the first `rem` spaces (or right-to-left when shrinking), and `Face.adv26` (`fonts.py:375`) uses `math.floor(raw_w * self.S)` rather than accumulating sub-26.6 fractional advances or device fixed-point space distribution. When total line width `start26 + off` lands within `1/64 px` of a half-pixel boundary (`place_phase = 0.5`), `math.floor((start26 + off) / 64.0 + 0.5)` flips by `1 px`.
2. **Heading Page-Fill & Page-Top Margin Differences at `pitch = 68` (`exam1` E09 Pages 34–38)**:
   - **Evidence**: While `exam2` X10 (`pages 22–28`, `size26=2688, pitch=57`) is `7/7` (`100%`) bitwise-exact (`106/106` lines), `exam1` E09 (`pages 34–38`, `size26=2880, pitch=68`) has vertical drift and page-fill differences on multi-line heading ladders.
   - **Mechanism**: `page.py:318-345` has calibrated transition adjustments (`h1->h2`, `h2->h2`, `p->h1`, `h3->p`, `2-line h5`, `3-line h3` page-top extra) gated on `std_body_pitch == 57`, whereas `std_body_pitch == 68` uses static `mt_tab = (76, 71, 66, 75, 79, 88)` and `mb_tab = (75, 70, 67, 75, 79, 89)` without the corresponding `pitch=68` transition adjustments or `h2/h3` integer pitch truncation.
3. **Hyphenation-Point & Tightness Differences on Specific Words (`exam2` X09, X11, X16; `exam1` E04)**:
   - **Evidence**:
     - `exam2` X16 page 51 (`diff_pixels = 30,683`), page 52 (`20,894`), page 55 (`24,562`), page 62 (`65,582`, where device breaks `"Govern-/esss"` vs. render `"Gov-/ernesss"`), page 63 (`51,389`), page 64 (`21,045`).
     - `exam2` X11 page 32 (`13,298` diff px) and page 33 (`18,900` diff px).
     - Words containing apostrophes (`layout.py:283` `token_re` keeps apostrophes inside the token passed to `LiangHyphenator.hyphenate_word` at `layout.py:456`, where `.isalpha()` is `False` for `'`/U+2019 unless stripped or split).
4. **Inline `<mark>` Highlight & Inline `<code>` / Mixed-Size Metrics (`exam2` X13 Pages 40–41, X14 Pages 42–43)**:
   - **Evidence**: `exam2` X13 (`pages 40–41`, `diff_pixels = 450,518`, `33/56` PI-lines) and X14 (`pages 42–43`, `diff_pixels = 141,663`).
   - **Mechanism**:
     - `<mark>` background highlight box is not yet drawn in `epub.py` / `page.py`.
     - Inline `<code>` (`DroidSansMono.ttf`) inside running prose uses `r_size26 = size26` (`layout.py:299`) without monospace-to-serif optical scale adjustment, shifting line breaks in paragraphs containing inline `<code>`.
     - Thai script in `exam2` X14 (page 43) has no spaces between words and requires dictionary-based Thai word-break segmentation (`icu` / maximal matching) before `build_items`.
5. **Tilde Mark Rendering on Uppercase & Non-Bookerly Faces (`exam2` X09 Pages 19, 21)**:
   - **Evidence**: `exam2` X09 (`pages 19–21`, `1/3` exact pages; page 19 has `67,853` diff px and page 21 has `246,796` diff px).
   - **Mechanism**: `GlyphCache._ft_glyph` (`raster.py:242`) applies separate-component light autohinting only to the 5 lowercase composites `('atilde', 'ntilde', 'otilde', 'itilde', 'utilde')`; uppercase tilde composites (`Atilde`, `Ntilde`, `Otilde`, `Itilde`, `Utilde`) and precomposed/combining sequences in extended Latin languages on pages 19 and 21 are still hinted as single composite outlines.
6. **Nav/TOC Link Text 1 px Offset & Antialiased Underlines (`probe` Page 2, `exam1` Page 2, `exam2` Page 2)**:
   - **Evidence**: Page 2 (`nav.xhtml`) across all three corpora (`probe` p.2 `46,056` diff px; `exam1` p.2 `28,375` diff px; `exam2` p.2 `55,007` diff px).
   - **Mechanism**: `Pager.draw_line` (`page.py:137-141`) draws link underlines as a solid `fg_col` rectangle of integer height `2 px` (`size26 <= 2688`) or `3 px` (`size26 > 2688`), whereas the device renders underlines with vertical antialiasing (fractional top/bottom edge coverage) and a `1 px` vertical/horizontal link offset in `<nav epub:type="toc">`.
7. **Nested List, Blockquote, and Table Cell Geometry (`exam1` E11 Pages 46–48, `probe` E3 Pages 87–88, `exam2` X03/X12)**:
   - **Evidence**: `exam1` pages 46–48 (`58,331`, `154,884`, `558,497` diff px), `probe` pages 87–88 (`60,934`, `134,093` diff px), `exam2` X03 (`70,608` diff px) and X12 (`718,629` diff px).
   - **Mechanism**: Multi-level nested list markers (`<ul>` inside `<ol>` and level-2/3 bullets `◦`/`▪` drawn procedurally at `page.py:172-186`), `<figure>/<figcaption>` spacing in `exam1` p.48, and bilinear vs. Skia fixed-point resampling on non-cover block images (`page.py:876` uses `im.resize(..., Image.BILINEAR)` instead of `_skia_bilerp_rgb`).

---

## 7. Dependencies and Determinism

1. **FreeType (`libfreetype.so.6`, version `2.12.1` loaded via `ctypes`)**:
   - Loaded in `kindle_render/raster.py:20-25` via `ctypes.util.find_library('freetype')` (verified version `2.12.1` in `tools/reports/manifest.json`).
   - Uses `FT_LOAD_DEFAULT | FT_LOAD_NO_BITMAP | FT_LOAD_TARGET_LIGHT` (`0x10008`, `raster.py:189`) and `FT_RENDER_MODE_LIGHT` (`1`, `raster.py:200`), plus `FT_Outline_Translate` and `FT_Outline_EmboldenXY` (`raster.py:194-198`).
   - **Determinism note**: FreeType's light autohinter is deterministic for a fixed FreeType version (`2.12.1`), font binary, and `size26`, but minor autohinter changes across major FreeType releases can alter gray coverage values by `1..2` levels.
2. **HarfBuzz (`libharfbuzz.so.0`, loaded via `ctypes`)**:
   - Loaded in `kindle_render/fonts.py:9` via `ctypes.CDLL("libharfbuzz.so.0")`.
   - Used **only** in `Face.shape_devanagari_word` (`fonts.py:270-311`) when shaping Devanagari script runs (`ऀ..ॿ`, `exam2` X14 page 42). All Latin, Greek, Cyrillic, Arabic, Hebrew, CJK, and Ethiopic runs are shaped directly in Python via `fontTools` (`cmap`/`hmtx`/`kern`/`GPOS`/`GSUB`).
3. **Pillow (`PIL.Image.BILINEAR`) & NumPy (`float32` / `float64`)**:
   - Block and inline images use `PIL.Image.Image.resize(..., Image.BILINEAR)` (`layout.py:292`, `page.py:876`), while solitary cover images use `_skia_bilerp_rgb` (`page.py:16-35`, pure NumPy `float64`).
   - Double-render determinism is verified across all three corpora (`probe`, `exam1`, `exam2`) by `tools/corpus.py`: rendering twice produces bitwise-identical SHA-256 hashes on every page.
