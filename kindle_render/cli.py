import argparse, json, os, sys
from pathlib import Path
from .config import Config, PALETTES
from .fonts import Family


def _add_epub_args(p):
    p.add_argument("epub", help="path to input .epub")
    p.add_argument("outdir", help="directory to write output files")
    p.add_argument("--pages", type=int, default=10, help="max pages to render")
    p.add_argument("--fonts", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"), help="directory containing Bookerly TTF files")
    p.add_argument("--size26", type=int, default=0, help="body font size in 26.6 fixed-point units (e.g. 2688 for 42px, 2880 for 45px)")
    p.add_argument("--x0", type=int, default=0, help="left margin x0 in pixels (e.g. 39 or 79)")
    p.add_argument("--right", type=int, default=0, help="right margin x1 in pixels (e.g. 1041 or 1001)")
    p.add_argument("--pitch", type=int, default=0, help="body line pitch in pixels (e.g. 57 or 68)")
    p.add_argument("--top", type=int, default=0, help="top margin y0 in pixels (default: 168)")
    p.add_argument("--page-bottom", type=int, default=0, help="bottom margin y1 in pixels (default: 2203)")
    p.add_argument("--breaker", choices=["kp", "greedy"], default="kp", help="line breaker algorithm (default: kp)")
    p.add_argument("--no-justify", action="store_true", help="disable full justification")
    p.add_argument("--no-hyphen", action="store_true", help="disable on-device hyphenation")
    p.add_argument("--hyphen-dic", default="", help="path to custom TeX/Libhyphen .dic file")
    p.add_argument("--no-optical-margin", action="store_true", help="disable 50%% hanging punctuation (default)")
    p.add_argument("--optical-margin", action="store_true", help="enable 50%% hanging punctuation")
    p.add_argument("--micro-tracking", action="store_true", help="enable Tier 2 inter-character micro-tracking (default: off)")
    p.add_argument("--no-micro-tracking", action="store_true", help="disable Tier 2 micro-tracking (default)")
    p.add_argument("--boldness", type=int, default=0, choices=range(0, 6), help="boldness slider level (0-5)")
    p.add_argument("--palette", choices=list(PALETTES.keys()), default="exact", help="calibrated luminance color palette")
    p.add_argument("--fallback-raster", action="store_true", help="do not use FreeType")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="kindle_render")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # epub command
    e = sub.add_parser("epub", help="render an EPUB to PNG pages")
    _add_epub_args(e)
    e.add_argument("--text-layer", action="store_true", help="also emit per-page and document structured text layer JSON files")

    # text command
    t = sub.add_parser("text", help="extract structured text layer JSON from an EPUB without rasterizing bitmaps")
    _add_epub_args(t)

    # lines command
    l = sub.add_parser("lines", help="render exam-style lines (one string per line) to one PNG")
    l.add_argument("json", help="path to text json")
    l.add_argument("key", help="key in json")
    l.add_argument("out", help="output PNG path")
    l.add_argument("--count", type=int, default=35, help="max lines to render")
    l.add_argument("--fonts", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"), help="fonts directory")
    l.add_argument("--size26", type=int, default=0, help="body font size in 26.6 fixed-point units")
    l.add_argument("--x0", type=int, default=0, help="left margin x0 in pixels")
    l.add_argument("--right", type=int, default=0, help="right margin x1 in pixels")
    l.add_argument("--pitch", type=int, default=0, help="body line pitch in pixels")
    l.add_argument("--bold", action="store_true", help="force bold font")
    l.add_argument("--italic", action="store_true", help="force italic font")
    l.add_argument("--boldness", type=int, default=0, choices=range(0, 6), help="boldness slider level (0-5)")
    l.add_argument("--palette", choices=list(PALETTES.keys()), default="exact", help="calibrated luminance color palette")
    l.add_argument("--fallback-raster", action="store_true")

    # compare command
    c = sub.add_parser("compare", help="compare reference and output PNG")
    c.add_argument("ref", help="reference PNG")
    c.add_argument("out", help="output PNG")
    c.add_argument("--json", default=None, help="write comparison report json")
    c.add_argument("--diff", default=None, help="write false-color diff map PNG")

    a = ap.parse_args(argv)

    if a.cmd == "compare":
        from .compare import compare, print_report
        rep = compare(a.ref, a.out, diff_path=a.diff)
        print_report(rep)
        if a.json:
            json.dump(rep, open(a.json, "w"), indent=1)
        return 0

    cfg = Config(
        fonts_dir=a.fonts,
        exact_raster=not a.fallback_raster,
        boldness_level=getattr(a, "boldness", 0)
    )
    if getattr(a, "size26", 0) > 0:
        cfg.size26 = a.size26
    if getattr(a, "x0", 0) > 0:
        cfg.x0 = a.x0
    if getattr(a, "right", 0) > 0:
        cfg.right = a.right
    if getattr(a, "pitch", 0) > 0:
        cfg.pitch = a.pitch
        cfg.pitch_ratio = a.pitch / (cfg.size26 / 64.0)
    if getattr(a, "top", 0) > 0:
        cfg.top = a.top
    if getattr(a, "page_bottom", 0) > 0:
        cfg.page_bottom = a.page_bottom
    if getattr(a, "palette", "exact"):
        cfg.apply_palette(a.palette)

    if a.cmd == "lines":
        fam = Family(cfg)
        from .page import render_lines
        lines = json.load(open(a.json, encoding="utf-8"))[a.key][:a.count]
        render_lines(lines, cfg, fam, a.bold, a.italic).save(a.out)
        print("wrote", a.out)
        return 0

    cfg.breaker = a.breaker
    cfg.justify = not a.no_justify
    cfg.hyphenate = not a.no_hyphen
    if a.hyphen_dic:
        cfg.hyphen_dic = a.hyphen_dic
    cfg.optical_margin = bool(getattr(a, "optical_margin", False)) and not a.no_optical_margin
    cfg.micro_tracking = bool(getattr(a, "micro_tracking", False)) and not a.no_micro_tracking

    fam = Family(cfg)
    from .epub import load_epub
    from .page import layout_blocks_to_ir, render_blocks
    from .text_layer import write_text_layer_files

    blocks = load_epub(a.epub, cfg)
    if a.cmd == "text":
        ir_doc = layout_blocks_to_ir(blocks, cfg, fam, max_pages=a.pages)
        write_text_layer_files(ir_doc, Path(a.outdir))
        print(f"wrote text layer for {len(ir_doc.pages)} pages to {a.outdir}")
        return 0

    imgs, meta = render_blocks(blocks, cfg, fam, a.pages, return_meta=True)
    os.makedirs(a.outdir, exist_ok=True)
    for i, im in enumerate(imgs, 1):
        im.save(os.path.join(a.outdir, f"page_{i:03d}.png"))
    if getattr(a, "text_layer", False):
        write_text_layer_files(meta["ir_doc"], Path(a.outdir))
    print(f"wrote {len(imgs)} pages to {a.outdir}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
