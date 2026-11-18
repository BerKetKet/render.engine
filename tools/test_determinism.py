#!/usr/bin/env python3
"""Cross-process & PYTHONHASHSEED determinism test (H4).

Renders each corpus in two separate subprocesses with PYTHONHASHSEED=1 and
PYTHONHASHSEED=42 and asserts 100% identical per-page pixel SHA-256 and
layout SHA-256 hashes.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

WORKER_CODE = """
import hashlib, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path.cwd()))
from kindle_render.epub import load_epub
from kindle_render.fonts import Family
from kindle_render.page import render_blocks
from tools.corpus import resolve_corpus_file, make_config

cname = sys.argv[1]
profs = json.loads(Path("tools/profiles.json").read_text())
cprof = profs["corpora"][cname]
ep = resolve_corpus_file(cprof["epub"], profs["search_paths"])
cfg = make_config(cprof["config"])
fam = Family(cfg)
blocks = load_epub(str(ep), cfg)
imgs, meta = render_blocks(blocks, cfg, fam, max_pages=cprof["max_pages"], return_meta=True)
px = [hashlib.sha256(np.asarray(im).tobytes()).hexdigest() for im in imgs]
lay = meta.get("layout_hashes", [])
print(json.dumps({"px": px, "lay": lay}))
"""


def run_with_seed(cname: str, seed: str) -> dict:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = seed
    proc = subprocess.run(
        [sys.executable, "-c", WORKER_CODE, cname],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout.strip().splitlines()[-1])


def main() -> int:
    corpora = ["probe", "exam1", "exam2", "exam3_normal", "exam3_small", "tables_images"]
    all_ok = True
    for cname in corpora:
        r1 = run_with_seed(cname, "1")
        r2 = run_with_seed(cname, "42")
        px_ok = (r1["px"] == r2["px"])
        lay_ok = (r1["lay"] == r2["lay"])
        ok = px_ok and lay_ok
        if not ok:
            all_ok = False
        print(f"[determinism:{cname}] pages={len(r1['px'])} pixel_eq={px_ok} layout_eq={lay_ok} {'PASS' if ok else 'FAIL'}", flush=True)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
