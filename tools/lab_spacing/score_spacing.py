#!/usr/bin/env python3
"""Score the engine against the spacing-setting device captures.

usage: python tools/lab_spacing/score_spacing.py CAPDIR EPUB OUTDIR [--vars line,paragraph,word,char] [--themes Standard,Compact,Large] [--steps 1,2,3,4,5] [-- extra render args]
CAPDIR holds <Theme>/theme_<Theme>/<var>_step_<k>_of_5/page_00{1..5}.png (the user's three zips, unpacked side by side).
EPUB is the exam2 book (kindle_exam_v2.epub). Page 1 (title) is ignored in totals.
All non-varied settings are rendered at step 1 (incl. --line-spacing-step 1), as captured.
Prints per-page diff pixels (compare()['diff_pixel_count']) and the sum of pages 2-5.
"""
import sys, os, subprocess, json, argparse
sys.path.insert(0, os.getcwd())
from kindle_render.compare import compare
ap = argparse.ArgumentParser()
ap.add_argument("cap"); ap.add_argument("epub"); ap.add_argument("out")
ap.add_argument("--vars", default="line,paragraph,word,char")
ap.add_argument("--themes", default="Standard,Compact,Large")
ap.add_argument("--steps", default="1,2,3,4,5")
a, extra = ap.parse_known_args()
extra = [x for x in extra if x != "--"]
GEO = {"Standard": (2880, 79, 1001), "Compact": (2496, 39, 1041), "Large": (3200, 131, 949)}
res = {}
for th in a.themes.split(","):
    s26, x0, right = GEO[th]
    for var in a.vars.split(","):
        for k in map(int, a.steps.split(",")):
            o = f"{a.out}/{th}_{var}{k}"
            sp = ["--line-spacing-step", "1"]
            if var == "line": sp = ["--line-spacing-step", str(k)]
            else: sp += [f"--{var}-spacing-step", str(k)]
            subprocess.run([sys.executable, "-m", "kindle_render", "epub", a.epub, o, "--pages", "6",
                            "--size26", str(s26), "--x0", str(x0), "--right", str(right), "--top", "168",
                            "--page-bottom", "2203"] + sp + extra, capture_output=True)
            cap = f"{a.cap}/{th}/theme_{th}/{var}_step_{k}_of_5"
            d = []
            for i in range(1, 6):
                f = f"{o}/page_{i:03d}.png"
                d.append(compare(f"{cap}/page_{i:03d}.png", f)["diff_pixel_count"] if os.path.exists(f) else None)
            res[f"{th}.{var}{k}"] = d
            print(th, var, k, d, "SUM2-5", sum(x for x in d[1:] if x is not None), flush=True)
json.dump(res, open(f"{a.out}/spacing_scores.json", "w"), indent=1)
print("GRAND", sum(sum(x for x in v[1:] if x is not None) for v in res.values()))
