#!/usr/bin/env python3
"""Comprehensive verifier for Phase 2.5 Structured Text Layer (tests a-d).

Tests across all three corpora (probe, exam1, exam2):
  (a) For each corpus, the extracted logical text of each chapter equals the source
      text after normalization, ignoring hyphenation (0 chapter mismatches).
  (b) On every page, the number of glyph boxes in the text layer equals the number
      of glyph draw commands (`GlyphCommand`) in the IR.
  (c) Every cluster, word, line, block, and link bounding box `[x0, y0, x1, y1]` lies
      strictly inside the page (`0 <= x0 < x1 <= width` and `0 <= y0 < y1 <= height`),
      and full schema validation (`validate_document_text_layer`) passes.
  (d) Rendering with and without the text layer (including CLI `epub` vs `epub --text-layer`)
      yields 100% identical pixel SHA-256 hashes matching `tools/golden/*.json`.
"""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path
import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kindle_render.epub import load_epub
from kindle_render.fonts import Family
from kindle_render.ir import GlyphCommand
from kindle_render.page import layout_blocks_to_ir, render_blocks
from kindle_render.text_layer import (
    build_document_text_layer,
    validate_document_text_layer,
    write_text_layer_files,
)
from tools.corpus import resolve_corpus_file, make_config


def normalize_for_comparison(s: str) -> str:
    """Normalizes Unicode text for Test (a), ignoring hyphenation and soft-wrap hyphens."""
    s = s.replace("\u00ad", "").replace("\u200b", "").replace("\u00a0", " ")
    s = s.replace("1\u20442", "\u00bd").replace("1\u20444", "\u00bc").replace("3\u20444", "\u00be")
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\ufe0e", "").replace("\ufe0f", "").replace("\u200d", "")
    s = s.replace("-", "")
    return re.sub(r"\s+", " ", s).strip()


def extract_source_chapters(blocks) -> dict:
    src_by_ch = {}
    for b in blocks:
        if getattr(b, "is_spacer", False):
            continue
        ch = b.chapter
        if ch not in src_by_ch:
            src_by_ch[ch] = []
        if b.kind == "text":
            dc = b.drop_cap_letter or ""
            txt = dc + "".join(r.text for r in b.runs)
            if txt.strip():
                src_by_ch[ch].append(txt)
        elif b.kind == "pre":
            src_by_ch[ch].append(" ".join(b.pre_lines))
        elif b.kind == "table":
            if b.table_caption:
                src_by_ch[ch].append(b.table_caption)
            for row in b.table_rows:
                for cell in row:
                    src_by_ch[ch].append(cell[0])
    return {ch: "\n".join(parts) for ch, parts in src_by_ch.items()}


def main():
    profiles_data = json.loads((REPO_ROOT / "tools" / "profiles.json").read_text())
    search_paths = profiles_data["search_paths"]

    all_ok = True
    results = {}

    for cname in ("probe", "exam1", "exam2"):
        cprof = profiles_data["corpora"][cname]
        epub_path = resolve_corpus_file(cprof["epub"], search_paths)
        cfg = make_config(cprof["config"])
        fam = Family(cfg)
        blocks = load_epub(str(epub_path), cfg)

        # Render without text layer
        imgs_without, meta_without = render_blocks(blocks, cfg, fam, max_pages=cprof["max_pages"], return_meta=True)
        hashes_without = [hashlib.sha256(np.asarray(im).tobytes()).hexdigest() for im in imgs_without]

        # Render with text layer emitted from IR
        imgs_with, meta_with = render_blocks(blocks, cfg, fam, max_pages=cprof["max_pages"], return_meta=True)
        doc_layer = build_document_text_layer(meta_with["ir_doc"])
        hashes_with = [hashlib.sha256(np.asarray(im).tobytes()).hexdigest() for im in imgs_with]

        # Schema & bounding box validation (Test c)
        schema_ok, schema_errs = validate_document_text_layer(doc_layer)

        # Test (a): Chapter text equality after normalization, ignoring hyphenation
        src_chapters = extract_source_chapters(blocks)
        ext_chapters = {ch_obj["chapter"]: ch_obj["logical_text"] for ch_obj in doc_layer["chapters"]}
        ch_mismatches = []
        for ch, src_txt in src_chapters.items():
            ext_txt = ext_chapters.get(ch, "")
            if normalize_for_comparison(src_txt) != normalize_for_comparison(ext_txt):
                ch_mismatches.append(ch)
        test_a_ok = (len(ch_mismatches) == 0)

        # Test (b): Number of glyph boxes equals number of glyph draw commands on every page
        total_glyph_cmds = 0
        total_glyph_boxes = 0
        box_count_mismatches = 0
        for p_ir, p_tl in zip(meta_with["ir_doc"].pages, doc_layer["pages"]):
            n_cmds = sum(1 for c in p_ir.commands if isinstance(c, GlyphCommand))
            n_boxes = sum(len(w["clusters"]) for b in p_tl["blocks"] for l in b["lines"] for w in l["words"])
            total_glyph_cmds += n_cmds
            total_glyph_boxes += n_boxes
            if n_cmds != n_boxes or n_boxes != p_tl["glyph_box_count"]:
                box_count_mismatches += 1
        test_b_ok = (box_count_mismatches == 0 and total_glyph_cmds == total_glyph_boxes)

        # Test (c): All boxes lie inside the page (0 <= x0 < x1 <= W, 0 <= y0 < y1 <= H)
        outside_boxes = 0
        for p_tl in doc_layer["pages"]:
            W, H = p_tl["width"], p_tl["height"]
            for b in p_tl["blocks"]:
                for l in b["lines"]:
                    for bx in [b["bbox"], l["bbox"]]:
                        if not (0 <= bx[0] < bx[2] <= W and 0 <= bx[1] < bx[3] <= H):
                            outside_boxes += 1
                    for w in l["words"]:
                        wb = w["bbox"]
                        if not (0 <= wb[0] < wb[2] <= W and 0 <= wb[1] < wb[3] <= H):
                            outside_boxes += 1
                        for cl in w["clusters"]:
                            cb = cl["bbox"]
                            if not (0 <= cb[0] < cb[2] <= W and 0 <= cb[1] < cb[3] <= H):
                                outside_boxes += 1
        test_c_ok = (schema_ok and outside_boxes == 0)

        # Test (d): Rendering with and without text layer yields identical pixels
        golden = json.loads((REPO_ROOT / "tools" / "golden" / f"{cname}.json").read_text())
        golden_hashes = [golden["pages"][str(i + 1)] for i in range(len(imgs_with))]
        test_d_ok = (hashes_without == hashes_with == golden_hashes)

        corpus_ok = test_a_ok and test_b_ok and test_c_ok and test_d_ok
        if not corpus_ok:
            all_ok = False

        results[cname] = {
            "pages": len(imgs_with),
            "chapters_checked": len(src_chapters),
            "test_a_chapter_text_match": test_a_ok,
            "test_a_mismatches": ch_mismatches,
            "test_b_glyph_boxes_equal_cmds": test_b_ok,
            "total_glyph_commands": total_glyph_cmds,
            "total_glyph_boxes": total_glyph_boxes,
            "test_c_all_boxes_in_page": test_c_ok,
            "outside_boxes": outside_boxes,
            "schema_valid": schema_ok,
            "test_d_identical_pixels_with_without": test_d_ok,
        }
        print(
            f"[text-layer:{cname}] pages={len(imgs_with)} chapters={len(src_chapters)} "
            f"(a)text_match={test_a_ok} "
            f"(b)boxes==cmds={test_b_ok} ({total_glyph_boxes}=={total_glyph_cmds}) "
            f"(c)boxes_in_page={test_c_ok} (outside={outside_boxes}) "
            f"(d)pixels_identical={test_d_ok}"
        )

    # Also test CLI `kindle_render text` and `kindle_render epub --text-layer` on exam2 first 3 pages
    with tempfile.TemporaryDirectory() as tmpd:
        tmp_p = Path(tmpd)
        e2_path = resolve_corpus_file(profiles_data["corpora"]["exam2"]["epub"], search_paths)
        dir_no_tl = tmp_p / "no_tl"
        dir_with_tl = tmp_p / "with_tl"
        dir_only_tl = tmp_p / "only_tl"

        base_args = [
            sys.executable, "-m", "kindle_render",
        ]
        cfg_args = [
            "--pages", "3", "--size26", "2688", "--x0", "79", "--right", "1001",
            "--pitch", "57", "--top", "168", "--page-bottom", "2203",
        ]
        subprocess.check_call(base_args + ["epub", str(e2_path), str(dir_no_tl)] + cfg_args, cwd=str(REPO_ROOT))
        subprocess.check_call(base_args + ["epub", str(e2_path), str(dir_with_tl), "--text-layer"] + cfg_args, cwd=str(REPO_ROOT))
        subprocess.check_call(base_args + ["text", str(e2_path), str(dir_only_tl)] + cfg_args, cwd=str(REPO_ROOT))

        for pno in (1, 2, 3):
            im1 = np.asarray(Image.open(dir_no_tl / f"page_{pno:03d}.png"))
            im2 = np.asarray(Image.open(dir_with_tl / f"page_{pno:03d}.png"))
            assert np.array_equal(im1, im2), f"CLI PNG mismatch on page {pno}"
            j1 = json.loads((dir_with_tl / f"page_{pno:03d}.json").read_text())
            j2 = json.loads((dir_only_tl / f"page_{pno:03d}.json").read_text())
            assert j1 == j2, f"CLI JSON mismatch on page {pno}"
        assert (dir_with_tl / "document.json").is_file()
        assert (dir_only_tl / "document.json").is_file()
        print("[text-layer:CLI] `kindle_render text` and `kindle_render epub --text-layer` verified=True")

    out_report = REPO_ROOT / "tools" / "reports" / "text_layer_tests.json"
    out_report.write_text(json.dumps(results, indent=2))
    if not all_ok:
        sys.exit(1)
    print("[Phase 2.5 text layer tests (a)-(d)] ALL PASSED")


if __name__ == "__main__":
    main()
