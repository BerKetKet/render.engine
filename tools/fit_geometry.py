#!/usr/bin/env python3
"""Find the text size / margins of a capture set whose geometry is unknown (e.g. standard size steps).
Sweeps whole-pixel text sizes and left margins; scores positional-exact lines on body pages. Sizes are sharply
determined (a wrong size gives ~0 matches), so a clear winner is expected. Vertical pitch must be given (measured).
Usage: python3 tools/fit_geometry.py exam/v3/size_02_Bookerly --pitch 59 --px 36 42 [--x0 79 81] [--pages 4 10]"""
import argparse, sys
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_all as S
C = S.C
ap = argparse.ArgumentParser(); ap.add_argument("capdir"); ap.add_argument("--pitch", type=int, required=True)
ap.add_argument("--px", nargs=2, type=int, required=True); ap.add_argument("--x0", nargs=2, type=int, default=[78, 82])
ap.add_argument("--pages", nargs=2, type=int, default=[4, 10]); ap.add_argument("--epub", default=str(S.V3 / "kindle_exam_v3.epub"))
a = ap.parse_args()
res = []
for px in range(a.px[0], a.px[1] + 1):
    for x0 in range(a.x0[0], a.x0[1] + 1):
        cfg = dict(size26=px * 64, x0=x0, right=1080 - x0, pitch=a.pitch, top=168, page_bottom=2203)
        imgs, _ = C.render_corpus_once(Path(a.epub), cfg, a.pages[1] + 1)
        pos = tot = 0
        for p in range(a.pages[0], a.pages[1] + 1):
            r = C.compare_page_to_capture(imgs[p - 1], Image.open(f"{a.capdir}/page_{p:03d}.png").convert("L"))
            pos += r["pos_exact_lines"]; tot += r["capture_lines"]
        res.append((pos, tot, px, x0)); print(f"px={px} x0={x0} pos_exact={pos}/{tot}", flush=True)
res.sort(reverse=True); print("BEST:", res[:3])
