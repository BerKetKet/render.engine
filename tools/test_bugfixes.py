#!/usr/bin/env python3
"""Regression tests for the 8 engine bug fixes and Config.extra_lead_px."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kindle_render.config import Config
from kindle_render.epub import Block
from kindle_render.fonts import Family
from kindle_render.layout import Run, build_items, break_kp
from kindle_render.page import layout_blocks_to_ir

def test_all():
    # 1. Config default pitch_px() at size 34px -> 51 (round half up)
    c34 = Config(size26=34 * 64, pitch=0)
    assert c34.pitch_px() == 51, f"Expected 51, got {c34.pitch_px()}"

    # 2. Config.extra_lead_px() for Compact (39/53), probe (42/57), Standard (45/68), Large (50/82)
    assert Config(size26=39 * 64, pitch=53).extra_lead_px() == 0.0
    assert Config(size26=42 * 64, pitch=57).extra_lead_px() == 0.0
    assert Config(size26=45 * 64, pitch=68).extra_lead_px() > 6.0
    assert Config(size26=50 * 64, pitch=82).extra_lead_px() > 14.0

    # 3. Dead heading_*_em removed from Config
    assert not hasattr(Config(), "heading_margin_top_em")
    assert not hasattr(Config(), "heading_margin_bottom_em")

    # 4. Long paragraph (>1000 items) uses Knuth-Plass (break_kp returns non-None)
    cfg = Config(max_kp_items=5000)
    fam = Family(cfg)
    long_txt = " ".join(["word"] * 600)
    items = build_items([Run(long_txt, False, False)], fam, cfg, cfg.size26)
    assert len(items) > 1000
    kp_res = break_kp(items, lambda i: (cfg.right - cfg.x0) * 64, 4.0, cfg, False)
    assert kp_res is not None and len(kp_res) > 10

    # 5. Tall table splits across pages without overflowing page_bottom
    rows = [[("Col A", True, "center", 1, 1), ("Col B", True, "center", 1, 1)]] + [
        [(f"Row {i}", False, "left", 1, 1), (f"Value {i}", False, "left", 1, 1)]
        for i in range(40)
    ]
    tbl_block = Block(kind="table", table_rows=rows, border_collapse=True)
    ir = layout_blocks_to_ir([tbl_block], cfg, fam)
    assert len(ir.pages) >= 2, f"Expected tall table to split across >=2 pages, got {len(ir.pages)}"

    # 6. Multi-line heading near page bottom moves to next page instead of splitting
    p_tall = Block(kind="text", runs=[Run("Line\n" * 33 + "Line", False, False)])
    h2_long = Block(kind="text", runs=[Run("A Very Long Multi Line Heading Title That Wraps Across Two Lines On The Page", True, False)], heading=2, scale=1.5)
    ir_h = layout_blocks_to_ir([p_tall, h2_long], cfg, fam)
    assert len(ir_h.pages) == 2

    print("ALL BUGFIX TESTS PASSED")

if __name__ == "__main__":
    test_all()
