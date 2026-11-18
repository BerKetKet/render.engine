#!/usr/bin/env python3
"""Score a folder of device captures against kindle_render."""
import argparse, glob, os, sys
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kindle_render.config import Config
from kindle_render.epub import load_epub
from kindle_render.fonts import Family
from kindle_render.page import render_blocks
from tools.corpus import compare_page_to_capture

ap = argparse.ArgumentParser()
ap.add_argument("epub")
ap.add_argument("captures_dir")
ap.add_argument("--size26", type=int, required=True)
ap.add_argument("--pitch",  type=int, required=True)
ap.add_argument("--x0",     type=int, required=True)
ap.add_argument("--right",  type=int, required=True)
ap.add_argument("--top",    type=int, default=168)
ap.add_argument("--bottom", type=int, default=2203)
args = ap.parse_args()

cfg = Config(size26=args.size26, pitch=args.pitch, x0=args.x0, right=args.right,
             top=args.top, page_bottom=args.bottom)
caps = {int(Path(p).stem.split("_")[1]): Image.open(p)
        for p in sorted(glob.glob(os.path.join(args.captures_dir, "page_[0-9][0-9][0-9].png")))}
blocks = load_epub(args.epub, cfg)
pages  = render_blocks(blocks, cfg, Family(cfg), max_pages=max(caps) + 10)

exact = diff = cap_l = pos_l = 0
for pno, cap in sorted(caps.items()):
    if pno > len(pages): break
    r = compare_page_to_capture(pages[pno - 1], cap, 83, 2240)
    exact += int(r["exact_page"]); diff += r["diff_pixels"]
    cap_l += r["capture_lines"];   pos_l += r["pos_exact_lines"]
print(f"rendered={len(pages)} captures={len(caps)} exact={exact}/{len(caps)} "
      f"diff_px={diff:,} pos_lines={pos_l}/{cap_l}")
