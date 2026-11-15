#!/usr/bin/env python3
"""Vertical-rhythm block-boundary and line-band measurement harness (Step 2 [P]).

Aligns device capture line bands with engine IR blocks/lines on every page where
neighbouring line bands match in ink content (position-independent or positional),
and records:
  - previous and next block kind (paragraph, h1..h6, li, pre, table, image, hr, blockquote, dt, dd, caption)
  - first_on_page and first_in_chapter flags
  - heading_size_px (when either block is a heading)
  - device_gap_ink, engine_gap_ink, delta_ink
  - device_gap_base, engine_gap_base, delta_base
Writes:
  - tools/reports/rhythm/gaps_<corpus>.json
  - tools/reports/rhythm/coverage.json
  - tools/reports/rhythm/coverage.md
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kindle_render import Family, load_epub
from kindle_render.page import layout_blocks_to_ir
from kindle_render.raster import Rasterizer
from tools.corpus import (
    detect_line_bands,
    load_captures_from_zip,
    make_config,
    resolve_corpus_file,
)


def classify_block_kind(b_meta, raw_block=None) -> str:
    if b_meta.heading_level > 0:
        return f"h{b_meta.heading_level}"
    if b_meta.list_level > 0 or b_meta.list_marker:
        return "li"
    if b_meta.kind in ("pre", "table", "image", "hr"):
        return b_meta.kind
    if raw_block is not None:
        if getattr(raw_block, "is_dt", False):
            return "dt"
        if getattr(raw_block, "is_dd", False):
            return "dd"
        if getattr(raw_block, "blockquote_level", 0) > 0:
            return "blockquote"
    return "paragraph"


def measure_corpus_rhythm(cname: str, cprof: dict, search_paths: List[str]) -> Optional[dict]:
    try:
        ep_p = resolve_corpus_file(cprof["epub"], search_paths)
        cz_p = resolve_corpus_file(cprof["captures_zip"], search_paths)
    except FileNotFoundError as e:
        print(f"[rhythm] Skipping {cname}: {e}")
        return None

    cfg = make_config(cprof["config"])
    geom_label = f"{int(round(cfg.size26 / 64.0))}px_pitch{cfg.pitch}"
    fam = Family(cfg)
    raw_blocks = load_epub(str(ep_p), cfg)
    raw_by_idx = {i: b for i, b in enumerate(raw_blocks)}

    max_p = cprof.get("max_pages", 100)
    doc = layout_blocks_to_ir(raw_blocks, cfg, fam, max_pages=max_p)
    rast = Rasterizer(cfg)
    imgs = rast.rasterize_document(doc)
    rast.close()

    caps = load_captures_from_zip(
        cz_p,
        cprof.get("ignore_captures", []),
        cprof.get("valid_capture_ranges", cprof.get("capture_page_ranges", [])),
    )

    records = []
    page_top_records = []
    prev_ch = None

    for pno, page_ir in enumerate(doc.pages, start=1):
        first_in_ch = (page_ir.chapter != prev_ch)
        prev_ch = page_ir.chapter
        if pno not in caps:
            continue

        R = np.asarray(caps[pno], dtype=np.uint8)
        O = np.asarray(imgs[pno - 1].convert("L"), dtype=np.uint8)
        cap_bands = detect_line_bands(R, 83, 2240)
        ren_bands = detect_line_bands(O, 83, 2240)

        # Map each rendered band (ry0, ry1) to its IR block_idx, baseline, and font size
        b_meta_map = {bm.block_idx: bm for bm in page_ir.blocks}
        ren_band_info = []
        for ry0, ry1 in ren_bands:
            # Find glyphs or commands overlapping vertically with [ry0, ry1]
            overlapping_glyphs = [
                cmd for cmd in page_ir.commands
                if getattr(cmd, "kind", "") == "glyph"
                and cmd.bbox[3] >= ry0 and cmd.bbox[1] <= ry1
            ]
            if overlapping_glyphs:
                b_idx = overlapping_glyphs[0].block_idx
                base_y = int(round(float(np.median([g.baseline for g in overlapping_glyphs]))))
                sz_px = round(max(g.size26 for g in overlapping_glyphs) / 64.0, 2)
                bm = b_meta_map.get(b_idx)
                b_kind = classify_block_kind(bm, raw_by_idx.get(b_idx)) if bm else "paragraph"
            else:
                b_idx = -1
                base_y = ry1
                sz_px = round(cfg.size26 / 64.0, 2)
                b_kind = "other"

            # Match rendered band to device capture band by exact pixel slice equality
            bh = ry1 - ry0 + 1
            ren_slice = O[ry0:ry1 + 1, :]
            dev_match = None
            for cy0, cy1 in cap_bands:
                if (cy1 - cy0 + 1) == bh and np.array_equal(ren_slice, R[cy0:cy1 + 1, :]):
                    dev_match = (cy0, cy1)
                    break
            ren_band_info.append({
                "ren_y0": ry0,
                "ren_y1": ry1,
                "dev_match": dev_match,
                "block_idx": b_idx,
                "block_kind": b_kind,
                "baseline": base_y,
                "size_px": sz_px,
            })

        if ren_band_info and ren_band_info[0]["dev_match"] is not None:
            b0 = ren_band_info[0]
            dy0, dy1 = b0["dev_match"]
            page_top_records.append({
                "corpus": cname,
                "geometry": geom_label,
                "page": pno,
                "chapter": page_ir.chapter,
                "first_in_chapter": first_in_ch,
                "first_block_kind": b0["block_kind"],
                "heading_size_px": b0["size_px"] if b0["block_kind"].startswith("h") else None,
                "device_top_ink": dy0,
                "engine_top_ink": b0["ren_y0"],
                "delta_top_ink": b0["ren_y0"] - dy0,
            })

        for i in range(len(ren_band_info) - 1):
            cur_b = ren_band_info[i]
            nxt_b = ren_band_info[i + 1]
            if cur_b["dev_match"] is None or nxt_b["dev_match"] is None:
                continue
            if cur_b["block_idx"] == nxt_b["block_idx"] and not cur_b["block_kind"].startswith("h"):
                # Same body paragraph line-to-line pitch
                continue
            d_cur_y0, d_cur_y1 = cur_b["dev_match"]
            d_nxt_y0, d_nxt_y1 = nxt_b["dev_match"]
            dev_gap_ink = d_nxt_y0 - d_cur_y1
            eng_gap_ink = nxt_b["ren_y0"] - cur_b["ren_y1"]
            eng_gap_base = nxt_b["baseline"] - cur_b["baseline"]
            dev_gap_base = eng_gap_base + (dev_gap_ink - eng_gap_ink)
            delta_ink = int(eng_gap_ink - dev_gap_ink)
            delta_base = int(eng_gap_base - dev_gap_base)
            is_unaligned = (abs(delta_ink) > cfg.pitch) or (abs(delta_base) > cfg.pitch) or (d_nxt_y0 <= d_cur_y0)
            records.append({
                "corpus": cname,
                "geometry": geom_label,
                "page": pno,
                "chapter": page_ir.chapter,
                "first_on_page": (i == 0),
                "first_in_chapter": (i == 0 and first_in_ch),
                "prev_kind": cur_b["block_kind"],
                "next_kind": nxt_b["block_kind"],
                "same_block": (cur_b["block_idx"] == nxt_b["block_idx"]),
                "heading_size_px": cur_b["size_px"] if cur_b["block_kind"].startswith("h") else (nxt_b["size_px"] if nxt_b["block_kind"].startswith("h") else None),
                "device_gap_ink": int(dev_gap_ink),
                "engine_gap_ink": int(eng_gap_ink),
                "delta_ink": delta_ink,
                "device_gap_base": int(dev_gap_base),
                "engine_gap_base": int(eng_gap_base),
                "delta_base": delta_base,
                "status": "unaligned" if is_unaligned else "aligned",
            })

    aligned_recs = [r for r in records if r["status"] == "aligned"]
    unaligned_recs = [r for r in records if r["status"] == "unaligned"]
    return {
        "corpus": cname,
        "geometry": geom_label,
        "boundary_count": len(records),
        "aligned_boundary_count": len(aligned_recs),
        "unaligned_boundary_count": len(unaligned_recs),
        "mean_delta_ink": round(float(np.mean([r["delta_ink"] for r in aligned_recs])), 4) if aligned_recs else 0.0,
        "exact_boundary_count": sum(1 for r in aligned_recs if r["delta_ink"] == 0),
        "within_1px_boundary_count": sum(1 for r in aligned_recs if abs(r["delta_ink"]) <= 1),
        "page_top_count": len(page_top_records),
        "page_tops": page_top_records,
        "boundaries": records,
    }


def main():
    ap = argparse.ArgumentParser(description="Vertical-rhythm block-boundary measurement harness.")
    ap.add_argument("--only", type=str, default=None, help="Run only a single corpus")
    args = ap.parse_args()

    with open(REPO_ROOT / "tools" / "profiles.json", "r") as pf:
        pdata = json.load(pf)

    out_dir = REPO_ROOT / "tools" / "reports" / "rhythm"
    out_dir.mkdir(parents=True, exist_ok=True)

    corpora = [args.only] if args.only else list(pdata["corpora"].keys())
    coverage: Dict[str, Dict[str, int]] = {}

    for cname in corpora:
        if cname not in pdata["corpora"]:
            continue
        res = measure_corpus_rhythm(cname, pdata["corpora"][cname], pdata["search_paths"])
        if res is None:
            continue
        out_p = out_dir / f"gaps_{cname}.json"
        with open(out_p, "w") as f:
            json.dump(res, f, indent=2)
        geom = res["geometry"]
        for rec in res["boundaries"]:
            if rec.get("status") != "aligned":
                continue
            pair_k = f"{rec['prev_kind']} -> {rec['next_kind']}" + (" (same)" if rec["same_block"] else "")
            coverage.setdefault(pair_k, {})
            coverage[pair_k][geom] = coverage[pair_k].get(geom, 0) + 1
        print(f"[rhythm:{cname}] geometry={geom} aligned={res['aligned_boundary_count']} unaligned={res['unaligned_boundary_count']} exact={res['exact_boundary_count']}/{res['aligned_boundary_count']} page_tops={res['page_top_count']}")

    # Aggregate coverage across all existing gaps_<corpus>.json files
    all_geoms = ["34px_pitch51", "42px_pitch57", "45px_pitch68"]
    coverage = {}
    base_summary = {}
    for gfile in sorted(out_dir.glob("gaps_*.json")):
        with open(gfile) as gf:
            gdata = json.load(gf)
        cn = gdata["corpus"]
        gm = gdata["geometry"]
        base_summary[cn] = {
            "geometry": gm,
            "boundary_count": gdata["boundary_count"],
            "aligned_boundary_count": gdata["aligned_boundary_count"],
            "unaligned_boundary_count": gdata["unaligned_boundary_count"],
            "exact_boundary_count": gdata["exact_boundary_count"],
            "within_1px_boundary_count": gdata["within_1px_boundary_count"],
            "mean_delta_ink": gdata["mean_delta_ink"],
            "page_top_count": gdata["page_top_count"],
        }
        for rec in gdata["boundaries"]:
            if rec.get("status") != "aligned":
                continue
            pair_k = f"{rec['prev_kind']} -> {rec['next_kind']}" + (" (same)" if rec["same_block"] else "")
            coverage.setdefault(pair_k, {g: 0 for g in all_geoms})
            coverage[pair_k][gm] = coverage[pair_k].get(gm, 0) + 1

    cov_report = {}
    md_lines = [
        "# Vertical Rhythm Boundary Coverage Across Geometries",
        "",
        "| Boundary Pair | 34px_pitch51 | 42px_pitch57 | 45px_pitch68 |",
        "|---|---|---|---|",
    ]
    for pair_k, gmap in sorted(coverage.items()):
        cov_report[pair_k] = {}
        row_cells = [pair_k]
        for g in all_geoms:
            cnt = gmap.get(g, 0)
            st = "ok" if cnt >= 3 else "insufficient"
            cov_report[pair_k][g] = {"count": cnt, "status": st}
            row_cells.append(f"{cnt} ({st})")
        md_lines.append("| " + " | ".join(row_cells) + " |")

    with open(out_dir / "coverage.json", "w") as f:
        json.dump(cov_report, f, indent=2)
    with open(out_dir / "coverage.md", "w") as f:
        f.write("\n".join(md_lines) + "\n")
    with open(out_dir / "base.json", "w") as f:
        json.dump(base_summary, f, indent=2)


if __name__ == "__main__":
    main()
