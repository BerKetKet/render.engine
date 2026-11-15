"""Structured text layer extraction and schema validation from PositionedDocument / PositionedPage IR.

Emits per-page and per-document JSON structures directly from the IR without recomputing layout
or invoking FreeType/rasterization.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from .ir import PositionedDocument, PositionedPage, GlyphCommand, TextBlockMeta

SCHEMA_VERSION = "1.0"


def _union_bbox(boxes: List[List[int]], page_w: int, page_h: int) -> List[int]:
    if not boxes:
        return [0, 0, min(1, page_w), min(1, page_h)]
    x0 = max(0, min(b[0] for b in boxes))
    y0 = max(0, min(b[1] for b in boxes))
    x1 = min(page_w, max(b[2] for b in boxes))
    y1 = min(page_h, max(b[3] for b in boxes))
    if x1 <= x0:
        x1 = min(page_w, x0 + 1)
    if y1 <= y0:
        y1 = min(page_h, y0 + 1)
    return [int(x0), int(y0), int(x1), int(y1)]


def _cluster_dict(cmd: GlyphCommand, page_w: int, page_h: int) -> Dict[str, Any]:
    bx0, by0, bx1, by1 = cmd.bbox
    cx0 = max(0, min(page_w - 1, int(bx0)))
    cy0 = max(0, min(page_h - 1, int(by0)))
    cx1 = max(cx0 + 1, min(page_w, int(bx1)))
    cy1 = max(cy0 + 1, min(page_h, int(by1)))
    return {
        "text": cmd.unicode_text,
        "glyph_name": cmd.glyph_name,
        "glyph_id": int(cmd.glyph_id),
        "font_id": cmd.font_id,
        "size26": int(cmd.size26),
        "x": int(cmd.x),
        "baseline": int(cmd.baseline),
        "bbox": [cx0, cy0, cx1, cy1],
        "is_synthetic_hyphen": bool(cmd.is_synthetic_hyphen),
        "is_list_marker": bool(cmd.is_list_marker),
        "is_drop_cap": bool(cmd.is_drop_cap),
        "is_ligature": bool(cmd.is_ligature),
        "direction": cmd.direction,
        "logical_char_idx": int(cmd.logical_char_idx),
        "link_href": cmd.link_href,
    }


def build_page_text_layer(ir_page: PositionedPage) -> Dict[str, Any]:
    W, H = int(ir_page.width), int(ir_page.height)
    glyph_cmds = [c for c in ir_page.commands if isinstance(c, GlyphCommand)]
    block_meta_map: Dict[int, TextBlockMeta] = {bm.block_idx: bm for bm in ir_page.blocks}

    # Group glyph commands by block_idx -> line_idx
    by_block: Dict[int, Dict[int, List[GlyphCommand]]] = {}
    block_order: List[int] = [bm.block_idx for bm in ir_page.blocks]
    for g in glyph_cmds:
        b_idx = g.block_idx
        if b_idx not in block_order:
            block_order.append(b_idx)
        by_block.setdefault(b_idx, {}).setdefault(g.line_idx, []).append(g)

    blocks_out: List[Dict[str, Any]] = []
    links_out: List[Dict[str, Any]] = []

    for r_ord, b_idx in enumerate(block_order):
        bm = block_meta_map.get(b_idx)
        b_kind = bm.kind if bm else "paragraph"
        lines_map = by_block.get(b_idx, {})
        lines_out: List[Dict[str, Any]] = []
        block_line_bboxes: List[List[int]] = []

        for l_ord, l_idx in enumerate(sorted(lines_map.keys())):
            l_glyphs = lines_map[l_idx]
            baseline_val = int(l_glyphs[-1].baseline) if l_glyphs else 0
            ends_with_synth_hy = any(g.is_synthetic_hyphen for g in l_glyphs)

            # Separate list marker glyphs (word_idx == -1) from content words ( grouped by logical_word_idx )
            marker_glyphs = [g for g in l_glyphs if g.is_list_marker]
            content_glyphs = [g for g in l_glyphs if not g.is_list_marker]

            words_by_lw: Dict[int, List[GlyphCommand]] = {}
            for g in content_glyphs:
                words_by_lw.setdefault(g.logical_word_idx, []).append(g)

            words_out: List[Dict[str, Any]] = []
            w_read_ord = 0

            if marker_glyphs:
                m_clusters = [_cluster_dict(g, W, H) for g in marker_glyphs]
                m_bbox = _union_bbox([c["bbox"] for c in m_clusters], W, H)
                words_out.append({
                    "word_idx": -1,
                    "logical_word_idx": -1,
                    "reading_order": w_read_ord,
                    "is_list_marker": True,
                    "text": "".join(c["text"] for c in m_clusters),
                    "direction": "ltr",
                    "link_href": None,
                    "bbox": m_bbox,
                    "clusters": m_clusters,
                })
                w_read_ord += 1

            for lw_idx in sorted(words_by_lw.keys()):
                w_gs = words_by_lw[lw_idx]
                w_dir = "rtl" if any(g.direction == "rtl" for g in w_gs) else "ltr"
                if w_dir == "rtl":
                    w_gs_ordered = sorted(w_gs, key=lambda g: (1 if g.is_synthetic_hyphen else 0, g.logical_char_idx))
                elif any(g.is_drop_cap for g in w_gs):
                    w_gs_ordered = sorted(w_gs, key=lambda g: (0 if g.is_drop_cap else 1))
                else:
                    w_gs_ordered = w_gs

                w_clusters = [_cluster_dict(g, W, H) for g in w_gs_ordered]
                w_bbox = _union_bbox([c["bbox"] for c in w_clusters], W, H)
                logical_w_text = "".join(c["text"] for c in w_clusters if not c["is_synthetic_hyphen"])
                w_href = next((c["link_href"] for c in w_clusters if c["link_href"]), None)

                words_out.append({
                    "word_idx": int(w_gs_ordered[0].word_idx),
                    "logical_word_idx": int(lw_idx),
                    "reading_order": w_read_ord,
                    "is_list_marker": False,
                    "text": logical_w_text,
                    "direction": w_dir,
                    "link_href": w_href,
                    "bbox": w_bbox,
                    "clusters": w_clusters,
                })
                w_read_ord += 1

            line_bbox = _union_bbox([w["bbox"] for w in words_out], W, H)
            block_line_bboxes.append(line_bbox)
            line_logical_text = " ".join(w["text"] for w in words_out if not w["is_list_marker"] and w["text"])

            # Collect link spans on this line
            link_groups: Dict[str, List[Dict[str, Any]]] = {}
            for w in words_out:
                if w["link_href"]:
                    link_groups.setdefault(w["link_href"], []).append(w)
            for href, lw_list in link_groups.items():
                links_out.append({
                    "href": href,
                    "text": " ".join(w["text"] for w in lw_list if w["text"]),
                    "bbox": _union_bbox([w["bbox"] for w in lw_list], W, H),
                })

            lines_out.append({
                "line_idx": int(l_idx),
                "reading_order": l_ord,
                "baseline": baseline_val,
                "bbox": line_bbox,
                "ends_with_synthetic_hyphen": ends_with_synth_hy,
                "logical_text": line_logical_text,
                "words": words_out,
            })

        # Compute logical text for this block on this page
        if b_kind in ("paragraph", "heading", "list_item"):
            all_words_map: Dict[int, List[str]] = {}
            for ln in lines_out:
                for w in ln["words"]:
                    if not w["is_list_marker"] and w["text"]:
                        all_words_map.setdefault(w["logical_word_idx"], []).append(w["text"])
            block_logical_text = " ".join("".join(parts) for _, parts in sorted(all_words_map.items()))
        else:
            b_parts = []
            for idx_l, ln in enumerate(lines_out):
                ls = ln["logical_text"]
                b_parts.append(ls)
                if idx_l + 1 < len(lines_out):
                    no_sp = ln["ends_with_synthetic_hyphen"] or ls.endswith(("-", "/", "_"))
                    if not no_sp:
                        b_parts.append(" ")
            block_logical_text = "".join(b_parts)

        block_bbox = _union_bbox(block_line_bboxes, W, H) if block_line_bboxes else [0, 0, min(1, W), min(1, H)]
        blocks_out.append({
            "reading_order": r_ord,
            "block_idx": int(b_idx),
            "chapter": bm.chapter if bm else ir_page.chapter,
            "kind": b_kind,
            "heading_level": int(bm.heading_level) if bm else 0,
            "list_level": int(bm.list_level) if bm else 0,
            "list_marker": bm.list_marker if bm else None,
            "table_caption": bm.table_caption if bm else None,
            "table_rows": bm.table_rows if bm else None,
            "bbox": block_bbox,
            "logical_text": block_logical_text,
            "lines": lines_out,
        })

    total_clusters = sum(
        len(w["clusters"])
        for b in blocks_out
        for l in b["lines"]
        for w in l["words"]
    )
    page_logical_text = "\n".join(b["logical_text"] for b in blocks_out if b["logical_text"])

    return {
        "schema_version": SCHEMA_VERSION,
        "ir_version": ir_page.ir_version,
        "page_number": int(ir_page.page_number),
        "chapter": ir_page.chapter,
        "width": W,
        "height": H,
        "glyph_command_count": len(glyph_cmds),
        "glyph_box_count": total_clusters,
        "logical_text": page_logical_text,
        "links": links_out,
        "blocks": blocks_out,
    }


def build_document_text_layer(ir_doc: PositionedDocument) -> Dict[str, Any]:
    page_layers = [build_page_text_layer(p) for p in ir_doc.pages]

    # Reconstruct full logical text per chapter across pages (merging split blocks across page boundaries)
    chapters_order: List[str] = []
    ch_pages: Dict[str, List[int]] = {}
    ch_blocks: Dict[str, Dict[int, List[Dict[str, Any]]]] = {}

    for p_layer in page_layers:
        ch = p_layer["chapter"]
        pno = p_layer["page_number"]
        if ch not in ch_pages:
            chapters_order.append(ch)
            ch_pages[ch] = []
            ch_blocks[ch] = {}
        ch_pages[ch].append(pno)
        for b in p_layer["blocks"]:
            ch_blocks[ch].setdefault(b["block_idx"], []).append(b)

    chapters_out: List[Dict[str, Any]] = []
    for ch in chapters_order:
        b_map = ch_blocks[ch]
        ch_block_texts: List[str] = []
        for b_idx in sorted(b_map.keys()):
            b_parts_on_pages = b_map[b_idx]
            b_kind = b_parts_on_pages[0]["kind"]
            all_lines = [ln for bp in b_parts_on_pages for ln in bp["lines"]]
            if not all_lines:
                continue
            if b_kind in ("paragraph", "heading", "list_item"):
                words_map: Dict[int, List[str]] = {}
                for ln in all_lines:
                    for w in ln["words"]:
                        if not w["is_list_marker"] and w["text"]:
                            words_map.setdefault(w["logical_word_idx"], []).append(w["text"])
                b_txt = " ".join("".join(ps) for _, ps in sorted(words_map.items()))
            else:
                l_parts = []
                for idx_l, ln in enumerate(all_lines):
                    ls = ln["logical_text"]
                    l_parts.append(ls)
                    if idx_l + 1 < len(all_lines):
                        no_sp = ln["ends_with_synthetic_hyphen"] or ls.endswith(("-", "/", "_"))
                        if not no_sp:
                            l_parts.append(" ")
                b_txt = "".join(l_parts)
            if b_txt:
                ch_block_texts.append(b_txt)

        chapters_out.append({
            "chapter": ch,
            "start_page": min(ch_pages[ch]),
            "end_page": max(ch_pages[ch]),
            "logical_text": "\n".join(ch_block_texts),
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "ir_version": ir_doc.ir_version,
        "engine_version": ir_doc.engine_version,
        "screen_w": int(ir_doc.screen_w),
        "screen_h": int(ir_doc.screen_h),
        "page_count": len(page_layers),
        "chapters": chapters_out,
        "pages": page_layers,
    }


def validate_page_text_layer(page_layer: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    req_top = ("schema_version", "ir_version", "page_number", "chapter", "width", "height", "glyph_command_count", "glyph_box_count", "logical_text", "links", "blocks")
    for k in req_top:
        if k not in page_layer:
            errors.append(f"Missing top-level key '{k}'")
    if errors:
        return False, errors

    W, H = page_layer["width"], page_layer["height"]

    def _chk_bbox(bbox, ctx: str):
        if not isinstance(bbox, list) or len(bbox) != 4 or not all(isinstance(v, int) for v in bbox):
            errors.append(f"{ctx}: invalid bbox format {bbox}")
            return
        x0, y0, x1, y1 = bbox
        if not (0 <= x0 < x1 <= W and 0 <= y0 < y1 <= H):
            errors.append(f"{ctx}: bbox {bbox} outside page (0..{W}, 0..{H})")

    cluster_cnt = 0
    for bi, b in enumerate(page_layer["blocks"]):
        for bk in ("reading_order", "block_idx", "chapter", "kind", "heading_level", "list_level", "bbox", "logical_text", "lines"):
            if bk not in b:
                errors.append(f"block[{bi}]: missing '{bk}'")
        if b.get("lines"):
            _chk_bbox(b["bbox"], f"block[{bi}]")
        for li, l in enumerate(b.get("lines", [])):
            for lk in ("line_idx", "reading_order", "baseline", "bbox", "ends_with_synthetic_hyphen", "logical_text", "words"):
                if lk not in l:
                    errors.append(f"block[{bi}].line[{li}]: missing '{lk}'")
            _chk_bbox(l["bbox"], f"block[{bi}].line[{li}]")
            for wi, w in enumerate(l.get("words", [])):
                for wk in ("word_idx", "logical_word_idx", "reading_order", "text", "direction", "bbox", "clusters"):
                    if wk not in w:
                        errors.append(f"block[{bi}].line[{li}].word[{wi}]: missing '{wk}'")
                _chk_bbox(w["bbox"], f"block[{bi}].line[{li}].word[{wi}]")
                for ci, c in enumerate(w.get("clusters", [])):
                    cluster_cnt += 1
                    for ck in ("text", "glyph_name", "glyph_id", "font_id", "size26", "x", "baseline", "bbox", "is_synthetic_hyphen", "is_ligature", "direction"):
                        if ck not in c:
                            errors.append(f"cluster[{bi},{li},{wi},{ci}]: missing '{ck}'")
                    _chk_bbox(c["bbox"], f"cluster[{bi},{li},{wi},{ci}]")

    if cluster_cnt != page_layer["glyph_box_count"]:
        errors.append(f"cluster_cnt {cluster_cnt} != glyph_box_count {page_layer['glyph_box_count']}")
    if page_layer["glyph_box_count"] != page_layer["glyph_command_count"]:
        errors.append(f"glyph_box_count {page_layer['glyph_box_count']} != glyph_command_count {page_layer['glyph_command_count']}")

    return (len(errors) == 0), errors


def validate_document_text_layer(doc_layer: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    for k in ("schema_version", "ir_version", "engine_version", "screen_w", "screen_h", "page_count", "chapters", "pages"):
        if k not in doc_layer:
            errors.append(f"Missing document key '{k}'")
    if errors:
        return False, errors
    if len(doc_layer["pages"]) != doc_layer["page_count"]:
        errors.append("len(pages) != page_count")
    for p in doc_layer["pages"]:
        ok, p_errs = validate_page_text_layer(p)
        if not ok:
            errors.extend([f"page_{p.get('page_number')}: {e}" for e in p_errs])
    return (len(errors) == 0), errors


def write_text_layer_files(ir_doc: PositionedDocument, out_dir: Path) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc_layer = build_document_text_layer(ir_doc)
    ok, errs = validate_document_text_layer(doc_layer)
    if not ok:
        raise ValueError(f"Text layer validation failed: {errs[:5]}")
    for p_layer in doc_layer["pages"]:
        pno = p_layer["page_number"]
        with open(out_dir / f"page_{pno:03d}.json", "w", encoding="utf-8") as pf:
            json.dump(p_layer, pf, indent=2, ensure_ascii=False)
    with open(out_dir / "document.json", "w", encoding="utf-8") as df:
        json.dump(doc_layer, df, indent=2, ensure_ascii=False)
    return doc_layer
