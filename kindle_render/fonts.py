import math, os, re
from fractions import Fraction
from fontTools.ttLib import TTFont
from .config import BOLDNESS_FUNITS_RAMP

import ctypes

try:
    _hb_cdll = ctypes.CDLL("/usr/lib/x86_64-linux-gnu/libharfbuzz.so.0")
except Exception:
    _hb_cdll = None

if _hb_cdll is not None:
    class _hb_glyph_info_t(ctypes.Structure):
        _fields_ = [("codepoint", ctypes.c_uint32), ("mask", ctypes.c_uint32), ("cluster", ctypes.c_uint32), ("var1", ctypes.c_uint32), ("var2", ctypes.c_uint32)]

    class _hb_glyph_position_t(ctypes.Structure):
        _fields_ = [("x_advance", ctypes.c_int32), ("y_advance", ctypes.c_int32), ("x_offset", ctypes.c_int32), ("y_offset", ctypes.c_int32), ("var", ctypes.c_uint32)]

    _hb_cdll.hb_blob_create_from_file.argtypes = [ctypes.c_char_p]
    _hb_cdll.hb_blob_create_from_file.restype = ctypes.c_void_p
    _hb_cdll.hb_face_create.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    _hb_cdll.hb_face_create.restype = ctypes.c_void_p
    _hb_cdll.hb_font_create.argtypes = [ctypes.c_void_p]
    _hb_cdll.hb_font_create.restype = ctypes.c_void_p
    _hb_cdll.hb_font_set_scale.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
    _hb_cdll.hb_buffer_create.restype = ctypes.c_void_p
    _hb_cdll.hb_buffer_destroy.argtypes = [ctypes.c_void_p]
    _hb_cdll.hb_buffer_add_utf8.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_uint, ctypes.c_int]
    _hb_cdll.hb_buffer_guess_segment_properties.argtypes = [ctypes.c_void_p]
    _hb_cdll.hb_shape.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
    _hb_cdll.hb_buffer_get_glyph_infos.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
    _hb_cdll.hb_buffer_get_glyph_infos.restype = ctypes.POINTER(_hb_glyph_info_t)
    _hb_cdll.hb_buffer_get_glyph_positions.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
    _hb_cdll.hb_buffer_get_glyph_positions.restype = ctypes.POINTER(_hb_glyph_position_t)


PRECOMPOSED_LIGATURES = {}

# Arabic dual-joining and right-joining letter classification (U+0621..U+064A)
ARABIC_RIGHT_ONLY = {
    0x0622, 0x0623, 0x0624, 0x0625, 0x0627, 0x0629,
    0x062F, 0x0630, 0x0631, 0x0632, 0x0648, 0x0649
}
ARABIC_DUAL_JOIN = {
    0x0626, 0x0628, 0x062A, 0x062B, 0x062C, 0x062D, 0x062E,
    0x0633, 0x0634, 0x0635, 0x0636, 0x0637, 0x0638, 0x0639,
    0x063A, 0x0640, 0x0641, 0x0642, 0x0643, 0x0644, 0x0645,
    0x0646, 0x0647, 0x064A
}


class Face:
    """One font file at one size. All metrics in 26.6 integers."""
    def __init__(self, path, size26, liga=True, kern=True, cpsp=False, boldness_level=0):
        self.path = path
        self.size26 = size26
        self.use_liga = liga
        self.use_kern = kern
        self.use_cpsp = cpsp
        self.boldness_level = boldness_level

        self.tt = TTFont(path)
        self.upem = self.tt['head'].unitsPerEm
        self.S = (size26 / float(self.upem)) - 1e-9
        self.cmap = self.tt.getBestCmap() or {}
        self.hmtx = self.tt['hmtx']
        self.glyf = self.tt['glyf'] if 'glyf' in self.tt else None
        self.order = self.tt.getGlyphOrder()
        self.gid = {n: i for i, n in enumerate(self.order)}
        self.lig_len_map = {}
        self._load_tables()
        self._adv = {}
        self._kern = {}

    def dilation_funits(self) -> int:
        if self.boldness_level <= 0:
            return 0
        if self.boldness_level < len(BOLDNESS_FUNITS_RAMP):
            return BOLDNESS_FUNITS_RAMP[self.boldness_level]
        return BOLDNESS_FUNITS_RAMP[-1]

    def _lookups(self, tbl, tag):
        if not hasattr(tbl, 'FeatureList') or not tbl.FeatureList:
            return []
        return sorted(set(i for fr in tbl.FeatureList.FeatureRecord if fr.FeatureTag == tag
                          for i in fr.Feature.LookupListIndex))

    def _load_tables(self):
        self.liga_tabs = []
        self.kern_tabs = []
        self.cpsp_glyphs = set()
        self.cpsp_xadv = 0
        self.cpsp_xplace = 0
        self.numr_map = {}
        self.dnom_map = {}
        self.single_subs = {}
        self.multi_ligs = {}

        if 'GSUB' in self.tt:
            gs = self.tt['GSUB'].table
            for i in self._lookups(gs, 'liga'):
                lk = gs.LookupList.Lookup[i]
                for st in lk.SubTable:
                    if lk.LookupType == 7:
                        st = st.ExtSubTable
                    if hasattr(st, 'ligatures'):
                        self.liga_tabs.append(st.ligatures)
                        for first_g, l_list in st.ligatures.items():
                            for L in l_list:
                                self.lig_len_map[L.LigGlyph] = 1 + len(L.Component)

            for tag, target_map in (('numr', self.numr_map), ('dnom', self.dnom_map)):
                for i in self._lookups(gs, tag):
                    lk = gs.LookupList.Lookup[i]
                    for st in lk.SubTable:
                        if lk.LookupType == 7:
                            st = st.ExtSubTable
                        if hasattr(st, 'mapping'):
                            target_map.update(st.mapping)

            for tag in ('init', 'medi', 'fina', 'isol'):
                m = {}
                for i in self._lookups(gs, tag):
                    lk = gs.LookupList.Lookup[i]
                    for st in lk.SubTable:
                        if lk.LookupType == 7:
                            st = st.ExtSubTable
                        if hasattr(st, 'mapping'):
                            m.update(st.mapping)
                if m:
                    self.single_subs[tag] = m

            for tag in ('rlig', 'liga', 'akhn', 'half', 'cjct', 'pres', 'blwf', 'pstf', 'vatu'):
                tab_list = []
                for i in self._lookups(gs, tag):
                    lk = gs.LookupList.Lookup[i]
                    for st in lk.SubTable:
                        if lk.LookupType == 7:
                            st = st.ExtSubTable
                        if hasattr(st, 'ligatures'):
                            tab_list.append(st.ligatures)
                if tab_list:
                    self.multi_ligs[tag] = tab_list

        if 'GPOS' in self.tt:
            gp = self.tt['GPOS'].table
            for i in self._lookups(gp, 'kern'):
                lk = gp.LookupList.Lookup[i]
                for st in lk.SubTable:
                    if lk.LookupType == 9:
                        st = st.ExtSubTable
                    if hasattr(st, 'Coverage') and hasattr(st, 'Format'):
                        self.kern_tabs.append(st)

            if self.use_cpsp:
                for i in self._lookups(gp, 'cpsp'):
                    lk = gp.LookupList.Lookup[i]
                    for st in lk.SubTable:
                        if lk.LookupType == 9:
                            st = st.ExtSubTable
                        if hasattr(st, 'Coverage') and hasattr(st, 'Value'):
                            self.cpsp_glyphs.update(st.Coverage.glyphs)
                            self.cpsp_xadv = getattr(st.Value, 'XAdvance', 0) or 0
                            self.cpsp_xplace = getattr(st.Value, 'XPlacement', 0) or 0

    def names(self, text):
        for k, v in PRECOMPOSED_LIGATURES.items():
            if k in text:
                text = text.replace(k, v)
        if "\u2044" in text:
            text = text.replace("1\u20442", "\u00bd").replace("1\u20444", "\u00bc").replace("3\u20444", "\u00be")
            if "\u2044" in text and self.numr_map and self.dnom_map:
                out = []
                i = 0
                n = len(text)
                while i < n:
                    m = re.match(r"^(\d+)\u2044(\d+)", text[i:])
                    if m:
                        num_s, den_s = m.group(1), m.group(2)
                        for ch in num_s:
                            g_base = self.cmap.get(ord(ch), '.notdef')
                            out.append(self.numr_map.get(g_base, g_base))
                        out.append(self.cmap.get(0x2044, 'fraction'))
                        for ch in den_s:
                            g_base = self.cmap.get(ord(ch), '.notdef')
                            out.append(self.dnom_map.get(g_base, g_base))
                        i += len(m.group(0))
                        continue
                    cp = ord(text[i])
                    if cp == 0xA0:
                        cp = 0x20
                    out.append(self.cmap.get(cp, '.notdef'))
                    i += 1
                if self.use_liga and self.liga_tabs:
                    out = self._ligate(out)
                return out

        out = []
        for c in text:
            cp = ord(c)
            if cp == 0xA0:
                cp = 0x20
            out.append(self.cmap.get(cp, '.notdef'))
        if self.use_liga and self.liga_tabs:
            out = self._ligate(out)
        return out

    def _ligate_with_tabs(self, g, tabs):
        out, i = [], 0
        while i < len(g):
            done = False
            for lig in tabs:
                if g[i] in lig:
                    for L in lig[g[i]]:
                        n = len(L.Component)
                        if g[i + 1:i + 1 + n] == list(L.Component):
                            out.append(L.LigGlyph)
                            i += 1 + n
                            done = True
                            break
                if done:
                    break
            if not done:
                out.append(g[i])
                i += 1
        return out

    def _ligate(self, g):
        return self._ligate_with_tabs(g, self.liga_tabs)

    def shape_arabic_word(self, logical_word: str):
        """Shapes a single Arabic word in logical order and returns visual RTL glyph names."""
        cps = [ord(c) for c in logical_word]
        n = len(cps)
        forms = []
        for idx, cp in enumerate(cps):
            # Check if previous logical char joins left
            prev_joins_left = (idx > 0) and (cps[idx - 1] in ARABIC_DUAL_JOIN)
            # Check if current char can join right and next char can join right
            cur_joins_right = (cp in ARABIC_DUAL_JOIN or cp in ARABIC_RIGHT_ONLY)
            cur_joins_left = (cp in ARABIC_DUAL_JOIN)
            next_joins_right = (idx + 1 < n) and (cps[idx + 1] in ARABIC_DUAL_JOIN or cps[idx + 1] in ARABIC_RIGHT_ONLY)

            j_prev = prev_joins_left and cur_joins_right
            j_next = cur_joins_left and next_joins_right
            if j_prev and j_next:
                forms.append('medi')
            elif j_prev:
                forms.append('fina')
            elif j_next:
                forms.append('init')
            else:
                forms.append('isol')

        glyphs = []
        for cp, form in zip(cps, forms):
            g = self.cmap.get(cp, '.notdef')
            sub_map = self.single_subs.get(form, {})
            glyphs.append(sub_map.get(g, g))

        # Apply rlig / liga in logical order (e.g. lam.init + alef.fina -> lam_alef)
        for tag in ('rlig', 'liga'):
            if tag in self.multi_ligs:
                glyphs = self._ligate_with_tabs(glyphs, self.multi_ligs[tag])

        # Reverse into visual left-to-right display order
        return glyphs[::-1]

    def shape_devanagari_word(self, word: str):
        """Shapes a Devanagari word using native HarfBuzz (hb_shape) when available, with GSUB fallback."""
        if _hb_cdll is not None:
            if not hasattr(self, "_hb_font"):
                blob = _hb_cdll.hb_blob_create_from_file(self.path.encode("utf-8"))
                hb_face = _hb_cdll.hb_face_create(blob, 0)
                self._hb_font = _hb_cdll.hb_font_create(hb_face)
                _hb_cdll.hb_font_set_scale(self._hb_font, self.upem, self.upem)
            buf = _hb_cdll.hb_buffer_create()
            b_utf8 = word.encode("utf-8")
            _hb_cdll.hb_buffer_add_utf8(buf, b_utf8, len(b_utf8), 0, len(b_utf8))
            _hb_cdll.hb_buffer_guess_segment_properties(buf)
            _hb_cdll.hb_shape(self._hb_font, buf, None, 0)
            length = ctypes.c_uint(0)
            infos = _hb_cdll.hb_buffer_get_glyph_infos(buf, ctypes.byref(length))
            poss = _hb_cdll.hb_buffer_get_glyph_positions(buf, ctypes.byref(length))
            out = []
            for i in range(length.value):
                gid = infos[i].codepoint
                gname = self.order[gid] if gid < len(self.order) else ".notdef"
                x_adv26 = int(math.floor(poss[i].x_advance * self.S))
                x_off_px = int(round((poss[i].x_offset * self.S) / 64.0))
                y_off_px = int(round((poss[i].y_offset * self.S) / 64.0))
                out.append((gname, x_adv26, x_off_px, y_off_px))
            _hb_cdll.hb_buffer_destroy(buf)
            return out

        chars = list(word)
        i = 1
        while i < len(chars):
            if ord(chars[i]) == 0x093F:
                j = i - 1
                while j >= 2 and ord(chars[j - 1]) == 0x094D:
                    j -= 2
                matra = chars.pop(i)
                chars.insert(j, matra)
            i += 1
        glyphs = [self.cmap.get(ord(c), '.notdef') for c in chars]
        for tag in ('akhn', 'half', 'cjct', 'pres', 'blwf', 'pstf', 'vatu'):
            if tag in self.multi_ligs:
                glyphs = self._ligate_with_tabs(glyphs, self.multi_ligs[tag])
        return [(gn, self.adv26(gn), 0, 0) for gn in glyphs]

    def get_colr_layers(self, gname: str):
        """Extracts (layer_glyph_name, (R, G, B)) list from COLR v1/v0 + CPAL tables for color emoji."""
        if not hasattr(self, "_colr_cache"):
            self._colr_cache = {}
            self._bgl_map = {}
            self._ll_paints = []
            self._cpal_colors = []
            if "COLR" in self.tt and "CPAL" in self.tt:
                colr = self.tt["COLR"].table
                self._cpal_colors = [(c.red, c.green, c.blue) for c in self.tt["CPAL"].palettes[0]]
                if getattr(colr, "BaseGlyphList", None):
                    self._bgl_map = {r.BaseGlyph: r.Paint for r in colr.BaseGlyphList.BaseGlyphPaintRecord}
                if getattr(colr, "LayerList", None):
                    self._ll_paints = colr.LayerList.Paint
        if gname in self._colr_cache:
            return self._colr_cache[gname]
        p = self._bgl_map.get(gname)
        if not p:
            self._colr_cache[gname] = None
            return None
        layers = []
        pal = self._cpal_colors
        ll = self._ll_paints
        def _extract_color(paint_obj):
            if paint_obj is None:
                return (0, 0, 0)
            fmt = getattr(paint_obj, "Format", 0)
            if fmt in (2, 3) and hasattr(paint_obj, "PaletteIndex"):
                idx = paint_obj.PaletteIndex
                return pal[idx] if idx < len(pal) else (0, 0, 0)
            if hasattr(paint_obj, "ColorLine") and paint_obj.ColorLine and paint_obj.ColorLine.ColorStop:
                 stops = paint_obj.ColorLine.ColorStop
                 mid = stops[len(stops) // 2].PaletteIndex
                 return pal[mid] if mid < len(pal) else (0, 0, 0)
            if hasattr(paint_obj, "Paint"):
                return _extract_color(paint_obj.Paint)
            return (0, 0, 0)
        def _walk_paint(paint_obj):
            if paint_obj is None:
                return
            fmt = getattr(paint_obj, "Format", 0)
            if fmt == 1:
                for li in range(paint_obj.FirstLayerIndex, paint_obj.FirstLayerIndex + paint_obj.NumLayers):
                    if li < len(ll):
                        _walk_paint(ll[li])
            elif fmt == 10 and hasattr(paint_obj, "Glyph"):
                layers.append((paint_obj.Glyph, _extract_color(paint_obj.Paint)))
            elif hasattr(paint_obj, "Paint"):
                _walk_paint(paint_obj.Paint)
            elif fmt == 32:
                _walk_paint(getattr(paint_obj, "BackdropPaint", None))
                _walk_paint(getattr(paint_obj, "SourcePaint", None))
        _walk_paint(p)
        self._colr_cache[gname] = layers if layers else None
        return self._colr_cache[gname]

    def adv26(self, name):
        a = self._adv.get(name)
        if a is None:
            raw_w = self.hmtx[name][0] if name in self.hmtx.metrics else 500
            if self.boldness_level > 0:
                raw_w += self.dilation_funits()
            a = self._adv[name] = math.floor(raw_w * self.S)
        return a

    def kern_units(self, g1, g2):
        key = (g1, g2)
        if key in self._kern:
            return self._kern[key]
        val = 0
        for st in self.kern_tabs:
            cov = st.Coverage.glyphs
            if g1 not in cov:
                continue
            if st.Format == 1:
                found = False
                for pvr in st.PairSet[cov.index(g1)].PairValueRecord:
                    if pvr.SecondGlyph == g2:
                        v = pvr.Value1
                        val = int(getattr(v, 'XAdvance', 0) or 0) if v else 0
                        found = True
                        break
                if found:
                    break
            else:
                c1 = st.ClassDef1.classDefs.get(g1, 0)
                c2 = st.ClassDef2.classDefs.get(g2, 0)
                v = st.Class1Record[c1].Class2Record[c2].Value1
                val = int(getattr(v, 'XAdvance', 0) or 0) if v else 0
                break
        self._kern[key] = val
        return val

    def shape(self, text, extra_track26=0):
        """-> list of (glyph_name, advance26 including kerning, cpsp, and extra tracking)."""
        g = self.names(text)
        out = []
        is_all_caps = (text.isupper() and len(text) > 1) if self.use_cpsp else False
        cpsp_add26 = math.floor(self.cpsp_xadv * self.S) if (is_all_caps and self.cpsp_xadv) else 0

        for i, n in enumerate(g):
            adv = self.adv26(n)
            if self.use_kern and i + 1 < len(g):
                adv += math.floor(self.kern_units(n, g[i + 1]) * self.S)
            if is_all_caps and n in self.cpsp_glyphs:
                adv += cpsp_add26
            if extra_track26:
                adv += extra_track26
            out.append((n, adv))
        return out

    def lsb26(self, name):
        if self.glyf is None or name not in self.glyf:
            return 0
        gl = self.glyf[name]
        return int(math.floor(gl.xMin * self.S)) if gl.numberOfContours else 0

    def space26(self):
        sp_glyph = self.cmap.get(0x20, '.notdef')
        return self.adv26(sp_glyph)

    def hyphen26(self):
        hy_glyph = self.cmap.get(ord('-'), '.notdef')
        return self.adv26(hy_glyph)


class Family:
    FILES = {
        (False, False): 'Bookerly-Regular.ttf',
        (True, False): 'Bookerly-Bold.ttf',
        (False, True): 'Bookerly-RegularItalic.ttf',
        (True, True): 'Bookerly-BoldItalic.ttf',
        'display': 'Bookerly-Display.ttf',
        'mono': 'DroidSansMono.ttf',
        'ethiopic': 'NotoSerifEthiopic-Regular.ttf',
        'ethiopic_sans': 'NotoSansEthiopic-Regular.ttf',
        'arabic': 'NotoNaskhArabic-Regular.ttf',
        'hebrew': 'NotoSansHebrew-Regular.ttf',
        'devanagari': 'NotoSansDevanagari-Regular.ttf',
            'thai': 'NotoSansThai-Regular.ttf',
        'cjk': 'NotoSansCJK-Regular.otf',
        'emoji': 'NotoColorEmoji.ttf',
        'symbols': 'NotoSansSymbols2-Regular.ttf',
        'dejavu': 'DejaVuSans.ttf',
    }

    def __init__(self, cfg):
        self.cfg = cfg
        self._faces = {}

    def face(self, bold=False, italic=False, size26=None, display=False):
        size26 = size26 or self.cfg.size26
        use_display = display

        key = ('display' if use_display else (bold, italic), size26, self.cfg.boldness_level)
        if key not in self._faces:
            fn = self.FILES['display'] if use_display else self.FILES[(bold, italic)]
            path = self.cfg.resolve_font_path(fn)
            self._faces[key] = Face(
                path,
                size26,
                liga=self.cfg.liga,
                kern=self.cfg.kern,
                cpsp=self.cfg.cpsp,
                boldness_level=self.cfg.boldness_level
            )
        return self._faces[key]

    def special_face(self, kind: str, size26=None):
        size26 = size26 or self.cfg.size26
        key = (kind, size26, self.cfg.boldness_level)
        if key not in self._faces:
            fn = self.FILES.get(kind)
            if not fn:
                return self.face(False, False, size26)
            path = self.cfg.resolve_font_path(fn)
            if not os.path.isfile(path):
                return self.face(False, False, size26)
            use_ot = kind in ('ethiopic', 'ethiopic_sans', 'arabic', 'hebrew', 'devanagari', 'dejavu')
            self._faces[key] = Face(
                path,
                size26,
                liga=use_ot,
                kern=use_ot,
                cpsp=False,
                boldness_level=self.cfg.boldness_level
            )
        return self._faces[key]

    def fallback_face_for_char(self, ch: str, size26=None):
        size26 = size26 or self.cfg.size26
        cp = ord(ch)
        if 0x1200 <= cp <= 0x137F:
            return self.special_face('ethiopic', size26)
        if 0x0600 <= cp <= 0x06FF or 0xFB50 <= cp <= 0xFEFF:
            return self.special_face('arabic', size26)
        if 0x0590 <= cp <= 0x05FF:
            return self.special_face('hebrew', size26)
        if 0x0900 <= cp <= 0x097F:
            return self.special_face('devanagari', size26)
        if 0x0E00 <= cp <= 0x0E7F:
            return self.special_face('thai', size26)
        if 0x3000 <= cp <= 0x9FFF or 0xAC00 <= cp <= 0xD7AF or 0xFF00 <= cp <= 0xFFEF:
            return self.special_face('cjk', size26)
        if cp >= 0x1F000 or cp in (0x2615, 0x2764, 0x2665, 0x200D, 0xFE0F):
            ef = self.special_face('emoji', size26)
            if cp in ef.cmap:
                return ef
        for kind in ('symbols', 'dejavu', 'cjk', 'emoji'):
            f = self.special_face(kind, size26)
            if cp in f.cmap:
                return f
        return self.face(False, False, size26)
