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
    dash: Optional[Tuple[int, int]] = None
    dash_phase: int = 0
    kind: str = "rule"

    def to_dict(self) -> Dict[str, Any]:
        is_fl = (self.role == "link_underline")
        out = {
            "kind": "rule",
            "role": self.role,
            "x0": round(float(self.x0), 6) if is_fl else int(self.x0),
            "y0": round(float(self.y0), 6) if is_fl else int(self.y0),
            "x1": round(float(self.x1), 6) if is_fl else int(self.x1),
            "y1": round(float(self.y1), 6) if is_fl else int(self.y1),
            "color": list(self.color),
            "link_href": self.link_href,
        }
        if self.dash is not None:
            out["dash"] = [int(self.dash[0]), int(self.dash[1])]
            out["dash_phase"] = int(self.dash_phase)
        return out


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
    engine_version: str = "1.9.0"
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

    @classmethod
    def from_dict(cls, d: Dict[str, Any], image_store: Optional[Dict[str, np.ndarray]] = None) -> "PositionedDocument":
        pages = [PositionedPage.from_dict(p, image_store=image_store) for p in d.get("pages", [])]
        return cls(
            pages=pages,
            chapter_errors=list(d.get("chapter_errors", [])),
            screen_w=int(d.get("screen_w", 1080)),
            screen_h=int(d.get("screen_h", 2340)),
            bg=tuple(int(x) for x in d.get("bg", (255, 255, 255))),
            fg=tuple(int(x) for x in d.get("fg", (0, 0, 0))),
            engine_version=str(d.get("engine_version", "1.9.0")),
            ir_version=str(d.get("ir_version", IR_VERSION)),
        )


def _cmd_from_dict(d: Dict[str, Any], image_store: Optional[Dict[str, np.ndarray]] = None) -> Any:
    k = d.get("kind")
    if k == "glyph":
        colr = None
        if d.get("colr_layers"):
            colr = [
                (str(layer["glyph_name"]), int(layer["glyph_id"]), tuple(int(c) for c in layer["color"]))
                for layer in d["colr_layers"]
            ]
        return GlyphCommand(
            font_id=str(d["font_id"]),
            font_path=str(d.get("font_path", d["font_id"])),
            glyph_id=int(d["glyph_id"]),
            glyph_name=str(d["glyph_name"]),
            size26=int(d["size26"]),
            boldness_level=int(d.get("boldness_level", 0)),
            x=int(d["x"]),
            baseline=int(d["baseline"]),
            start26=int(d["start26"]),
            off26=int(d["off26"]),
            adv26=int(d["adv26"]),
            dx_px=int(d.get("dx_px", 0)),
            dy_px=int(d.get("dy_px", 0)),
            color=tuple(int(c) for c in d.get("color", (0, 0, 0))),
            colr_layers=colr,
            bbox=tuple(int(b) for b in d.get("bbox", (0, 0, 0, 0))),
            unicode_text=str(d.get("unicode_text", "")),
            is_synthetic_hyphen=bool(d.get("is_synthetic_hyphen", False)),
            is_list_marker=bool(d.get("is_list_marker", False)),
            is_table_chrome=bool(d.get("is_table_chrome", False)),
            is_drop_cap=bool(d.get("is_drop_cap", False)),
            is_ligature=bool(d.get("is_ligature", False)),
            block_idx=int(d.get("block_idx", -1)),
            line_idx=int(d.get("line_idx", -1)),
            word_idx=int(d.get("word_idx", -1)),
            logical_word_idx=int(d.get("logical_word_idx", -1)),
            logical_char_idx=int(d.get("logical_char_idx", 0)),
            direction=str(d.get("direction", "ltr")),
            link_href=d.get("link_href"),
        )
    if k == "rect":
        return RectCommand(
            x0=int(d["x0"]),
            y0=int(d["y0"]),
            x1=int(d["x1"]),
            y1=int(d["y1"]),
            color=tuple(int(c) for c in d["color"]),
            role=str(d.get("role", "rect")),
        )
    if k == "rule":
        role = str(d.get("role", "rule"))
        is_fl = (role == "link_underline")
        dash_val = d.get("dash")
        return RuleCommand(
            x0=float(d["x0"]) if is_fl else int(d["x0"]),
            y0=float(d["y0"]) if is_fl else int(d["y0"]),
            x1=float(d["x1"]) if is_fl else int(d["x1"]),
            y1=float(d["y1"]) if is_fl else int(d["y1"]),
            color=tuple(int(c) for c in d["color"]),
            role=role,
            link_href=d.get("link_href"),
            dash=(int(dash_val[0]), int(dash_val[1])) if dash_val is not None else None,
            dash_phase=int(d.get("dash_phase", 0)),
        )
    if k == "ring_bullet":
        return RingBulletCommand(
            cx=int(d["cx"]),
            cy=int(d["cy"]),
            r=int(d["r"]),
            color=tuple(int(c) for c in d["color"]),
        )
    if k == "image":
        sha = str(d.get("image_sha256", ""))
        w, h = int(d["width"]), int(d["height"])
        px = image_store.get(sha) if (image_store and sha in image_store) else np.zeros((h, w, 3), dtype=np.uint8)
        return ImageCommand(
            x=int(d["x"]),
            y=int(d["y"]),
            width=w,
            height=h,
            pixels=px,
            role=str(d.get("role", "image")),
            image_sha256=sha,
        )
    raise ValueError(f"Unknown IR command kind: {k!r}")


def _page_from_dict(cls, d: Dict[str, Any], image_store: Optional[Dict[str, np.ndarray]] = None) -> "PositionedPage":
    cmds = [_cmd_from_dict(c, image_store=image_store) for c in d.get("commands", [])]
    blks = [
        TextBlockMeta(
            block_idx=int(b["block_idx"]),
            chapter=str(b["chapter"]),
            kind=str(b["kind"]),
            heading_level=int(b.get("heading_level", 0)),
            list_level=int(b.get("list_level", 0)),
            list_marker=b.get("list_marker"),
            table_caption=b.get("table_caption"),
            table_rows=b.get("table_rows"),
            bbox=tuple(int(x) for x in b.get("bbox", (0, 0, 0, 0))),
        )
        for b in d.get("blocks", [])
    ]
    return cls(
        page_number=int(d["page_number"]),
        chapter=str(d["chapter"]),
        width=int(d["width"]),
        height=int(d["height"]),
        bg=tuple(int(x) for x in d.get("bg", (255, 255, 255))),
        fg=tuple(int(x) for x in d.get("fg", (0, 0, 0))),
        commands=cmds,
        blocks=blks,
        ir_version=str(d.get("ir_version", IR_VERSION)),
    )


PositionedPage.from_dict = classmethod(_page_from_dict)


def validate_ir_page(page: PositionedPage) -> List[str]:
    errors: List[str] = []
    if page.ir_version != IR_VERSION:
        errors.append(f"page {page.page_number}: ir_version {page.ir_version!r} != {IR_VERSION!r}")
    W, H = int(page.width), int(page.height)
    block_ids = {int(b.block_idx) for b in page.blocks}
    for i, cmd in enumerate(page.commands):
        k = getattr(cmd, "kind", None)
        if k == "glyph":
            bx0, by0, bx1, by1 = cmd.bbox
            if not (0 <= bx0 <= bx1 <= W and 0 <= by0 <= by1 <= H):
                errors.append(f"page {page.page_number} cmd {i}: glyph bbox {cmd.bbox} outside page (0,0,{W},{H})")
            if cmd.block_idx != -1 and cmd.block_idx not in block_ids:
                errors.append(f"page {page.page_number} cmd {i}: glyph block_idx {cmd.block_idx} not in page.blocks")
        elif k in ("rect", "rule"):
            if not (0.0 <= float(cmd.x0) <= float(cmd.x1) <= float(W) and 0.0 <= float(cmd.y0) <= float(cmd.y1) <= float(H)):
                errors.append(f"page {page.page_number} cmd {i}: {k} bounds ({cmd.x0},{cmd.y0},{cmd.x1},{cmd.y1}) outside page")
        elif k == "image":
            if not (0 <= cmd.x and cmd.x + cmd.width <= W and 0 <= cmd.y and cmd.y + cmd.height <= H):
                errors.append(f"page {page.page_number} cmd {i}: image bounds outside page")
    return errors


def validate_ir_document(doc: PositionedDocument) -> List[str]:
    errors: List[str] = []
    if doc.ir_version != IR_VERSION:
        errors.append(f"doc ir_version {doc.ir_version!r} != {IR_VERSION!r}")
    for p in doc.pages:
        errors.extend(validate_ir_page(p))
    return errors
