__version__ = "1.10.0"
"""
kindle_render v1.9.0 — Universal, viewport-independent EPUB typography, pagination, IR layout, structured text layer, and rasterization engine.

Core compute mechanisms:
- Decoupled layout-to-IR (`PositionedDocument` / `PositionedPage` / `RenderCommand`) and instance-owned FreeType rasterization (`render_to_ir`, `rasterize`, `Rasterizer`)
- Structured text layer extraction (`build_page_text_layer`, `build_document_text_layer`) with word/cluster bounding boxes, reading order, ligature expansion, RTL logical ordering, and synthetic hyphen tagging
- Subpixel 26.6 fixed-point glyph advance scaling via IEEE-754 float32 LSB-difference quantization
- Backward dynamic programming paragraph line-breaking with quadratic stretch/shrink/ragged badness, 8-bit sliding-window hyphenation history bitmask, terminal-word hyphen guard, and runt-line linear penalty
- Double-array compiled state-machine hyphenation trie lookup with language-specific minimum prefix/suffix guards
- OpenType GSUB/GPOS complex-script shaping (Devanagari, CJK/Hangul, Arabic, Hebrew, Ethiopic, Thai) with UAX #14 ideographic break opportunities and COLR/CPAL multi-layer vector glyph compositing
- FreeType light-autohinted 256-level grayscale outline rasterization with anisotropic synthetic emboldening
"""
from pathlib import Path
from typing import Optional, Union
from .config import Config, PALETTES
from .fonts import Family, Face
from .epub import Block, load_epub
from .layout import Run, Box, Glue, Penalty, build_items, make_lines, layout_line
from .ir import (
    IR_VERSION,
    PositionedDocument,
    PositionedPage,
    GlyphCommand,
    RectCommand,
    RuleCommand,
    RingBulletCommand,
    ImageCommand,
    TextBlockMeta,
)
from .page import layout_blocks_to_ir, layout_lines_to_ir, render_blocks, render_lines
from .raster import Rasterizer, rasterize
from .text_layer import (
    build_page_text_layer,
    build_document_text_layer,
    validate_page_text_layer,
    validate_document_text_layer,
    write_text_layer_files,
)
from .compare import compare, print_report


def render_to_ir(book: Union[str, Path, list], cfg: Optional[Config] = None, max_pages: Optional[int] = None) -> PositionedDocument:
    """Lays out an EPUB file path (or pre-parsed Block list) into a PositionedDocument IR without invoking FreeType."""
    use_cfg = cfg or Config()
    fam = Family(use_cfg)
    if isinstance(book, (str, Path)):
        blocks = load_epub(str(book), use_cfg)
    else:
        blocks = list(book)
    return layout_blocks_to_ir(blocks, use_cfg, fam, max_pages=max_pages)
