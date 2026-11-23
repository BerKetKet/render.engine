#!/usr/bin/env python3
"""Compare ink-row bands (tops, bottoms, left/right ink edges) between device captures and engine renders.

Usage: python3 tools/lab_spacing/bands.py CAPDIR OUTPREFIX [--out-json docs/data/spacing_bands.json]
"""
import argparse, json, os, statistics
from pathlib import Path
import numpy as np
from PIL import Image


def extract_bands(png_path, y0=150, y1=2210, thresh=140):
    arr = np.asarray(Image.open(png_path).convert("L"))
    sub = arr[y0:y1, :]
    ink = (sub < thresh).any(axis=1)
    bands, in_b, s = [], False, 0
    for i, v in enumerate(ink):
        if v and not in_b:
            s = i; in_b = True
        elif not v and in_b:
            b0, b1 = y0 + s, y0 + i - 1
            cols = np.where((arr[b0:b1 + 1, :] < thresh).any(axis=0))[0]
            bands.append((b0, b1, int(cols[0]), int(cols[-1])))
            in_b = False
    if in_b:
        b0, b1 = y0 + s, y1 - 1
        cols = np.where((arr[b0:b1 + 1, :] < thresh).any(axis=0))[0]
        bands.append((b0, b1, int(cols[0]), int(cols[-1])))
    return bands


def compare_page_bands(cap_png, eng_png):
    bc = extract_bands(cap_png)
    be = extract_bands(eng_png)
    n = min(len(bc), len(be))
    dtops = [be[i][0] - bc[i][0] for i in range(n)]
    dbots = [be[i][1] - bc[i][1] for i in range(n)]
    dx0s = [be[i][2] - bc[i][2] for i in range(n)]
    dx1s = [be[i][3] - bc[i][3] for i in range(n)]
    return dict(
        n_cap=len(bc), n_eng=len(be),
        cap=bc, eng=be,
        dtop=dtops, dbot=dbots, dx0=dx0s, dx1=dx1s,
        nonzero_dtop=sum(1 for d in dtops if d != 0),
        nonzero_dx0=sum(1 for d in dx0s if d != 0),
        med_dtop=statistics.median(dtops) if dtops else 0,
        med_dx0=statistics.median(dx0s) if dx0s else 0,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cap")
    ap.add_argument("out_prefix")
    ap.add_argument("--out-json", default="docs/data/spacing_bands.json")
    a = ap.parse_args()

    res = {}
    const_dx0_pages = []
    for th in ("Standard", "Compact", "Large"):
        for var in ("line", "paragraph", "word", "char"):
            for k in range(1, 6):
                for pg in range(2, 6):
                    cap_p = f"{a.cap}/{th}/theme_{th}/{var}_step_{k}_of_5/page_{pg:03d}.png"
                    eng_p = f"{a.out_prefix}_{th}/{th}_{var}{k}/page_{pg:03d}.png"
                    if not (os.path.exists(cap_p) and os.path.exists(eng_p)):
                        continue
                    r = compare_page_bands(cap_p, eng_p)
                    key = f"{th}.{var}{k}.p{pg}"
                    res[key] = {k2: v2 for k2, v2 in r.items() if k2 not in ("cap", "eng")}
                    if r["n_cap"] == r["n_eng"] and r["n_cap"] >= 4 and len(set(r["dx0"])) == 1 and r["dx0"][0] != 0:
                        const_dx0_pages.append((key, r["n_cap"], r["dx0"][0], r["dtop"][:6]))
    os.makedirs(os.path.dirname(a.out_json), exist_ok=True)
    json.dump(res, open(a.out_json, "w"), indent=1)
    print(f"Wrote {a.out_json} ({len(res)} pages)")
    print(f"Pages with constant nonzero dX0 across all bands ({len(const_dx0_pages)}):")
    for item in const_dx0_pages:
        print(" ", item)


if __name__ == "__main__":
    main()
