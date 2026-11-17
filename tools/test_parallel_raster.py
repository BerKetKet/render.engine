#!/usr/bin/env python3
"""Parallel rasterization verifier (Phase 2.4) for kindle_render.

Tests:
1. Two concurrent threads (`ThreadPoolExecutor(max_workers=2)`) each creating their own
   `Rasterizer` instance and rasterizing the same `PositionedPage` list concurrently.
2. Two concurrent processes (`ProcessPoolExecutor(max_workers=2)`) each rasterizing
   the same `PositionedPage` list concurrently.
3. Asserts that sequential hashes, thread-1 hashes, thread-2 hashes, process-1 hashes,
   process-2 hashes, and stored golden hashes in `tools/golden/*.json` are 100% identical.
"""
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from pathlib import Path
from typing import List
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kindle_render.config import Config
from kindle_render.epub import load_epub
from kindle_render.fonts import Family
from kindle_render.page import layout_blocks_to_ir
from kindle_render.raster import Rasterizer
from tools.corpus import resolve_corpus_file, make_config


def _hash_img(im) -> str:
    return hashlib.sha256(np.asarray(im).tobytes()).hexdigest()


def _rasterize_pages_worker(args) -> List[str]:
    ir_pages, prof_cfg = args
    cfg = make_config(prof_cfg)
    rast = Rasterizer(cfg)
    try:
        return [_hash_img(rast.rasterize_page(p)) for p in ir_pages]
    finally:
        rast.close()


def main():
    profiles_data = json.loads((REPO_ROOT / "tools" / "profiles.json").read_text())
    search_paths = profiles_data["search_paths"]

    for cname in ("exam2", "exam1", "probe"):
        cprof = profiles_data["corpora"][cname]
        epub_path = resolve_corpus_file(cprof["epub"], search_paths)
        cfg = make_config(cprof["config"])
        fam = Family(cfg)
        blocks = load_epub(str(epub_path), cfg)
        ir_doc = layout_blocks_to_ir(blocks, cfg, fam, max_pages=cprof["max_pages"])
        ir_pages = ir_doc.pages

        golden = json.loads((REPO_ROOT / "tools" / "golden" / f"{cname}.json").read_text())
        golden_hashes = [golden["pages"][str(i + 1)] for i in range(len(ir_pages))]

        # 1. Two concurrent threads
        with ThreadPoolExecutor(max_workers=2) as tex:
            f1 = tex.submit(_rasterize_pages_worker, (ir_pages, cprof["config"]))
            f2 = tex.submit(_rasterize_pages_worker, (list(reversed(ir_pages)), cprof["config"]))
            th1_hashes = f1.result()
            th2_hashes = list(reversed(f2.result()))

        # 2. Two concurrent processes
        with ProcessPoolExecutor(max_workers=2) as pex:
            p1 = pex.submit(_rasterize_pages_worker, (ir_pages, cprof["config"]))
            p2 = pex.submit(_rasterize_pages_worker, (list(reversed(ir_pages)), cprof["config"]))
            pr1_hashes = p1.result()
            pr2_hashes = list(reversed(p2.result()))

        ok_t1 = (th1_hashes == golden_hashes)
        ok_t2 = (th2_hashes == golden_hashes)
        ok_p1 = (pr1_hashes == golden_hashes)
        ok_p2 = (pr2_hashes == golden_hashes)
        print(
            f"[parallel-raster:{cname}] pages={len(ir_pages)} "
            f"threads_equal={th1_hashes == th2_hashes} "
            f"procs_equal={pr1_hashes == pr2_hashes} "
            f"matches_golden={ok_t1 and ok_t2 and ok_p1 and ok_p2}"
        )
        if not (ok_t1 and ok_t2 and ok_p1 and ok_p2):
            sys.exit(1)

    print("[Phase 2.4 parallel rasterization] ALL PASSED")


if __name__ == "__main__":
    main()
