#!/usr/bin/env python3
"""Score the current checkout against every device-capture set available in exam/.
Usage: python3 tools/score_all.py [--only NAME ...] [--out results.json]
Prints one summary line per dataset and writes per-page rows to --out (JSON).
Run with the SAME environment (HarfBuzz 6.0.0) before and after a change, then use tools/ab_diff.py."""
import argparse, json, os, sys
from pathlib import Path
from PIL import Image
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))
import corpus as C

X = REPO / "exam"
V3, TI = X / "v3", X / "tables_images_exam"
STD = dict(size26=2880, x0=79, right=1001, pitch=68)
CMP = dict(size26=2496, x0=39, right=1041, pitch=53)
LRG = dict(size26=3200, x0=131, right=949, pitch=82)
# name: (epub, capture dir, filename pattern, geometry)
DATASETS = {
    "exam1":      (X/"v1/kindle_exam_v1.epub", X/"v1/exam_v1_screenshots", "exam_screen_{i}.png", STD),
    "exam2":      (X/"v2/kindle_exam_v2.epub", X/"v2/exam_v2_screenshots", "exam_screen_{i}.png", dict(size26=2688, x0=79, right=1001, pitch=57)),
    "e3_std":     (V3/"kindle_exam_v3.epub", V3/"size_04_Bookerly", "page_{i:03d}.png", STD),
    "e3_small":   (V3/"kindle_exam_v3.epub", V3/"size_00_Bookerly", "page_{i:03d}.png", dict(size26=2176, x0=79, right=1001, pitch=51)),
    "e3_compact": (V3/"kindle_exam_v3.epub", V3/"theme_Compact", "page_{i:03d}.png", CMP),
    "e3_large":   (V3/"kindle_exam_v3.epub", V3/"theme_Large", "page_{i:03d}.png", LRG),
    "ti_std":     (TI/"kindle_tables_images_exam.epub", TI/"theme_Standard", "page_{i:03d}.png", STD),
    "ti_compact": (TI/"kindle_tables_images_exam.epub", TI/"theme_Compact", "page_{i:03d}.png", CMP),
    "ti_large":   (TI/"kindle_tables_images_exam.epub", TI/"theme_Large", "page_{i:03d}.png", LRG),
}

def count_caps(capdir, pat):
    n = 0
    while (Path(capdir) / pat.format(i=n + 1)).exists(): n += 1
    return n

def render(name, max_pages=None):
    epub, capdir, pat, g = DATASETS[name]
    n = count_caps(capdir, pat)
    cfg = dict(g, top=168, page_bottom=2203)
    imgs, meta = C.render_corpus_once(Path(epub), cfg, (max_pages or n) + 5)
    return imgs, meta, n

def score(name):
    epub, capdir, pat, g = DATASETS[name]
    imgs, meta, n = render(name)
    chs = meta.get("page_chapters") or []
    rows = []
    for i in range(1, n + 1):
        if i > len(imgs): rows.append(dict(p=i, missing=True)); continue
        r = C.compare_page_to_capture(imgs[i - 1], Image.open(Path(capdir) / pat.format(i=i)).convert("L"))
        rows.append(dict(p=i, exact=int(r["exact_page"]), diff=int(r["diff_pixels"]), lines=r["capture_lines"],
                         render_lines=r["render_lines"], pos=r["pos_exact_lines"], pi=r["pos_indep_lines"],
                         ch=chs[i - 1] if i <= len(chs) else "?"))
    return dict(name=name, ncap=n, nren=len(imgs), rows=rows)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=list(DATASETS)); ap.add_argument("--out", default="score_all.json")
    a = ap.parse_args()
    out = {}
    for name in a.only:            # sequential on purpose: parallel full-book renders can exhaust memory
        res = score(name); out[name] = res
        ok = [r for r in res["rows"] if not r.get("missing")]
        print(f"{name:11s} caps={res['ncap']:>3} rendered={res['nren']:>3} exact={sum(r['exact'] for r in ok):>3} "
              f"diff_px={sum(r['diff'] for r in ok):>10,} pos_lines={sum(r['pos'] for r in ok)}/{sum(r['lines'] for r in ok)}", flush=True)
        json.dump(out, open(a.out, "w"))
