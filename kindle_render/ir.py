"""Serializable Intermediate Representation (IR) between layout and rasterization.

Defines:
- IR_VERSION = "1.0"
- RenderCommand hierarchy: GlyphCommand, RectCommand, RuleCommand, RingBulletCommand, ImageCommand
- Text layer metadata attached during layout: TextClusterMeta, TextWordMeta, TextLineMeta, TextBlockMeta
- PositionedPage and PositionedDocument with canonical JSON serialization and SHA-256 layout hashing
"""
import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

IR_VERSION = "1.0"


def _fmt_val(v: Any) -> Any:
    if isinstance(v, float):
        return f"{v:.6f}"
    if isinstance(v, (list, tuple)):
        return [_fmt_val(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _fmt_val(val) for k, val in sorted(v.items())}
    return v


@dataclass
class GlyphCommand:
    font_id: str
    font_path: str
    glyph_id: int
    glyph_name: str
    size26: int
    boldness_level: int
    x: int
    baseline: int
    start26: int
    off26: int
    adv26: int
    dx_px: int = 0
    dy_px: int = 0
    color: Tuple[int, int, int] = (0, 0, 0)
    colr_layers: Optional[List[Tuple[str, int, Tuple[int, int, int]]]] = None
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    unicode_text: str = ""
    is_synthetic_hyphen: bool = False
    is_list_marker: bool = False
    is_table_chrome: bool = False
    is_drop_cap: bool = False
    is_ligature: bool = False
    block_idx: int = -1
    line_idx: int = -1
    word_idx: int = -1
    logical_word_idx: int = -1
    logical_char_idx: int = 0
    direction: str = "ltr"
    link_href: Optional[str] = None
    kind: str = "glyph"

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "kind": "glyph",
            "font_id": self.font_id,
            "glyph_id": int(self.glyph_id),
            "glyph_name": self.glyph_name,
            "size26": int(self.size26),
            "boldness_level": int(self.boldness_level),
            "x": int(self.x),
            "baseline": int(self.baseline),
            "start26": int(self.start26),
            "off26": int(self.off26),
            "adv26": int(self.adv26),
            "dx_px": int(self.dx_px),
            "dy_px": int(self.dy_px),
            "color": list(self.color),
            "bbox": list(self.bbox),
            "unicode_text": self.unicode_text,
            "is_synthetic_hyphen": bool(self.is_synthetic_hyphen),
            "is_list_marker": bool(self.is_list_marker),
            "is_table_chrome": bool(self.is_table_chrome),
            "is_drop_cap": bool(self.is_drop_cap),
            "is_ligature": bool(self.is_ligature),
            "block_idx": int(self.block_idx),
            "line_idx": int(self.line_idx),
            "word_idx": int(self.word_idx),
            "logical_word_idx": int(self.logical_word_idx),
            "logical_char_idx": int(self.logical_char_idx),
            "direction": self.direction,
            "link_href": self.link_href,
        }
        if self.colr_layers:
            d["colr_layers"] = [
                {"glyph_name": gn, "glyph_id": int(gid), "color": list(col)}
                for gn, gid, col in self.colr_layers
            ]
        return d


@dataclass
class RectCommand:
    x0: int
    y0: int
    x1: int
    y1: int
    color: Tuple[int, int, int]
    role: str = "rect"
    kind: str = "rect"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": "rect",
            "role": self.role,
            "x0": int(self.x0),
            "y0": int(self.y0),
            "x1": int(self.x1),
            "y1": int(self.y1),
            "color": list(self.color),
        }


@dataclass
class RuleCommand:
    x0: int
    y0: int
    x1: int
    y1: int
    color: Tuple[int, int, int]
    role: str = "rule"
    link_href: Optional[str] = None
    kind: str = "rule"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": "rule",
            "role": self.role,
            "x0": int(self.x0),
            "y0": int(self.y0),
            "x1": int(self.x1),
            "y1": int(self.y1),
            "color": list(self.color),
            "link_href": self.link_href,
        }


@dataclass
class RingBulletCommand:
    cx: int
    cy: int
    r: int
    color: Tuple[int, int, int]
    kind: str = "ring_bullet"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": "ring_bullet",
            "cx": int(self.cx),
            "cy": int(self.cy),
            "r": int(self.r),
            "color": list(self.color),
        }


@dataclass
class ImageCommand:
    x: int
    y: int
    width: int
    height: int
    pixels: np.ndarray
    role: str = "image"
    image_sha256: str = ""
    kind: str = "image"

    def __post_init__(self):
        if not self.image_sha256 and self.pixels is not None:
            arr_u8 = np.asarray(self.pixels, dtype=np.uint8)
            self.image_sha256 = hashlib.sha256(arr_u8.tobytes()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": "image",
            "role": self.role,
            "x": int(self.x),
            "y": int(self.y),
            "width": int(self.width),
            "height": int(self.height),
            "image_sha256": self.image_sha256,
        }


@dataclass
class TextBlockMeta:
    block_idx: int
    chapter: str
    kind: str
    heading_level: int = 0
    list_level: int = 0
    list_marker: Optional[str] = None
    table_caption: Optional[str] = None
    table_rows: Optional[List[List[Dict[str, Any]]]] = None
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "block_idx": int(self.block_idx),
            "chapter": self.chapter,
            "kind": self.kind,
            "heading_level": int(self.heading_level),
            "list_level": int(self.list_level),
            "list_marker": self.list_marker,
            "bbox": list(self.bbox),
        }
        if self.table_caption is not None:
            d["table_caption"] = self.table_caption
        if self.table_rows is not None:
            d["table_rows"] = self.table_rows
        return d


@dataclass
class PositionedPage:
    page_number: int
    chapter: str
    width: int
    height: int
    bg: Tuple[int, int, int] = (255, 255, 255)
    fg: Tuple[int, int, int] = (0, 0, 0)
    commands: List[Any] = field(default_factory=list)
    blocks: List[TextBlockMeta] = field(default_factory=list)
    ir_version: str = IR_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return _fmt_val({
            "ir_version": self.ir_version,
            "page_number": int(self.page_number),
            "chapter": self.chapter,
            "width": int(self.width),
            "height": int(self.height),
            "bg": list(self.bg),
            "fg": list(self.fg),
            "commands": [cmd.to_dict() for cmd in self.commands],
            "blocks": [b.to_dict() for b in self.blocks],
        })

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def layout_sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass
class PositionedDocument:
    pages: List[PositionedPage] = field(default_factory=list)
    chapter_errors: List[Dict[str, Any]] = field(default_factory=list)
    screen_w: int = 1080
    screen_h: int = 2340
    bg: Tuple[int, int, int] = (255, 255, 255)
    fg: Tuple[int, int, int] = (0, 0, 0)
    engine_version: str = "1.8.0-rc1"
    ir_version: str = IR_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return _fmt_val({
            "ir_version": self.ir_version,
            "engine_version": self.engine_version,
            "screen_w": int(self.screen_w),
            "screen_h": int(self.screen_h),
            "bg": list(self.bg),
            "fg": list(self.fg),
            "page_count": len(self.pages),
            "chapter_errors": self.chapter_errors,
            "pages": [p.to_dict() for p in self.pages],
        })
