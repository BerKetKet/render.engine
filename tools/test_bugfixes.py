#!/usr/bin/env python3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kindle_render import Config, layout_blocks_to_ir
from kindle_render.epub import Block
from kindle_render.fonts import Family
from kindle_render.layout import Run


def main() -> int:
    # 1. Config default pitch_px at size 34 (2176) with pitch=0
    c34 = Config(size26=2176, pitch=0)
    assert c34.pitch_px() == 51, f"Expected 51, got {c34.pitch_px()}"

    # 2. Tall table (> 1 page) splits across pages and never exceeds page_bottom
    cfg = Config(size26=2688, x0=79, right=1001, pitch=57, top=168, page_bottom=2203)
    fam = Family(cfg)
    rows = [[("Row " + str(r), False, None, 1, 1), ("Value " + str(r), False, None, 1, 1)] for r in range(60)]
    b_tbl = Block(kind="table", runs=[], table_rows=rows, border_collapse=True)
    doc = layout_blocks_to_ir([b_tbl], cfg, fam)
    assert len(doc.pages) >= 2, f"Expected tall table to split across >=2 pages, got {len(doc.pages)}"
    for pg in doc.pages:
        max_y = max((cmd.baseline for cmd in pg.commands if getattr(cmd, "kind", "") == "glyph"), default=0)
        assert max_y <= cfg.page_bottom, f"Glyph baseline {max_y} exceeded page_bottom {cfg.page_bottom}"

    # 3. Scaled run (2.5x) near page bottom does not overflow page_bottom
    blocks = [Block(runs=[Run("Normal body line of text for spacing.")]) for _ in range(34)]
    blocks.append(Block(runs=[Run("Tall scaled run", scale=2.5)]))
    doc2 = layout_blocks_to_ir(blocks, cfg, fam)
    for pg in doc2.pages:
        max_y = max((cmd.baseline for cmd in pg.commands if getattr(cmd, "kind", "") == "glyph"), default=0)
        assert max_y <= cfg.page_bottom, f"Scaled run baseline {max_y} exceeded page_bottom {cfg.page_bottom}"

    print("[test_bugfixes] pitch_34=51 tall_table_pages=%d scaled_run_pages=%d ALL PASSED" % (len(doc.pages), len(doc2.pages)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
