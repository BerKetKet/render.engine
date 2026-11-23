import math
import os
from dataclasses import dataclass
from typing import Optional, Tuple, Dict

PALETTES: Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = {
    "exact":    ((255, 255, 255), (0, 0, 0)),
    "white":    ((255, 255, 255), (18, 18, 18)),
    "sepia":    ((251, 240, 217), (56, 44, 30)),
    "emerald1": ((200, 230, 201), (35, 43, 32)),
    "emerald2": ((226, 236, 216), (35, 43, 32)),
    "dark":     ((18, 18, 18),    (213, 213, 213)),
}

COMPACT_FONT_RAMP_SP: Tuple[float, ...] = (
    11.0, 13.2, 15.4, 16.5, 17.6, 18.425, 19.8,
    20.9, 22.0, 23.1, 24.2, 27.5, 38.5, 49.5
)
TABLET_FONT_RAMP_SP: Tuple[float, ...] = (
    12.1, 14.3, 16.5, 18.7, 20.9, 22.0, 24.2, 26.4, 28.6,
    30.8, 33.0, 37.4, 41.8, 46.2, 50.6, 55.0, 71.5, 93.5
)

# Empirically measured FUnits dilation ramp across boldness levels 0..5
BOLDNESS_FUNITS_RAMP: Tuple[int, ...] = (0, 12, 24, 38, 52, 68)


LINE_SPACING_RATIOS: Tuple[float, ...] = (1.353, 1.510, 1.635, 2.318, 2.977)
WORD_SPACING_STEP_EM: float = 0.22
CHAR_SPACING_STEP_EM: float = 0.056
THEME_SPACING_PRESETS: Dict[str, Dict[str, int]] = {
    "standard": {"line": 2, "paragraph": 1, "word": 1, "char": 1},
    "compact":  {"line": 1, "paragraph": 1, "word": 1, "char": 1},
    "large":    {"line": 3, "paragraph": 1, "word": 1, "char": 1},
}

@dataclass
class Config:
    # ---------------- screen / geometry ----------------
    screen_w: int = 1080
    screen_h: int = 2340
    x0: int = 39
    right: int = 1041
    top: int = 168
    page_bottom: int = 2203
    dpi_scale: float = 2.625
    img_px_scale: float = 1.80

    # ---------------- font size ----------------
    size26: int = 2688                # 42.0 px in 26.6 fixed-point units (42 * 64)

    # ---------------- vertical rhythm ----------------
    pitch: int = 0                    # Explicit body line pitch in px (0 = use round(pitch_ratio * size_px()))
    pitch_ratio: float = 1.5          # Default ratio when pitch == 0 (e.g. 34px -> 51px)
    line_spacing_step: Optional[int] = None  # User line-spacing slider (1..5; None = use pitch/pitch_ratio)
    paragraph_spacing_step: int = 1   # User paragraph-spacing slider (1..5; step 1 = 0 extra gap)
    word_spacing_step: int = 1        # User word-spacing slider (1..5; +0.22 em per step above 1)
    char_spacing_step: int = 1        # User character-spacing slider (1..5; +0.056 em per step above 1)
    word_spacing_step_em: float = WORD_SPACING_STEP_EM
    char_spacing_step_em: float = CHAR_SPACING_STEP_EM
    word_spacing_shrink_mult: float = 0.10
    word_spacing_shrink_decay: float = 3.27
    char_spacing_shrink_mult: float = 0.80
    heading_line_spacing_lead_k: float = 0.045
    heading_line_spacing_mb_em: float = 0.652
    typo_ascender: float = 0.802      # Bookerly OS/2 sTypoAscender (+802 FUnits)
    body_cap_height: float = 0.693
    display_cap_height: float = 0.762
    fractional_pitch_snapping: bool = True

    # ---------------- shaping & font features ----------------
    liga: bool = True
    kern: bool = True
    cpsp: bool = False
    optical_sizing: bool = False
    display_threshold_px: float = 48.0

    # ---------------- continuous boldness slider ----------------
    boldness_level: int = 0
    boldness_ramp: Tuple[int, ...] = BOLDNESS_FUNITS_RAMP
    boldness_anisotropic_y: float = 0.80

    # ---------------- placement / raster ----------------
    place_phase: float = 0.5
    overhang_shift: bool = True
    exact_raster: bool = True
    allow_unshaped: bool = False
    fg: Tuple[int, int, int] = (0, 0, 0)
    bg: Tuple[int, int, int] = (255, 255, 255)

    # ---------------- paragraph layer & justification ----------------
    justify: bool = True
    breaker: str = "kp"
    max_kp_items: int = 1000
    ragged_greedy: bool = False       # Unified Knuth-Plass across both justified and ragged text
    space_stretch: float = 0.75
    space_shrink: float = 101 / 577.0 # Unified dynamic shrink ratio (101 units at 577-unit space)
    runt_min_chars: int = 7

    # ---------------- micro-tracking (letter spacing) ----------------
    micro_tracking: bool = False      # Dormant by default in both API and CLI
    tracking_min_em: float = -0.005
    tracking_max_em: float = 0.005
    tracking_badness_threshold: float = 80.0

    # ---------------- optical margin alignment ----------------
    optical_margin: bool = False
    optical_margin_draw: bool = False
    optical_margin_ratio: float = 0.5
    left_optical_margin: bool = False

    # ---------------- on-device hyphenation ----------------
    hyphenate: bool = True
    hyphen_dic: str = ""
    left_hyphen_min: int = 2
    right_hyphen_min: int = 3
    min_word_length: int = 5
    tbl_scale_model: str = "M"
    tbl_pad_em: float = 1.37
    tbl_cap_em: float = 7.5
    tbl_scale_floor: float = 0.2
    tbl_uniform_layout: bool = True
    tbl_data_min_factor: float = 0.8
    tbl_long3_cap_em: float = 8.8
    tbl_lp0_em: float = 0.845
    tbl_lpm_em: float = 0.567
    tbl_row_pad_em: float = 0.28
    hyphen_penalty: int = 125
    ragged_hyphen_penalty: int = 50
    ladder2: int = 3000
    ladder3: int = 10000
    fitness_gap: int = 1000
    tolerance: float = 4.0
    ragged_shortfall: float = 100.0
    remainder: str = "bresenham"

    # ---------------- structure & margins ----------------
    default_indent_em: float = 0.0
    first_para_no_indent: bool = True
    last_line_flush_left: bool = True
    widow_orphan: int = 2

    # Headings
    heading_scale: Tuple[float, ...] = (2.0, 1.5, 1.17, 1.0, 0.83, 0.67)
    heading_top_extra_px: int = 1
    heading_right_margin_em: float = 0.0
    margin_at_page_top: bool = True
    use_display_for_headings: bool = False

    # Indents & Spacing
    base_root_em_sp: float = 10.97619 # DEVICE-CONSTANT (measured exam1 p.25-26 & exam2 p.40-41): 28.8125 px root em at 2.625x density
    blockquote_margin_ratio: float = 0.04725  # DEVICE-CONSTANT (measured probe p.52, exam1 p.44): blockquote left/right margin ratio
    collapsed_table_margin_px: int = 36       # DEVICE-CONSTANT (measured exam2 p.8,13,35): right margin reserve for border-collapse:collapse tables
    collapsed_table_scale: float = 0.70       # DEVICE-CONSTANT (measured exam2 p.8): auto-fit scale factor for wide >=4-col collapsed tables
    collapsed_table_line_pitch: int = 55      # DEVICE-CONSTANT (measured exam2 p.13,35): 1.0x collapsed table row line pitch at 57px body pitch
    collapsed_table_rule_h: int = 4           # DEVICE-CONSTANT (measured exam2 p.8,13,35): bottom rule height for collapsed tables
    collapsed_table_pad_1x: int = 34          # DEVICE-CONSTANT (measured exam2 p.13,35): base horizontal cell padding for 1.0x collapsed tables
    collapsed_table_pad_scaled: int = 24      # DEVICE-CONSTANT (measured exam2 p.8): base horizontal cell padding for 0.70x scaled tables
    pre_hr_top_gap_px: int = 50               # DEVICE-CONSTANT (measured exam2 p.36): vertical gap from <pre> block to <hr/>
    blockquote_indent_em: float = 1.1286
    dd_indent_em: float = 1.1286
    ul_indent_em: float = 2.0000
    ul_nested_indent_em: float = 2.0000
    ol_indent_em: float = 2.1054              # DEVICE-CONSTANT (measured across 3 geometries / 5 corpora: probe p.2/87 x=127.42px, exam2 p.2/7 x=167.42px, exam1 p.2/45 & exam3_normal p.2/39 x=173.74px, exam3_small p.2/24 x=150.58px)
    link_underline_base_offset: float = -0.5855 # DEVICE-CONSTANT (measured across 3 geometries / 5 corpora: probe p.2, exam1 p.2, exam2 p.2, exam3_normal p.2, exam3_small p.2): subpixel link underline top offset relative to stroke_h + 0.0261*size_px + 0.0025*pitch
    css_px_scale: float = 2.625
    para_gap_em: float = 0.0

    # Fonts search paths
    fonts_dir: str = "kindle_analysis/fonts"
    fonts_fallback_dirs: Tuple[str, ...] = ("fonts", "fonts_github", "../kindle_analysis/fonts")

    def size_px(self) -> float:
        return self.size26 / 64.0

    def raw_pitch_px(self) -> float:
        if self.pitch > 0:
            return float(self.pitch)
        if self.line_spacing_step is not None:
            step = max(1, min(5, int(self.line_spacing_step)))
            return LINE_SPACING_RATIOS[step - 1] * self.size_px()
        return float(int(math.floor(self.pitch_ratio * self.size_px() + 0.5)))

    def pitch_px(self) -> int:
        if self.pitch > 0:
            return self.pitch
        if self.line_spacing_step is not None:
            return int(round(self.raw_pitch_px()))
        return int(math.floor(self.pitch_ratio * self.size_px() + 0.5))

    def user_para_gap_px(self) -> int:
        step = max(1, min(5, int(self.paragraph_spacing_step)))
        return int(round((step - 1) * self.size_px())) if step > 1 else 0

    def user_word_spacing_26(self) -> int:
        step = max(1, min(5, int(self.word_spacing_step)))
        return int(round((step - 1) * self.word_spacing_step_em * self.size26)) if step > 1 else 0

    def user_char_spacing_26(self) -> int:
        step = max(1, min(5, int(self.char_spacing_step)))
        return int(round((step - 1) * self.char_spacing_step_em * self.size26)) if step > 1 else 0

    def extra_lead_px(self) -> float:
        # pitch_px() is integer-rounded, so |error| <= 0.5; below that the
        # geometry is the tight regime. Matches the existing +0.5 in the has_extra_lead test.
        raw = self.pitch_px() - (19.0 / 14.0) * self.size_px()
        return raw if raw > 0.5 else 0.0

    def vem_px(self) -> float:
        """Dynamic vertical CSS em unit derived from body line pitch (std_pitch / 1.2)."""
        return self.pitch_px() / 1.2

    def base_root_em_px(self) -> float:
        """Base CSS root em in device pixels (10.97619sp * 2.625 = 28.8125 px)."""
        return self.base_root_em_sp * self.css_px_scale

    def boldness_dilation_funits(self) -> int:
        if self.boldness_level <= 0:
            return 0
        idx = min(self.boldness_level, len(self.boldness_ramp) - 1)
        return self.boldness_ramp[idx]

    def apply_palette(self, name: str):
        if name in PALETTES:
            self.bg, self.fg = PALETTES[name]

    def resolve_hyphen_dic(self, lang: str = "en") -> str:
        """Resolves the native Kindle compiled binary (.bin) or fallback (.dic) hyphenation dictionary for the requested language."""
        if self.hyphen_dic and os.path.isfile(self.hyphen_dic):
            return os.path.abspath(self.hyphen_dic)
        pkg_dir = os.path.dirname(os.path.abspath(__file__))
        lang_low = (lang or "en").lower()
        lang_prefix = lang_low[:2]
        bin_map = {
            "de": ["hyph_de_DE.dic", "hyph_de.bin"],
            "fr": ["hyph_fr.dic", "hyph_fr.bin"],
            "es": ["hyph_es.bin"],
            "it": ["hyph_it.bin"],
            "pt": ["hyph_pt.bin"],
            "ru": ["hyph_ru.bin"],
            "nl": ["hyph_nl.bin"],
        }
        if lang_prefix in bin_map:
            for fn in bin_map[lang_prefix]:
                for c in [os.path.join(pkg_dir, fn), fn]:
                    if os.path.isfile(c):
                        return os.path.abspath(c)
        if lang_prefix != "en":
            return ""
        candidates = [
            os.path.join(pkg_dir, "hyph_en_YJ.bin"),
            os.path.join(pkg_dir, "hyph_cthulu_fever.dic"),
            os.path.join(pkg_dir, "hyph_en_us.dic"),
            "kindle_render/hyph_cthulu_fever.dic",
            "kindle_render/hyph_en_us.dic",
            "hyph_cthulu_fever.dic",
            "hyph_en_us.dic",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return os.path.abspath(c)
        return ""

    def resolve_font_path(self, filename: str) -> str:
        """Locates a font file across bundled package fonts, configured directories, and system fonts."""
        pkg_dir = os.path.dirname(os.path.abspath(__file__))
        dirs = [
            os.path.join(pkg_dir, "fonts"),
            self.fonts_dir,
        ] + list(self.fonts_fallback_dirs) + [
            os.path.join(pkg_dir, "../kindle_analysis/fonts"),
            "/usr/share/fonts/truetype/noto",
            "/usr/share/fonts/opentype/noto",
            "/usr/share/fonts/truetype/droid",
            "/usr/share/fonts/truetype/dejavu",
            "/usr/share/fonts/truetype/liberation",
        ]
        for d in dirs:
            p = os.path.join(d, filename)
            if os.path.isfile(p):
                return os.path.abspath(p)
        return os.path.join(self.fonts_dir, filename)
