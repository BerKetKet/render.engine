__version__ = "1.6.1"
"""
kindle_render v1.6.1 — Universal, viewport-independent EPUB typography, pagination, and rasterization engine.

Core compute mechanisms:
- Subpixel 26.6 fixed-point glyph advance scaling via IEEE-754 float32 LSB-difference quantization
- Backward dynamic programming paragraph line-breaking with quadratic stretch/shrink/ragged badness, 7-line sliding-window hyphenation history bitmask, terminal-word hyphen guard, and runt-line linear penalty
- Double-array compiled state-machine hyphenation trie lookup with language-specific minimum prefix/suffix guards
- OpenType GSUB/GPOS complex-script shaping (Devanagari, CJK/Hangul, Arabic, Hebrew, Ethiopic) with UAX #14 ideographic break opportunities and COLR/CPAL multi-layer vector glyph compositing
- FreeType light-autohinted 256-level grayscale outline rasterization with anisotropic synthetic emboldening
"""
from .config import Config, PALETTES
from .fonts import Family, Face
from .epub import Block, load_epub
from .layout import Run, Box, Glue, Penalty, build_items, make_lines, layout_line
from .page import render_blocks, render_lines
from .compare import compare, print_report
