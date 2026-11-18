# Numerics & Determinism Inventory (`kindle_render` v1.11.5)

This document catalogs every site in `kindle_render/*.py` where numeric representation, rounding, library kernels, container ordering, or Unicode data could cause a Rust (or other) port to diverge from bit-exact `v1.11.5` output. Each entry is tagged with its arithmetic type: **`int`**, **`f64`** (Python `float` / `np.float64`), or **`f32`** (`np.float32`).

---

## 1. `float32` (`f32`) and Fixed-Point / `numpy` Dtypes
- **16.16 fixed-point font scale (`fonts.py:Face.__init__`, `adv26`, `kern_units`, `lsb26`, `shape_cluster`)**:
  - `S = round((size26 / 64.0) / upem * 65536.0) / 65536.0` (`f64`, quantized to `1/65536` steps).
  - Glyph advances (`math.floor(raw_w * self.S)`), kerning (`math.floor(ku * self.S)`), and HarfBuzz `x_advance` (`int(math.floor(poss[i].x_advance * self.S))`) multiply `int` font units by `S` (`f64`) and floor to `int` 26.6 units (`int`).
- **Justified-line pen accumulation (`layout.py:layout_line`, line 1336)**:
  - `f32 = np.float32`: `g_pen_fl` accumulates `f32(w_acc) + f32(sp26_fl)` in IEEE-754 **32-bit float (`f32`)**, then converts via `int(math.floor(float(g_pen_fl) / 64.0 + 0.5))` (`f64` cast for division/floor).
  - *Porting note*: Must use `f32` accumulation with exact `f32` rounding before `f64` division by `64.0` + `0.5` floor; `f64` accumulation changes tie-break pixels on justified lines.
- **Rasterizer canvas & alpha blending (`raster.py:Rasterizer.rasterize_page`, `_draw_glyph_on_canvas`)**:
  - `canvas` is `np.empty((H, W, 3), dtype=np.float32)` (`f32`).
  - Glyph coverage `cov = g.cov.astype(np.float32) / 255.0` (`f32`), blended linearly in `f32`: `dst + (fg - dst) * cov[..., None]`.
  - Anti-aliased `RectCommand` (`raster.py:427-431`) computes coverage `cx`, `cy` in `f32` (`np.arange(..., dtype=np.float32)`).
  - Final quantization (`raster.py:455`): `np.clip(canvas + 0.5, 0, 255).astype(np.uint8)` (`f32` add `0.5`, clamp `[0, 255]`, truncate to `uint8`).
- **Skia-calibrated bilinear image resampler (`page.py:_skia_bilerp_rgb`)**:
  - Computes in `np.float64` (`f64`): `np.floor(ys).astype(int)`, bilinear weights, and `np.round(val).astype(np.uint8)` (banker's rounding in `f64` before `uint8` cast).

---

## 2. Rounding Semantics: Python `round()` vs `floor(x + 0.5)` vs `int()` Truncation
Python's built-in `round(x)` uses **round-half-to-even (banker's rounding)** on `f64`, whereas `int(math.floor(x + 0.5))` is **round-half-up (toward `+inf`)**, and `int(x)` is **truncation toward zero**.

- **Banker's `round()` (`f64 -> int`)**:
  - `fonts.py:Face.shape_cluster` (`x_off_px`, `y_off_px`), `glyph_bbox_px` (`gx1`).
  - `layout.py:build_items` (`dy_px`, `sc_face` `size26 * 0.70`, `w_sc`, `h_sc`, `w26`, `r_size26`, `extra_track26`, `extra_word26`, `0.0536 * r_size26`), `layout_line` (`max_stretch`, `max_shrink`, `min_t`, `max_t`).
  - `page.py:Page.pitch_in`, `baseline_in`, `add_text_block` (`mt`, `mb_est`, `gap` in `prev_h == 1`, `self.y = int(round(self.y_float))`, `width26`, `indent26` when `< 0`, `drop_size26`, `drop_gap26`, `line_base_x26`), `add_table` (`tbl_size26`, `line_p`, `col_ws`, `wrap_line_p`, `im_x`, `im_y`), `add_hr` (`g_top`, `by0`), `add_image` (`target_w`, `target_h`, `mt_px`, `gap`), `render_blocks` (`pg.y`).
  - `raster.py:Rasterizer.glyph` (`x_strength26`, `y_strength26`, `dx26`).
  - `ir.py:RectCommand.to_dict` (`round(float(...), 6)`).
- **`math.floor(x + 0.5)` (`f64 -> int`, half-up)**:
  - `config.py:Config.pitch_px` (`int(math.floor(self.pitch_ratio * self.size_px() + 0.5))`).
  - `page.py:_round_half_up` (`int(math.floor(x + 0.5))`), used in `add_image` (`x0_sn`, `x1_sn`, `target_h`, `target_w * scale_rem`).
  - `layout.py:layout_line` (`x_fl`, `x_int` with `cfg.place_phase`).
- **`math.floor(x)` / `math.ceil(x)` (`f64 -> int`)**:
  - `fonts.py`: `adv26`, `cpsp_add26`, `kern_units`, `lsb26`, `glyph_bbox_px` (`gx0`, `gx1`, `gy0`, `gy1`).
  - `layout.py`: `sh_u` (`space_shrink`), `k_adv`, `hang_left` / `hang_right`.
  - `page.py:Page.draw_line` (`x0_bg`, `x1_bg`, `y1_bg`, `x`, `x_end`), `add_text_block` (`mb_est` when `mb_em != 1.0`), `add_hr` (`rule_y_float`).
  - `raster.py`: fallback `glyph` (`left`, `right`, `bot`, `top`), `rasterize_page` (`ix0`, `ix1`, `iy0`, `iy1`).
- **`int(x)` truncation toward zero (`f64 -> int`)**:
  - `page.py:add_text_block`: `indent26 = int(indent_em * size_px * 64)` when `indent_em > 0` (`f64` truncated), `pitch = int(b.line_height * vem_px * b.scale + 1e-6)` when `1.5 < b.line_height < 2.0`, `mt = int(b.mt_em * vem_px * b.scale + 1e-6)` / `int(b.mt_em * eff_vem * b.scale + 0.25)`, `mb_est = int(b.mb_em * vem_px * b.scale + 0.4)` when `b.mb_em == 1.0`, `extra_asc_r = int((sc_r - 1.0) * vem_px)`, `lp_r`, `add_image` (`gap = int(c.vem_px() - 1.5)` / `self.prev_mb = int(c.vem_px() + 0.5)`).
- **`//` and `%` on integers**:
  - Integer division `//` and modulo `%` in `kindle_render/*.py` operate on non-negative pixel/26.6 coordinates; negative values are passed to `math.floor()` explicitly rather than relying on Python's floor-division `//`.

---

## 3. PIL / NumPy Numeric & Resampling Dependence
- **Image resizing (`layout.py:298`, `page.py:1501`)**: `im.resize((w, h), Image.BILINEAR)` (Pillow 10.2.0 2-pass separable bilinear filter with Pillow's exact center-offset and uint8 rounding).
  - *Porting note*: Pillow `BILINEAR` differs subtly from Skia/libpng/image-rs bilinear kernels; bit-exact porting of image pages requires matching Pillow 10.2.0's `ImagingResampleHorizontal`/`Vertical` weights or pre-storing resampled image bytes in IR.
- **FreeType glyph rasterization (`raster.py:274, 292`)**: `FT_LOAD_DEFAULT | FT_LOAD_NO_HINTING` + `FT_RENDER_MODE_NORMAL` (256-level grayscale anti-aliased bitmap) with `FT_Outline_EmboldenXY` when `boldness_level > 0`. Must match FreeType `2.12.1` (`requirements.lock`).
- **No PIL gamma tables or `np.rint`**: Gamma = `1.0` (linear RGB blending in `f32`). `np.rint` is not used (`np.round` is used once in `page.py:49`).

---

## 4. Container Ordering, Unicode Database, Locale, Time & Randomness
- **Dict/Set ordering**:
  - Python 3.7+ preserves insertion order for `dict`; `set` iteration order is NEVER used to order layout items, glyphs, or IR commands (`sorted(...)` is used wherever sets are serialized). Verified across `PYTHONHASHSEED` values by `tools/test_determinism.py`.
- **Unicode database (`unicodedata`)**:
  - Used in `epub.py` (`unicodedata.normalize("NFC", ...)`), `layout.py` (`unicodedata.category`, `unicodedata.normalize`), and `text_layer.py`. Python 3.11 bundles Unicode `14.0.0`.
- **Locale, `time`, and `random`**:
  - Zero calls to `random`, `os.urandom`, `time.time()`, `datetime.now()`, or locale-dependent string formatting in `kindle_render/*.py`.
