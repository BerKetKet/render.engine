#!/usr/bin/env python3
"""Per-block vertical residuals on chapter-first pages (or chosen pages).
For every text band on the DEVICE capture, find the identical band (pixel-equal) in OUR render and print
shift = our_top - device_top  (0 = exact; + = we are too low; - = too high; '?' = no identical band, i.e. glyph/line-break difference).
Heading blocks and the gap below them show up as the first rows of a chapter-first page.
Usage: python3 tools/block_residuals.py e3_large [--pages 3 16 31] [--csv out.csv]"""
import argparse, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_all as S
C = S.C
ap = argparse.ArgumentParser(); ap.add_argument("dataset", choices=list(S.DATASETS))
ap.add_argument("--pages", nargs="*", type=int); ap.add_argument("--rows", type=int, default=6); ap.add_argument("--csv")
a = ap.parse_args()
epub, capdir, pat, g = S.DATASETS[a.dataset]
imgs, meta, n = S.render(a.dataset)
chs = meta.get("page_chapters") or []
pages = a.pages or [i for i in range(1, n + 1) if i <= len(chs) and (i == 1 or chs[i - 1] != chs[i - 2])]
out = []
print(f"# {a.dataset} geometry={g}  columns: page chapter | row: device_top h shift  (shift = ours - device)")
for p in pages:
    cap = np.asarray(Image.open(Path(capdir) / pat.format(i=p)).convert("L")); ren = np.asarray(imgs[p - 1].convert("L"))
    bc, br = C.detect_line_bands(cap), C.detect_line_bands(ren)
    cells = []
    for k, (y0, y1) in enumerate(bc[:a.rows]):
        sh = next((c - y0 for c, d in br if d - c == y1 - y0 and np.array_equal(cap[y0:y1 + 1], ren[c:d + 1])), None)
        cells.append(f"{y0}/h{y1 - y0 + 1}/{'?' if sh is None else f'{sh:+d}'}")
        out.append((a.dataset, p, chs[p - 1] if p <= len(chs) else "?", k, y0, y1 - y0 + 1, "" if sh is None else sh))
    print(f"p{p:<3d} {(chs[p-1] if p <= len(chs) else '?')[:14]:14s} | " + "  ".join(cells))
if a.csv:
    import csv; w = csv.writer(open(a.csv, "w")); w.writerow("dataset page chapter row device_top height shift".split()); w.writerows(out)
