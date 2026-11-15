"""Glyph bitmaps via FreeType FT_LOAD_TARGET_LIGHT (256-level grayscale).
Includes:
1. Checked ctypes FreeType return codes and FT_Library_Version introspection
2. Separate-component light autohinting for lowercase tilde composites (atilde, ntilde, otilde, itilde, utilde)
3. Anisotropic vector outline dilation (y_strength = 0.80 * x_strength)
"""
import ctypes
import ctypes.util
import math
import numpy as np
from PIL import Image, ImageDraw, ImageChops
from fontTools.pens.basePen import BasePen

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

    _ft_lib_handle = ctypes.c_void_p()
    _check_ft(_ft_cdll.FT_Init_FreeType(ctypes.byref(_ft_lib_handle)), "FT_Init_FreeType")


def get_freetype_version() -> str:
    if USE_CTYPES_FT and _ft_cdll is not None:
        maj, min_, pat = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
        _ft_cdll.FT_Library_Version(_ft_lib_handle, ctypes.byref(maj), ctypes.byref(min_), ctypes.byref(pat))
        return f"{maj.value}.{min_.value}.{pat.value}"
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


class GlyphCache:
    def __init__(self, exact=True):
        self.exact = exact and HAVE_FT
        self.warned = False
        self._ft, self._gs, self._c = {}, {}, {}

    def get(self, face, name):
        bold_lvl = getattr(face, 'boldness_level', 0)
        key = (face.path, face.size26, bold_lvl, name)
        if key in self._c:
            return self._c[key]
        g = self._ft_glyph(face, name) if self.exact else self._own_glyph(face, name)
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

    def _ft_glyph(self, face, name):
        bold_lvl = getattr(face, 'boldness_level', 0)
        dil_funits = face.dilation_funits() if hasattr(face, 'dilation_funits') else 0
        x_strength26 = int(round(dil_funits * face.S)) if bold_lvl > 0 else 0
        y_strength26 = int(round(0.80 * x_strength26)) if bold_lvl > 0 else 0

        if USE_CTYPES_FT:
            f = self._ft.get(face.path)
            if f is None:
                f = ctypes.POINTER(_FT_FaceRec)()
                _check_ft(_ft_cdll.FT_New_Face(_ft_lib_handle, face.path.encode('utf-8'), 0, ctypes.byref(f)), "FT_New_Face")
                self._ft[face.path] = f
            _check_ft(_ft_cdll.FT_Set_Char_Size(f, face.size26, 0, 72, 72), "FT_Set_Char_Size")
        else:
            f = self._ft.get(face.path)
            if f is None:
                f = self._ft[face.path] = freetype.Face(face.path)
            f.set_char_size(face.size26, 0, 72, 72)

        # Decompose lowercase tilde composites (atilde, ntilde, otilde, itilde, utilde) so tildecomb is autohinted independently
        if face.glyf is not None and name in face.glyf:
            gl = face.glyf[name]
            if gl.isComposite() and len(gl.components) == 2:
                c0, c1 = gl.components[0], gl.components[1]
                if c1.glyphName == 'tildecomb' and getattr(c1, 'y', 0) == 0:
                    g0 = self._load_single_ft(f, face.gid[c0.glyphName], x_strength26, y_strength26, 0, 0)
                    dx26 = int(round(getattr(c1, 'x', 0) * face.S))
                    g1 = self._load_single_ft(f, face.gid[c1.glyphName], x_strength26, y_strength26, dx26, 0)
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

        return self._load_single_ft(f, face.gid[name], x_strength26, y_strength26, 0, 0)

    def _own_glyph(self, face, name):
        if not self.warned and not HAVE_FT:
            print("NOTE: FreeType not available; using fallback outline rasteriser.")
            self.warned = True
        gs = self._gs.get(face.path)
        if gs is None:
            gs = self._gs[face.path] = face.tt.getGlyphSet()
        pen = _Pen(gs)
        gs[name].draw(pen)
        if not pen.contours:
            return None
        sp = face.size26 / 64.0 / face.upem
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
