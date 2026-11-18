#!/usr/bin/env python3
"""Corpus runner and golden verification tool for kindle_render.

Supports:
  - Named corpus profiles from tools/profiles.json (probe, exam1, exam2)
  - Window y=83..2240 full-width grayscale ('L') comparison:
      (a) strict pixel equality per page (differing pixel count)
      (b) positional exact lines (capture line bands equal at identical y)
      (c) position-independent lines (capture line band equal anywhere on rendered page)
  - Dynamic per-chapter page range derivation from layout metadata
  - Per-page raw pixel SHA-256 golden comparison and explicit --update-golden
  - Per-page layout IR SHA-256 golden comparison (layout_pages, added in Phase 0.6 / Phase 2.1)
  - Double-render determinism verification (pixel and layout hashes)
  - Synthetic generalization suite verification (tools/golden/synthetic.json)
  - Environment, font, hyphenation, and corpus SHA-256 manifest generation
  - Restartable execution (--only <corpus>, --pages N, --skip-existing)
"""
import argparse
import ctypes
import hashlib
import io
import json
import os
import platform
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import kindle_render
from kindle_render.config import Config
from kindle_render.epub import load_epub
from kindle_render.fonts import Family, get_harfbuzz_info
from PIL import features as pil_features
import PIL
from kindle_render.page import render_blocks
from kindle_render.raster import get_freetype_version
from tools.check_imports import check_imports


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_image(im: Image.Image) -> str:
    arr = np.asarray(im)
    return hashlib.sha256(arr.tobytes()).hexdigest()


def get_git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), stderr=subprocess.DEVNULL
        )
        return out.decode("utf-8").strip()
    except Exception:
        return "unknown"


def resolve_corpus_file(filename: str, search_paths: List[str]) -> Path:
    p = Path(filename)
    if p.is_file():
        return p.resolve()
    for sp in search_paths:
        cand_dir = Path(sp) if os.path.isabs(sp) else (REPO_ROOT / sp)
        cand = cand_dir / filename
        if cand.is_file():
            return cand.resolve()
    raise FileNotFoundError(f"Could not locate corpus file '{filename}' in {search_paths}")


def resolve_corpus_dir(dirname: str, search_paths: List[str]) -> Path:
    p = Path(dirname)
    if p.is_dir():
        return p.resolve()
    for sp in search_paths:
        cand_dir = Path(sp) if os.path.isabs(sp) else (REPO_ROOT / sp)
        cand = cand_dir / dirname
        if cand.is_dir():
            return cand.resolve()
    raise FileNotFoundError(f"Could not locate corpus directory '{dirname}' in {search_paths}")


def build_manifest(profiles_data: dict, selected_corpora: List[str], epub_overrides: Dict[str, str], allow_unshaped: bool = False) -> dict:
    pkg_dir = REPO_ROOT / "kindle_render"
    fonts_dir = pkg_dir / "fonts"
    font_hashes = {}
    if fonts_dir.is_dir():
        for fn in sorted(os.listdir(fonts_dir)):
            fp = fonts_dir / fn
            if fp.is_file():
                font_hashes[f"kindle_render/fonts/{fn}"] = sha256_file(fp)

    hyph_hashes = {}
    for fn in sorted(os.listdir(pkg_dir)):
        if fn.startswith("hyph_") and (fn.endswith(".dic") or fn.endswith(".bin")):
            fp = pkg_dir / fn
            if fp.is_file():
                hyph_hashes[f"kindle_render/{fn}"] = sha256_file(fp)

    corpus_hashes = {}
    search_paths = profiles_data.get("search_paths", [])
    for cname in selected_corpora:
        cprof = profiles_data["corpora"][cname]
        ep_name = epub_overrides.get(cname) or cprof["epub"]
        try:
            ep_p = resolve_corpus_file(ep_name, search_paths)
            corpus_hashes[f"{cname}:epub:{ep_p.name}"] = sha256_file(ep_p)
        except FileNotFoundError:
            corpus_hashes[f"{cname}:epub:{ep_name}"] = "missing"
        if cprof.get("captures_dir"):
            try:
                cd_p = resolve_corpus_dir(cprof["captures_dir"], search_paths)
                corpus_hashes[f"{cname}:captures_dir"] = str(cd_p.relative_to(REPO_ROOT)) if cd_p.is_relative_to(REPO_ROOT) else str(cd_p)
            except FileNotFoundError:
                corpus_hashes[f"{cname}:captures_dir"] = "missing"
        elif cprof.get("captures_zip"):
            try:
                cz_p = resolve_corpus_file(cprof["captures_zip"], search_paths)
                corpus_hashes[f"{cname}:captures:{cz_p.name}"] = sha256_file(cz_p)
            except FileNotFoundError:
                corpus_hashes[f"{cname}:captures:{cprof['captures_zip']}"] = "missing"

    pil_feats = {}
    for k in ["jpg", "zlib", "freetype2", "harfbuzz", "raqm", "fribidi", "webp", "libtiff", "littlecms2", "jpg_2000"]:
        try:
            pil_feats[k] = pil_features.version(k) or str(pil_features.check(k))
        except Exception:
            pil_feats[k] = "none"
    hb_info = get_harfbuzz_info()
    ft_ver = get_freetype_version()
    os_arch = f"{platform.system()}-{platform.release()}-{platform.machine()}"
    fp_payload = {
        "python_version": platform.python_version(),
        "os_arch": os_arch,
        "pillow_version": PIL.__version__,
        "pillow_features": pil_feats,
        "numpy_version": np.__version__,
        "freetype_version": ft_ver,
        "harfbuzz_version": hb_info.get("version"),
        "harfbuzz_path": hb_info.get("path"),
    }
    env_fp = hashlib.sha256(json.dumps(fp_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "engine_version": getattr(kindle_render, "__version__", "unknown"),
        "git_commit": get_git_commit(),
        "python_version": platform.python_version(),
        "os_arch": os_arch,
        "pillow_version": PIL.__version__,
        "pillow_features": pil_feats,
        "numpy_version": np.__version__,
        "freetype_version": ft_ver,
        "harfbuzz": hb_info,
        "allow_unshaped": bool(allow_unshaped),
        "environment_fingerprint": env_fp,
        "fonts_sha256": font_hashes,
        "hyphen_sha256": hyph_hashes,
        "corpus_files_sha256": corpus_hashes,
    }


def detect_line_bands(gray: np.ndarray, y0: int = 83, y1: int = 2240, thresh: int = 250) -> List[Tuple[int, int]]:
    sub = gray[y0:y1, :] < thresh
    row_has_ink = sub.any(axis=1)
    bands_out = []
    in_band = False
    start_y = y0
    for dy, has_ink in enumerate(row_has_ink):
        y = y0 + dy
        if has_ink and not in_band:
            in_band = True
            start_y = y
        elif not has_ink and in_band:
            in_band = False
            bands_out.append((start_y, y - 1))
    if in_band:
        bands_out.append((start_y, y1 - 1))
    return bands_out


def compare_page_to_capture(
    ren_img: Image.Image,
    cap_img: Image.Image,
    y0: int = 83,
    y1: int = 2240,
) -> dict:
    O = np.asarray(ren_img.convert("L"), dtype=np.uint8)
    R = np.asarray(cap_img.convert("L"), dtype=np.uint8)

    O_win = O[y0:y1, :]
    R_win = R[y0:y1, :]
    diff_pixels = int(np.sum(R_win != O_win))
    exact_page = (diff_pixels == 0)

    cap_bands = detect_line_bands(R, y0, y1)
    ren_bands = detect_line_bands(O, y0, y1)

    pos_exact = 0
    for by0, by1 in cap_bands:
        if np.array_equal(R[by0:by1 + 1, :], O[by0:by1 + 1, :]):
            pos_exact += 1

    used_ren = set()
    pos_indep = 0
    for by0, by1 in cap_bands:
        bh = by1 - by0 + 1
        cap_slice = R[by0:by1 + 1, :]
        matched = False
        # First check detected bands on rendered page
        for ri, (ry0, ry1) in enumerate(ren_bands):
            if ri not in used_ren and (ry1 - ry0 + 1) == bh:
                if np.array_equal(cap_slice, O[ry0:ry1 + 1, :]):
                    used_ren.add(ri)
                    pos_indep += 1
                    matched = True
                    break
        if not matched:
            # Also check if identical slice exists at same y (e.g. when render band merged)
            if np.array_equal(cap_slice, O[by0:by1 + 1, :]):
                pos_indep += 1

    win_px = int(O_win.size)
    match_pct = 100.0 * (1.0 - diff_pixels / win_px) if win_px > 0 else 100.0
    o_ink = O_win < 128
    r_ink = R_win < 128
    inter = int(np.sum(o_ink & r_ink))
    union = int(np.sum(o_ink | r_ink))
    ink_iou = (inter / union) if union > 0 else 1.0

    return {
        "exact_page": exact_page,
        "diff_pixels": diff_pixels,
        "match_pct": match_pct,
        "ink_iou": ink_iou,
        "capture_lines": len(cap_bands),
        "render_lines": len(ren_bands),
        "pos_exact_lines": pos_exact,
        "pos_indep_lines": pos_indep,
        "displaced_lines": pos_indep - pos_exact,
    }


def load_captures_from_dir(
    cap_dir: Path,
    pattern: str,
    ignore_list: List[str],
    valid_ranges: List[List[int]],
    max_pages: int = 200,
) -> Dict[int, Image.Image]:
    valid_pages = set()
    for r0, r1 in valid_ranges:
        for p in range(r0, r1 + 1):
            valid_pages.add(p)

    captures = {}
    ignore_set = set(ignore_list)
    limit = max(valid_pages) if valid_pages else max_pages
    for pno in range(1, limit + 1):
        if valid_pages and pno not in valid_pages:
            continue
        bn = pattern.format(i=pno)
        if bn in ignore_set or "_table_" in bn:
            continue
        fp = cap_dir / bn
        if fp.is_file():
            captures[pno] = Image.open(fp).convert("L")
    return captures


def load_captures_from_zip(zip_path: Path, ignore_list: List[str], valid_ranges: List[List[int]]) -> Dict[int, Image.Image]:
    valid_pages = set()
    for r0, r1 in valid_ranges:
        for p in range(r0, r1 + 1):
            valid_pages.add(p)

    captures = {}
    ignore_set = set(ignore_list)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            bn = os.path.basename(name)
            if not bn.endswith(".png") or bn in ignore_set:
                continue
            nums = [int(s) for s in re.findall(r"\d+", bn)]
            if not nums:
                continue
            pno = nums[-1]
            if valid_pages and pno not in valid_pages:
                continue
            captures[pno] = Image.open(io.BytesIO(zf.read(name))).convert("L")
    return captures


def make_config(prof_cfg: dict) -> Config:
    cfg = Config()
    for k, v in prof_cfg.items():
        setattr(cfg, k, v)
    cfg.pitch_ratio = cfg.pitch / (cfg.size26 / 64.0)
    return cfg


def render_corpus_once(epub_path: Path, prof_cfg: dict, max_pages: int) -> Tuple[List[Image.Image], dict]:
    cfg = make_config(prof_cfg)
    fam = Family(cfg)
    blocks = load_epub(str(epub_path), cfg)
    imgs, meta = render_blocks(blocks, cfg, fam, max_pages=max_pages, return_meta=True)
    return imgs, meta


def format_chapter_table(cname: str, summary: dict) -> str:
    lines = []
    lines.append(f"=== Corpus: {cname} (rendered={summary['rendered_pages']}, compared={summary['compared_pages']}) ===")
    lines.append(
        f"{'Chapter':22s} | {'Pages':9s} | {'ExactPg':8s} | {'DiffPx':10s} | {'PosLines':11s} | {'PILines':11s}"
    )
    lines.append("-" * 84)
    for ch in summary["chapters"]:
        p_rng = f"{ch['start_page']}-{ch['end_page']}" if ch["start_page"] != ch["end_page"] else f"{ch['start_page']}"
        ex_s = f"{ch['exact_pages']}/{ch['compared_pages']}"
        pl_s = f"{ch['pos_exact_lines']}/{ch['capture_lines']}"
        pi_s = f"{ch['pos_indep_lines']}/{ch['capture_lines']}"
        lines.append(
            f"{ch['chapter']:22s} | {p_rng:9s} | {ex_s:8s} | {ch['diff_pixels']:10,d} | {pl_s:11s} | {pi_s:11s}"
        )
    lines.append("-" * 84)
    t = summary["totals"]
    ex_t = f"{t['exact_pages']}/{summary['compared_pages']}"
    pl_t = f"{t['pos_exact_lines']}/{t['capture_lines']}"
    pi_t = f"{t['pos_indep_lines']}/{t['capture_lines']}"
    lines.append(
        f"{'TOTAL':22s} | {'all':9s} | {ex_t:8s} | {t['diff_pixels']:10,d} | {pl_t:11s} | {pi_t:11s}"
    )
    return "\n".join(lines)


def run_single_corpus(
    cname: str,
    cprof: dict,
    search_paths: List[str],
    pages_limit: Optional[int],
    update_golden: bool,
    check_golden: bool,
    check_determinism: bool,
    epub_override: Optional[str] = None,
    out_dir: Optional[Path] = None,
    golden_only: bool = False,
) -> Tuple[dict, bool]:
    ep_name = epub_override or cprof["epub"]
    epub_path = resolve_corpus_file(ep_name, search_paths)

    max_p = pages_limit if pages_limit is not None else cprof.get("max_pages", 100)
    imgs, meta = render_corpus_once(epub_path, cprof["config"], max_p)
    page_hashes = [sha256_image(im) for im in imgs]
    layout_hashes = meta.get("layout_hashes", [])

    deterministic = True
    if check_determinism:
        imgs2, meta2 = render_corpus_once(epub_path, cprof["config"], max_p)
        page_hashes2 = [sha256_image(im) for im in imgs2]
        layout_hashes2 = meta2.get("layout_hashes", [])
        deterministic = (page_hashes == page_hashes2) and (layout_hashes == layout_hashes2)

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        for idx, im in enumerate(imgs, start=1):
            im.save(out_dir / f"page_{idx:03d}.png")

    captures = {}
    cap_source = "none"
    if not golden_only and cprof.get("captures_dir"):
        try:
            cap_dir = resolve_corpus_dir(cprof["captures_dir"], search_paths)
            captures = load_captures_from_dir(
                cap_dir,
                cprof.get("capture_pattern", "page_{i:03d}.png"),
                cprof.get("ignore_captures", []),
                cprof.get("capture_page_ranges", []),
                max_pages=max_p,
            )
            cap_source = str(cap_dir.name)
        except FileNotFoundError:
            pass
    if not golden_only and not captures and cprof.get("captures_zip"):
        try:
            cap_zip_path = resolve_corpus_file(cprof["captures_zip"], search_paths)
            captures = load_captures_from_zip(
                cap_zip_path,
                cprof.get("ignore_captures", []),
                cprof.get("capture_page_ranges", []),
            )
            cap_source = str(cap_zip_path.name)
        except FileNotFoundError:
            pass
    y0, y1 = cprof.get("window_y", [83, 2240])

    page_chapters = meta.get("page_chapters", [])
    while len(page_chapters) < len(imgs):
        page_chapters.append("unknown")

    per_page = {}
    for pno in range(1, len(imgs) + 1):
        ch_id = page_chapters[pno - 1] or "unknown"
        entry = {
            "page": pno,
            "chapter": ch_id,
            "sha256": page_hashes[pno - 1],
            "has_capture": (pno in captures),
        }
        if pno <= len(layout_hashes):
            entry["layout_sha256"] = layout_hashes[pno - 1]
        if pno in captures:
            cmp_res = compare_page_to_capture(imgs[pno - 1], captures[pno], y0, y1)
            entry.update(cmp_res)
        per_page[pno] = entry

    # Group chapters in spine order derived dynamically from layout
    chapters_order = []
    ch_pages: Dict[str, List[int]] = {}
    for pno in range(1, len(imgs) + 1):
        ch_id = per_page[pno]["chapter"]
        if ch_id not in ch_pages:
            chapters_order.append(ch_id)
            ch_pages[ch_id] = []
        ch_pages[ch_id].append(pno)

    chapters_summary = []
    for ch_id in chapters_order:
        pnos = ch_pages[ch_id]
        cmp_pnos = [p for p in pnos if per_page[p]["has_capture"]]
        chapters_summary.append({
            "chapter": ch_id,
            "start_page": min(pnos),
            "end_page": max(pnos),
            "rendered_pages": len(pnos),
            "compared_pages": len(cmp_pnos),
            "exact_pages": sum(1 for p in cmp_pnos if per_page[p]["exact_page"]),
            "diff_pixels": sum(per_page[p]["diff_pixels"] for p in cmp_pnos),
            "capture_lines": sum(per_page[p]["capture_lines"] for p in cmp_pnos),
            "render_lines": sum(per_page[p]["render_lines"] for p in cmp_pnos),
            "pos_exact_lines": sum(per_page[p]["pos_exact_lines"] for p in cmp_pnos),
            "pos_indep_lines": sum(per_page[p]["pos_indep_lines"] for p in cmp_pnos),
            "displaced_lines": sum(per_page[p]["pos_indep_lines"] - per_page[p]["pos_exact_lines"] for p in cmp_pnos),
        })

    cmp_all = [p for p in per_page.values() if p["has_capture"]]
    totals = {
        "exact_pages": sum(1 for p in cmp_all if p["exact_page"]),
        "diff_pixels": sum(p["diff_pixels"] for p in cmp_all),
        "mean_match_pct": (sum(p["match_pct"] for p in cmp_all) / len(cmp_all)) if cmp_all else None,
        "mean_ink_iou": (sum(p["ink_iou"] for p in cmp_all) / len(cmp_all)) if cmp_all else None,
        "capture_lines": sum(p["capture_lines"] for p in cmp_all),
        "render_lines": sum(p["render_lines"] for p in cmp_all),
        "pos_exact_lines": sum(p["pos_exact_lines"] for p in cmp_all),
        "pos_indep_lines": sum(p["pos_indep_lines"] for p in cmp_all),
        "displaced_lines": sum(p["pos_indep_lines"] - p["pos_exact_lines"] for p in cmp_all),
    }

    golden_path = REPO_ROOT / "tools" / "golden" / f"{cname}.json"
    golden_ok = True
    golden_mismatches = []
    layout_golden_ok = True
    layout_golden_mismatches = []

    if update_golden:
        golden_payload = {
            "corpus": cname,
            "environment_fingerprint": build_manifest({"corpora": {}, "search_paths": []}, [], {})["environment_fingerprint"],
            "engine_version": getattr(kindle_render, "__version__", "unknown"),
            "page_count": len(imgs),
            "pages": {str(i + 1): h for i, h in enumerate(page_hashes)},
            "layout_pages": {str(i + 1): h for i, h in enumerate(layout_hashes)} if layout_hashes else {},
        }
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        with open(golden_path, "w") as gf:
            json.dump(golden_payload, gf, indent=2)
    golden_status = "PASS"
    layout_golden_status = "PASS"
    if not update_golden and not check_golden:
        golden_status = "NO-GOLDEN"
        layout_golden_status = "NO-GOLDEN"
    elif check_golden:
        if not golden_path.is_file():
            golden_ok = False
            layout_golden_ok = False
            golden_status = "NO-GOLDEN"
            layout_golden_status = "NO-GOLDEN"
            golden_mismatches.append("NO-GOLDEN")
        else:
            with open(golden_path, "r") as gf:
                gdata = json.load(gf)
            cur_fp = build_manifest({"corpora": {}, "search_paths": []}, [], {})["environment_fingerprint"]
            g_fp = gdata.get("environment_fingerprint")
            if g_fp and g_fp != cur_fp:
                print(f"[WARNING] {cname}: golden environment_fingerprint ({g_fp[:12]}) != current ({cur_fp[:12]})")
            gpages = gdata.get("pages", {})
            if pages_limit is None and len(imgs) != gdata.get("page_count", len(gpages)):
                golden_ok = False
                golden_mismatches.append(f"page_count:{len(imgs)}!={gdata.get('page_count')}")
            for idx, h in enumerate(page_hashes, start=1):
                gh = gpages.get(str(idx))
                if gh != h:
                    golden_ok = False
                    golden_mismatches.append(f"page_{idx:03d}")

            glayout = gdata.get("layout_pages", {})
            if glayout:
                if pages_limit is None and len(layout_hashes) != len(glayout):
                    layout_golden_ok = False
                    layout_golden_mismatches.append(f"layout_page_count:{len(layout_hashes)}!={len(glayout)}")
                for idx, lh in enumerate(layout_hashes, start=1):
                    glh = glayout.get(str(idx))
                    if glh != lh:
                        layout_golden_ok = False
                        layout_golden_mismatches.append(f"layout_page_{idx:03d}")

    summary = {
        "corpus": cname,
        "epub": str(epub_path.name),
        "captures_zip": cap_source,
        "rendered_pages": len(imgs),
        "compared_pages": len(cmp_all),
        "deterministic": deterministic,
        "golden_passed": (golden_status if golden_status == "NO-GOLDEN" else golden_ok),
        "golden_mismatches": golden_mismatches,
        "layout_golden_passed": (layout_golden_status if layout_golden_status == "NO-GOLDEN" else layout_golden_ok),
        "layout_golden_mismatches": layout_golden_mismatches,
        "chapter_errors": meta.get("chapter_errors", []),
        "totals": totals,
        "chapters": chapters_summary,
        "pages": {str(k): v for k, v in per_page.items()},
    }
    return summary, (deterministic and golden_ok and layout_golden_ok)


def run_synthetic_suite(prof_cfg: dict, update_golden: bool, check_golden: bool, check_determinism: bool) -> Tuple[dict, bool]:
    syn_epub = REPO_ROOT / "tools" / "reports" / "synthetic" / "synthetic_generalization.epub"
    if not syn_epub.is_file():
        return {"present": False, "passed": True}, True

    imgs, meta = render_corpus_once(syn_epub, prof_cfg, 100)
    page_hashes = [sha256_image(im) for im in imgs]
    layout_hashes = meta.get("layout_hashes", [])

    deterministic = True
    if check_determinism:
        imgs2, meta2 = render_corpus_once(syn_epub, prof_cfg, 100)
        page_hashes2 = [sha256_image(im) for im in imgs2]
        layout_hashes2 = meta2.get("layout_hashes", [])
        deterministic = (page_hashes == page_hashes2) and (layout_hashes == layout_hashes2)

    golden_path = REPO_ROOT / "tools" / "golden" / "synthetic.json"
    golden_ok = True
    layout_golden_ok = True
    mismatches = []

    if update_golden:
        golden_payload = {
            "corpus": "synthetic",
            "engine_version": getattr(kindle_render, "__version__", "unknown"),
            "page_count": len(imgs),
            "pages": {str(i + 1): h for i, h in enumerate(page_hashes)},
            "layout_pages": {str(i + 1): h for i, h in enumerate(layout_hashes)} if layout_hashes else {},
        }
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        with open(golden_path, "w") as gf:
            json.dump(golden_payload, gf, indent=2)
    elif check_golden and golden_path.is_file():
        with open(golden_path, "r") as gf:
            gdata = json.load(gf)
        gpages = gdata.get("pages", {})
        if len(imgs) != gdata.get("page_count", len(gpages)):
            golden_ok = False
            mismatches.append(f"page_count:{len(imgs)}!={gdata.get('page_count')}")
        for idx, h in enumerate(page_hashes, start=1):
            if gpages.get(str(idx)) != h:
                golden_ok = False
                mismatches.append(f"page_{idx:02d}")
        glayout = gdata.get("layout_pages", {})
        if glayout:
            if len(layout_hashes) != len(glayout):
                layout_golden_ok = False
                mismatches.append(f"layout_page_count:{len(layout_hashes)}!={len(glayout)}")
            for idx, lh in enumerate(layout_hashes, start=1):
                if glayout.get(str(idx)) != lh:
                    layout_golden_ok = False
                    mismatches.append(f"layout_page_{idx:02d}")

    passed = deterministic and golden_ok and layout_golden_ok
    return {
        "present": True,
        "rendered_pages": len(imgs),
        "deterministic": deterministic,
        "golden_passed": golden_ok,
        "layout_golden_passed": layout_golden_ok,
        "mismatches": mismatches,
        "passed": passed,
    }, passed


def main():
    ap = argparse.ArgumentParser(description="Corpus runner and golden verifier for kindle_render.")
    ap.add_argument("--only", type=str, default=None, help="Run only a single corpus (key in tools/profiles.json or synthetic)")
    ap.add_argument("--write-manifest", action="store_true", help="Explicitly overwrite tracked tools/reports/manifest.json")
    ap.add_argument("--golden-only", action="store_true", help="Skip capture comparison; verify determinism and golden hashes only")
    ap.add_argument("--allow-unshaped", action="store_true", help="Debug flag: allow fallback shaper if HarfBuzz is unavailable")
    ap.add_argument("--pages", type=int, default=None, help="Render at most N pages")
    ap.add_argument("--update-golden", action="store_true", help="Explicitly write tools/golden/<corpus>.json")
    ap.add_argument("--no-golden", action="store_true", help="Skip golden comparison (for pre-golden runs)")
    ap.add_argument("--no-determinism", action="store_true", help="Skip second-render determinism check")
    ap.add_argument("--skip-existing", action="store_true", help="Skip corpus if report JSON already exists")
    ap.add_argument("--epub", type=str, default=None, help="Override EPUB path (with --only)")
    ap.add_argument("--out-dir", type=str, default=None, help="Optional directory to save rendered PNGs")
    ap.add_argument("--report-json", type=str, default=None, help="Path to write combined JSON report")
    ap.add_argument("--report-md", type=str, default=None, help="Path to write compact Markdown report")
    args = ap.parse_args()

    imp_ok, imp_errs, _ = check_imports()
    if not imp_ok:
        for e in imp_errs:
            print(f"[G4 ERROR] {e}")
        sys.exit(1)
    print("[G4 import-graph] passed=True")

    profiles_path = REPO_ROOT / "tools" / "profiles.json"
    with open(profiles_path, "r") as pf:
        profiles_data = json.load(pf)

    if args.only == "synthetic":
        syn_res, syn_ok = run_synthetic_suite(
            profiles_data["corpora"]["exam2"]["config"],
            update_golden=args.update_golden,
            check_golden=(not args.no_golden and not args.update_golden),
            check_determinism=(not args.no_determinism),
        )
        print(
            f"[synthetic] deterministic={syn_res.get('deterministic')} "
            f"golden_passed={syn_res.get('golden_passed')} "
            f"layout_golden_passed={syn_res.get('layout_golden_passed')} "
            f"pages={syn_res.get('rendered_pages')}"
        )
        if not syn_ok:
            sys.exit(1)
        return

    selected = [args.only] if args.only else ["probe", "exam1", "exam2"]
    epub_overrides = {args.only: args.epub} if (args.only and args.epub) else {}

    manifest = build_manifest(profiles_data, selected, epub_overrides, allow_unshaped=getattr(args, "allow_unshaped", False))
    reports_dir = REPO_ROOT / "tools" / "reports_local"
    reports_dir.mkdir(parents=True, exist_ok=True)
    with open(reports_dir / "manifest.json", "w") as mf:
        json.dump(manifest, mf, indent=2)
    if args.write_manifest:
        tracked_reports = REPO_ROOT / "tools" / "reports"
        tracked_reports.mkdir(parents=True, exist_ok=True)
        with open(tracked_reports / "manifest.json", "w") as mf:
            json.dump(manifest, mf, indent=2)

    all_passed = True
    corpus_results = {}
    md_sections = [
        f"# Corpus Baseline Report (`kindle_render` v{manifest['engine_version']})",
        f"- **Git Commit**: `{manifest['git_commit']}`",
        f"- **Python**: `{manifest['python_version']}` | **FreeType**: `{manifest['freetype_version']}`",
        "",
    ]

    for cname in selected:
        per_corpus_json = reports_dir / f"{cname}_report.json"
        if args.skip_existing and per_corpus_json.is_file() and not args.update_golden:
            with open(per_corpus_json, "r") as rf:
                res = json.load(rf)
            corpus_results[cname] = res
            tbl_txt = format_chapter_table(cname, res)
            print(tbl_txt)
            md_sections.append(f"## Corpus: `{cname}`")
            md_sections.append("```text")
            md_sections.append(tbl_txt)
            md_sections.append("```")
            md_sections.append("")
            continue

        c_out_dir = Path(args.out_dir) / cname if args.out_dir else None
        res, ok = run_single_corpus(
            cname=cname,
            cprof=profiles_data["corpora"][cname],
            search_paths=profiles_data["search_paths"],
            pages_limit=args.pages,
            update_golden=args.update_golden,
            check_golden=(not args.no_golden and not args.update_golden),
            check_determinism=(not args.no_determinism),
            epub_override=epub_overrides.get(cname),
            out_dir=c_out_dir,
            golden_only=args.golden_only,
        )
        with open(per_corpus_json, "w") as rf:
            json.dump(res, rf, indent=2)

        corpus_results[cname] = res
        tbl_txt = format_chapter_table(cname, res)
        print(tbl_txt)
        print(
            f"[{cname}] deterministic={res['deterministic']} golden_passed={res['golden_passed']} "
            f"layout_golden_passed={res.get('layout_golden_passed', True)} "
            f"exact_pages={res['totals']['exact_pages']}/{res['compared_pages']} "
            f"pos_lines={res['totals']['pos_exact_lines']}/{res['totals']['capture_lines']} "
            f"pi_lines={res['totals']['pos_indep_lines']}/{res['totals']['capture_lines']} "
            f"displaced_lines={res['totals']['displaced_lines']}\n"
        )
        md_sections.append(f"## Corpus: `{cname}`")
        md_sections.append("```text")
        md_sections.append(tbl_txt)
        md_sections.append("```")
        md_sections.append("")
        if not ok:
            all_passed = False

    if not args.only and args.pages is None:
        syn_res, syn_ok = run_synthetic_suite(
            profiles_data["corpora"]["exam2"]["config"],
            update_golden=args.update_golden,
            check_golden=(not args.no_golden and not args.update_golden),
            check_determinism=(not args.no_determinism),
        )
        print(
            f"[synthetic] deterministic={syn_res.get('deterministic')} "
            f"golden_passed={syn_res.get('golden_passed')} "
            f"layout_golden_passed={syn_res.get('layout_golden_passed')} "
            f"pages={syn_res.get('rendered_pages')}"
        )
        if not syn_ok:
            all_passed = False

    combined = {
        "manifest": manifest,
        "corpora": corpus_results,
    }
    if args.report_json:
        rp_j = Path(args.report_json)
        rp_j.parent.mkdir(parents=True, exist_ok=True)
        with open(rp_j, "w") as jf:
            json.dump(combined, jf, indent=2)

    if args.report_md:
        rp_m = Path(args.report_md)
        rp_m.parent.mkdir(parents=True, exist_ok=True)
        with open(rp_m, "w") as mf:
            mf.write("\n".join(md_sections))

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
