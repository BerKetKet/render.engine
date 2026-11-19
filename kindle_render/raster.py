import os
"""Glyph bitmaps and IR page rasterization via FreeType FT_LOAD_TARGET_LIGHT (256-level grayscale).
Includes:
1. Checked ctypes FreeType return codes and FT_Library_Version introspection
2. Separate-component light autohinting for lowercase tilde composites (atilde, ntilde, otilde, itilde, utilde)
3. Anisotropic vector outline dilation (y_strength = 0.80 * x_strength)
4. Instance-owned Rasterizer and GlyphCache reading only PositionedPage / RenderCommand IR
"""
import ctypes
import ctypes.util
import math
from typing import Dict, Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageChops
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from .config import Config, BOLDNESS_FUNITS_RAMP
from .ir import (
    PositionedDocument,
    PositionedPage,
    GlyphCommand,
    RectCommand,
    RuleCommand,
    RingBulletCommand,
    ImageCommand,
)

try:
    import freetype
    HAVE_FT = True
    USE_CTYPES_FT = False
except Exception:
    freetype = None
    _ft_lib_path = ctypes.util.find_library('freetype')
    if _ft_lib_path:
        try:
            _ft_cdll = ctypes.CDLL(_ft_lib_path)
            HAVE_FT = True
            USE_CTYPES_FT = True
        except Exception:
            _ft_cdll = None
            HAVE_FT = False
            USE_CTYPES_FT = False
    else:
        _ft_cdll = None
        HAVE_FT = False
        USE_CTYPES_FT = False


def _check_ft(err: int, fn_name: str):
    if err != 0:
        raise RuntimeError(f"FreeType {fn_name} failed with error code {err}")


if USE_CTYPES_FT:
    class _FT_Generic(ctypes.Structure):
        _fields_ = [('data', ctypes.c_void_p), ('finalizer', ctypes.c_void_p)]

    class _FT_BBox(ctypes.Structure):
        _fields_ = [('xMin', ctypes.c_long), ('yMin', ctypes.c_long), ('xMax', ctypes.c_long), ('yMax', ctypes.c_long)]

    class _FT_Vector(ctypes.Structure):
        _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

    class _FT_Bitmap(ctypes.Structure):
        _fields_ = [
            ('rows', ctypes.c_uint),
            ('width', ctypes.c_uint),
            ('pitch', ctypes.c_int),
            ('buffer', ctypes.POINTER(ctypes.c_ubyte)),
            ('num_grays', ctypes.c_ushort),
            ('pixel_mode', ctypes.c_ubyte),
            ('palette_mode', ctypes.c_ubyte),
            ('palette', ctypes.c_void_p),
        ]

    class _FT_Glyph_Metrics(ctypes.Structure):
        _fields_ = [
            ('width', ctypes.c_long), ('height', ctypes.c_long),
            ('horiBearingX', ctypes.c_long), ('horiBearingY', ctypes.c_long), ('horiAdvance', ctypes.c_long),
            ('vertBearingX', ctypes.c_long), ('vertBearingY', ctypes.c_long), ('vertAdvance', ctypes.c_long),
        ]

    class _FT_Outline(ctypes.Structure):
        _fields_ = [
            ('n_contours', ctypes.c_short),
            ('n_points', ctypes.c_short),
            ('points', ctypes.POINTER(_FT_Vector)),
            ('tags', ctypes.c_char_p),
            ('contours', ctypes.POINTER(ctypes.c_short)),
            ('flags', ctypes.c_int),
        ]

    class _FT_GlyphSlotRec(ctypes.Structure):
        _fields_ = [
            ('library', ctypes.c_void_p),
            ('face', ctypes.c_void_p),
            ('next', ctypes.c_void_p),
            ('glyph_index', ctypes.c_uint),
            ('generic', _FT_Generic),
            ('metrics', _FT_Glyph_Metrics),
            ('linearHoriAdvance', ctypes.c_long),
            ('linearVertAdvance', ctypes.c_long),
            ('advance', _FT_Vector),
            ('format', ctypes.c_int),
            ('bitmap', _FT_Bitmap),
            ('bitmap_left', ctypes.c_int),
            ('bitmap_top', ctypes.c_int),
            ('outline', _FT_Outline),
        ]

    class _FT_FaceRec(ctypes.Structure):
        _fields_ = [
            ('num_faces', ctypes.c_long),
            ('face_index', ctypes.c_long),
            ('face_flags', ctypes.c_long),
            ('style_flags', ctypes.c_long),
            ('num_glyphs', ctypes.c_long),
            ('family_name', ctypes.c_char_p),
            ('style_name', ctypes.c_char_p),
            ('num_fixed_sizes', ctypes.c_int),
            ('available_sizes', ctypes.c_void_p),
            ('num_charmaps', ctypes.c_int),
            ('charmaps', ctypes.c_void_p),
            ('generic', _FT_Generic),
            ('bbox', _FT_BBox),
            ('units_per_EM', ctypes.c_ushort),
            ('ascender', ctypes.c_short),
            ('descender', ctypes.c_short),
            ('height', ctypes.c_short),
            ('max_advance_width', ctypes.c_short),
            ('max_advance_height', ctypes.c_short),
            ('underline_position', ctypes.c_short),
            ('underline_thickness', ctypes.c_short),
            ('glyph', ctypes.POINTER(_FT_GlyphSlotRec)),
        ]


def get_freetype_version() -> str:
    if USE_CTYPES_FT and _ft_cdll is not None:
        lib = ctypes.c_void_p()
        _check_ft(_ft_cdll.FT_Init_FreeType(ctypes.byref(lib)), "FT_Init_FreeType")
        try:
            maj, min_, pat = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
            _ft_cdll.FT_Library_Version(lib, ctypes.byref(maj), ctypes.byref(min_), ctypes.byref(pat))
            return f"{maj.value}.{min_.value}.{pat.value}"
        finally:
            if hasattr(_ft_cdll, "FT_Done_FreeType"):
                _ft_cdll.FT_Done_FreeType(lib)
    if HAVE_FT and freetype is not None:
        v = freetype.version()
        return f"{v[0]}.{v[1]}.{v[2]}"
    return "fallback"


class _Pen(BasePen):
    def __init__(self, gs):
        super().__init__(gs)
        self.contours, self.cur = [], []
    def _moveTo(self, p): self.cur = [p]
    def _lineTo(self, p): self.cur.append(p)
    def _curveToOne(self, a, b, c):
        p0 = self.cur[-1]
        for i in range(1, 9):
            t = i / 8.0; u = 1 - t
            self.cur.append((u**3*p0[0]+3*u*u*t*a[0]+3*u*t*t*b[0]+t**3*c[0],
                             u**3*p0[1]+3*u*u*t*a[1]+3*u*t*t*b[1]+t**3*c[1]))
    def _qCurveToOne(self, a, b):
        p0 = self.cur[-1]
        for i in range(1, 9):
            t = i / 8.0; u = 1 - t
            self.cur.append((u*u*p0[0]+2*u*t*a[0]+t*t*b[0], u*u*p0[1]+2*u*t*a[1]+t*t*b[1]))
    def _closePath(self):
        if len(self.cur) > 2: self.contours.append(self.cur)
        self.cur = []
    _endPath = _closePath


class Glyph:
    __slots__ = ("cov", "left", "top")
    def __init__(self, cov, left, top):
        self.cov, self.left, self.top = cov, left, top


class _RasterFontMeta:
    """Per-instance font table metadata used by GlyphCache when rasterizing IR commands."""
    def __init__(self, path: str):
        self.path = path
        self.tt = TTFont(path)
        self.upem = self.tt['head'].unitsPerEm
        self.glyf = self.tt['glyf'] if 'glyf' in self.tt else None
        self.order = self.tt.getGlyphOrder()
        self.gid = {n: i for i, n in enumerate(self.order)}


class GlyphCache:
    """Instance-owned FreeType handle and glyph bitmap cache (zero shared module state)."""
    def __init__(self, exact=True):
        self.exact = exact and HAVE_FT
        self.warned = False
        self._ft, self._gs, self._c = {}, {}, {}
        self._font_meta: Dict[str, _RasterFontMeta] = {}
        self._ft_lib = None
        if self.exact and USE_CTYPES_FT and _ft_cdll is not None:
            self._ft_lib = ctypes.c_void_p()
            _check_ft(_ft_cdll.FT_Init_FreeType(ctypes.byref(self._ft_lib)), "FT_Init_FreeType")

    def close(self):
        if USE_CTYPES_FT and _ft_cdll is not None and self._ft_lib:
            if hasattr(_ft_cdll, "FT_Done_Face"):
                for f in self._ft.values():
                    if f:
                        _ft_cdll.FT_Done_Face(f)
            self._ft.clear()
            if hasattr(_ft_cdll, "FT_Done_FreeType"):
                _ft_cdll.FT_Done_FreeType(self._ft_lib)
            self._ft_lib = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def _get_font_meta(self, path: str) -> _RasterFontMeta:
        m = self._font_meta.get(path)
        if m is None:
            m = self._font_meta[path] = _RasterFontMeta(path)
        return m

    def get(self, face, name):
        bold_lvl = getattr(face, 'boldness_level', 0)
        key = (face.path, face.size26, bold_lvl, name)
        if key in self._c:
            return self._c[key]
        g = self._ft_glyph(face, name) if self.exact else self._own_glyph(face, name)
        self._c[key] = g
        return g

    def get_by_params(self, font_path: str, size26: int, boldness_level: int, glyph_name: str, glyph_id: int) -> Optional[Glyph]:
        key = (font_path, size26, boldness_level, glyph_name)
        if key in self._c:
            return self._c[key]
        g = self._ft_glyph_params(font_path, size26, boldness_level, glyph_name, glyph_id) if self.exact else self._own_glyph_params(font_path, size26, glyph_name)
        self._c[key] = g
        return g

    def _load_single_ft(self, f, gid: int, x_strength26: int, y_strength26: int, dx26: int = 0, dy26: int = 0):
        if USE_CTYPES_FT:
            _check_ft(_ft_cdll.FT_Load_Glyph(f, gid, (1 << 16) | 32), "FT_Load_Glyph")
            slot = f.contents.glyph
            if x_strength26 > 0:
                if hasattr(_ft_cdll, 'FT_Outline_EmboldenXY'):
                    _check_ft(_ft_cdll.FT_Outline_EmboldenXY(
                        ctypes.byref(slot.contents.outline),
                        ctypes.c_long(x_strength26),
                        ctypes.c_long(y_strength26)
                    ), "FT_Outline_EmboldenXY")
                else:
                    _check_ft(_ft_cdll.FT_Outline_Embolden(
                        ctypes.byref(slot.contents.outline),
                        ctypes.c_long(x_strength26)
                    ), "FT_Outline_Embolden")
            if dx26 != 0 or dy26 != 0:
                _ft_cdll.FT_Outline_Translate(
                    ctypes.byref(slot.contents.outline),
                    ctypes.c_long(dx26),
                    ctypes.c_long(dy26)
                )
            _check_ft(_ft_cdll.FT_Render_Glyph(slot, 0), "FT_Render_Glyph")
            bm = slot.contents.bitmap
            if bm.rows == 0 or bm.width == 0:
                return None
            a = np.ctypeslib.as_array(bm.buffer, shape=(bm.rows, bm.pitch))[:, :bm.width].copy()
            return Glyph(a, slot.contents.bitmap_left, slot.contents.bitmap_top)

        f.load_glyph(gid, freetype.FT_LOAD_TARGET_LIGHT | freetype.FT_LOAD_FORCE_AUTOHINT)
        if x_strength26 > 0:
            if hasattr(freetype, 'FT_Outline_EmboldenXY'):
                outline_ptr = ctypes.byref(f.glyph._FT_GlyphSlot.contents.outline)
                freetype.FT_Outline_EmboldenXY(outline_ptr, x_strength26, y_strength26)
            elif hasattr(freetype, 'FT_Outline_Embolden'):
                outline_ptr = ctypes.byref(f.glyph._FT_GlyphSlot.contents.outline)
                freetype.FT_Outline_Embolden(outline_ptr, x_strength26)
        if dx26 != 0 or dy26 != 0:
            outline_ptr = ctypes.byref(f.glyph._FT_GlyphSlot.contents.outline)
            freetype.FT_Outline_Translate(outline_ptr, dx26, dy26)
        f.glyph.render(freetype.FT_RENDER_MODE_NORMAL)
        bm = f.glyph.bitmap
        if bm.rows == 0 or bm.width == 0:
            return None
        a = np.array(bm.buffer, dtype=np.uint8).reshape(bm.rows, bm.pitch)[:, :bm.width].copy()
        return Glyph(a, f.glyph.bitmap_left, f.glyph.bitmap_top)

    def _ft_glyph_params(self, font_path: str, size26: int, bold_lvl: int, name: str, gid: int) -> Optional[Glyph]:
        meta = self._get_font_meta(font_path)
        S = (size26 / float(meta.upem)) - 1e-9
        dil_funits = 0
        if bold_lvl > 0:
            dil_funits = BOLDNESS_FUNITS_RAMP[min(bold_lvl, len(BOLDNESS_FUNITS_RAMP) - 1)]
        x_strength26 = int(round(dil_funits * S)) if bold_lvl > 0 else 0
        y_strength26 = int(round(0.80 * x_strength26)) if bold_lvl > 0 else 0

        if USE_CTYPES_FT:
            f = self._ft.get(font_path)
            if f is None:
                f = ctypes.POINTER(_FT_FaceRec)()
                _check_ft(_ft_cdll.FT_New_Face(self._ft_lib, font_path.encode('utf-8'), 0, ctypes.byref(f)), "FT_New_Face")
                self._ft[font_path] = f
            _check_ft(_ft_cdll.FT_Set_Char_Size(f, size26, 0, 72, 72), "FT_Set_Char_Size")
        else:
            f = self._ft.get(font_path)
            if f is None:
                f = self._ft[font_path] = freetype.Face(font_path)
            f.set_char_size(size26, 0, 72, 72)

        if meta.glyf is not None and name in meta.glyf:
            gl = meta.glyf[name]
            if gl.isComposite() and len(gl.components) == 2:
                c0, c1 = gl.components[0], gl.components[1]
                if c1.glyphName == 'tildecomb' and getattr(c1, 'y', 0) == 0:
                    g0 = self._load_single_ft(f, meta.gid[c0.glyphName], x_strength26, y_strength26, 0, 0)
                    dx26 = int(round(getattr(c1, 'x', 0) * S))
                    g1 = self._load_single_ft(f, meta.gid[c1.glyphName], x_strength26, y_strength26, dx26, 0)
                    if g0 is not None and g1 is not None:
                        x_min = min(g0.left, g1.left)
                        x_max = max(g0.left + g0.cov.shape[1], g1.left + g1.cov.shape[1])
                        y_top = max(g0.top, g1.top)
                        y_bot = min(g0.top - g0.cov.shape[0], g1.top - g1.cov.shape[0])
                        H, W = y_top - y_bot, x_max - x_min
                        cov = np.zeros((H, W), dtype=np.uint8)
                        r0, col0 = y_top - g0.top, g0.left - x_min
                        cov[r0:r0 + g0.cov.shape[0], col0:col0 + g0.cov.shape[1]] = g0.cov
                        r1, col1 = y_top - g1.top, g1.left - x_min
                        sub = cov[r1:r1 + g1.cov.shape[0], col1:col1 + g1.cov.shape[1]]
                        cov[r1:r1 + g1.cov.shape[0], col1:col1 + g1.cov.shape[1]] = np.maximum(sub, g1.cov)
                        return Glyph(cov, x_min, y_top)

        use_gid = gid if gid >= 0 else meta.gid.get(name, 0)
        return self._load_single_ft(f, use_gid, x_strength26, y_strength26, 0, 0)

    def _ft_glyph(self, face, name):
        bold_lvl = getattr(face, 'boldness_level', 0)
        return self._ft_glyph_params(face.path, face.size26, bold_lvl, name, face.gid[name])

    def _own_glyph_params(self, font_path: str, size26: int, name: str) -> Optional[Glyph]:
        if not self.warned and not HAVE_FT:
            print("NOTE: FreeType not available; using fallback outline rasteriser.")
            self.warned = True
        meta = self._get_font_meta(font_path)
        gs = self._gs.get(font_path)
        if gs is None:
            gs = self._gs[font_path] = meta.tt.getGlyphSet()
        pen = _Pen(gs)
        gs[name].draw(pen)
        if not pen.contours:
            return None
        sp = size26 / 64.0 / meta.upem
        xs = [p[0]*sp for c in pen.contours for p in c]
        ys = [p[1]*sp for c in pen.contours for p in c]
        left, right = math.floor(min(xs)), math.ceil(max(xs))
        bot, top = math.floor(min(ys)), math.ceil(max(ys))
        w, h = max(1, right-left), max(1, top-bot)
        SS = 8
        mask = Image.new('1', (w*SS, h*SS), 0)
        for c in pen.contours:
            im = Image.new('1', (w*SS, h*SS), 0)
            ImageDraw.Draw(im).polygon([((x*sp-left)*SS, (top-y*sp)*SS) for x, y in c], fill=1)
            mask = ImageChops.logical_xor(mask, im)
        a = np.array(mask, dtype=np.float32).reshape(h, SS, w, SS).mean(axis=(1, 3))
        return Glyph((a*255+0.5).astype(np.uint8), left, top)

    def _own_glyph(self, face, name):
        return self._own_glyph_params(face.path, face.size26, name)


class Rasterizer:
    """Instance-owned page rasterizer consuming PositionedPage / PositionedDocument IR."""
    def __init__(self, cfg: Optional[Config] = None):
        self.cfg = cfg or Config()
        self.cache = GlyphCache(self.cfg.exact_raster)

    def close(self):
        self.cache.close()

    @staticmethod
    def _draw_glyph_on_canvas(canvas: np.ndarray, g: Glyph, x: int, baseline: int, fg_rgb: Tuple[int, int, int]):
        cov = g.cov.astype(np.float32) / 255.0
        h, w = cov.shape
        x0, y0 = x + g.left, baseline - g.top
        H, W = canvas.shape[:2]
        sx0, sy0 = max(0, -x0), max(0, -y0)
        ex, ey = min(w, W - x0), min(h, H - y0)
        if ex <= sx0 or ey <= sy0:
            return
        reg = canvas[y0 + sy0:y0 + ey, x0 + sx0:x0 + ex]
        a = cov[sy0:ey, sx0:ex][..., None]
        fg = np.array(fg_rgb, dtype=np.float32)
        reg[:] = reg * (1.0 - a) + fg * a

    def rasterize_page(self, ir_page: PositionedPage) -> Image.Image:
        H, W = int(ir_page.height), int(ir_page.width)
        canvas = np.empty((H, W, 3), dtype=np.float32)
        canvas[:] = np.array(ir_page.bg, dtype=np.float32)

        for cmd in ir_page.commands:
            k = getattr(cmd, "kind", None)
            if k == "glyph":
                font_path = cmd.font_path
                if not os.path.isfile(font_path):
                    font_path = self.cfg.resolve_font_path(cmd.font_id)
                if cmd.colr_layers:
                    for l_gname, l_gid, l_rgb in cmd.colr_layers:
                        lg = self.cache.get_by_params(font_path, cmd.size26, cmd.boldness_level, l_gname, l_gid)
                        if lg is not None:
                            self._draw_glyph_on_canvas(canvas, lg, cmd.x, cmd.baseline, l_rgb)
                else:
                    g = self.cache.get_by_params(font_path, cmd.size26, cmd.boldness_level, cmd.glyph_name, cmd.glyph_id)
                    if g is not None:
                        self._draw_glyph_on_canvas(canvas, g, cmd.x, cmd.baseline, cmd.color)
            elif k == "rule" and getattr(cmd, "role", None) == "link_underline":
                x0_fl, y0_fl, x1_fl, y1_fl = float(cmd.x0), float(cmd.y0), float(cmd.x1), float(cmd.y1)
                ix0, ix1 = max(0, int(math.floor(x0_fl))), min(W, int(math.ceil(x1_fl)))
                iy0, iy1 = max(0, int(math.floor(y0_fl))), min(H, int(math.ceil(y1_fl)))
                if iy1 > iy0 and ix1 > ix0:
                    fg = np.array(cmd.color, dtype=np.float32)
                    xs = np.arange(ix0, ix1, dtype=np.float32)
                    cx = np.clip(np.minimum(xs + 1.0, x1_fl) - np.maximum(xs, x0_fl), 0.0, 1.0)
                    for y_px in range(iy0, iy1):
                        cy = max(0.0, min(1.0, min(y_px + 1.0, y1_fl) - max(float(y_px), y0_fl)))
                        al = np.minimum(cx, cy)[..., None]
                        canvas[y_px, ix0:ix1] = canvas[y_px, ix0:ix1] * (1.0 - al) + fg * al
            elif k in ("rect", "rule"):
                x0 = max(0, int(cmd.x0))
                y0 = max(0, int(cmd.y0))
                x1 = min(W, int(cmd.x1))
                y1 = min(H, int(cmd.y1))
                if y1 > y0 and x1 > x0:
                    col_arr = np.array(cmd.color, dtype=np.float32)
                    dash = getattr(cmd, "dash", None) if k == "rule" else None
                    if dash is not None:
                        on_px, off_px = int(dash[0]), int(dash[1])
                        period = max(1, on_px + off_px)
                        phase = int(getattr(cmd, "dash_phase", 0))
                        xs = (np.arange(x0, x1) - int(cmd.x0) + phase) % period
                        mask = xs < on_px
                        canvas[y0:y1, x0:x1][:, mask] = col_arr
                    else:
                        canvas[y0:y1, x0:x1] = col_arr
            elif k == "ring_bullet":
                cx, cy, r = int(cmd.cx), int(cmd.cy), int(cmd.r)
                col_arr = np.array(cmd.color, dtype=np.float32)
                for dy in range(-r - 1, r + 2):
                    for dx in range(-r - 1, r + 2):
                        dist = math.hypot(dx, dy)
                        if r - 0.8 <= dist <= r + 0.8:
                            py, px = cy + dy, cx + dx
                            if 0 <= py < H and 0 <= px < W:
                                canvas[py, px] = col_arr
            elif k == "image":
                x, y, w, h = int(cmd.x), int(cmd.y), int(cmd.width), int(cmd.height)
                if cmd.pixels is not None and 0 <= y and y + h <= H and 0 <= x and x + w <= W:
                    canvas[y:y + h, x:x + w] = np.asarray(cmd.pixels, dtype=np.float32)

        return Image.fromarray(np.clip(canvas + 0.5, 0, 255).astype(np.uint8), "RGB")

    def rasterize_document(self, ir_doc: PositionedDocument, max_pages: Optional[int] = None) -> list:
        pages = ir_doc.pages[:max_pages] if max_pages else ir_doc.pages
        return [self.rasterize_page(p) for p in pages]


def rasterize(ir_page_or_doc, cfg: Optional[Config] = None):
    """Public helper to rasterize a PositionedPage (returns PIL.Image) or PositionedDocument (returns List[PIL.Image])."""
    r = Rasterizer(cfg)
    try:
        if isinstance(ir_page_or_doc, PositionedDocument):
            return r.rasterize_document(ir_page_or_doc)
        return r.rasterize_page(ir_page_or_doc)
    finally:
        r.close()
