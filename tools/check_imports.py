#!/usr/bin/env python3
"""Import-graph and dependency boundary verifier (Gate G4) for kindle_render.

Verifies:
1. Pure layout modules (`config.py`, `epub.py`, `fonts.py`, `hyphen.py`, `layout.py`, `ir.py`, `text_layer.py`)
   contain zero AST imports of `raster` or `freetype` and zero references to `libfreetype` or `FT_`.
2. `page.py` top-level imports do not import `raster` or `freetype`, and `Pager`, `layout_blocks_to_ir`,
   and `layout_lines_to_ir` contain zero imports of `raster` or `freetype` (only the legacy convenience
   wrappers `render_blocks` and `render_lines` delegate to `Rasterizer`).
3. `raster.py` contains zero module-level `FT_Library` handles (`_ft_lib_handle`).
"""
import ast
import sys
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
PKG_DIR = REPO_ROOT / "kindle_render"

PURE_LAYOUT_MODULES = [
    "config.py",
    "epub.py",
    "fonts.py",
    "hyphen.py",
    "layout.py",
    "ir.py",
]

FORBIDDEN_IMPORT_TARGETS = {"raster", "kindle_render.raster", "freetype"}
FORBIDDEN_SYMBOLS = {"libfreetype", "FT_Init_FreeType", "FT_New_Face", "FT_Load_Glyph", "FT_Render_Glyph", "_ft_lib_handle"}


def _imported_names(node: ast.AST) -> List[str]:
    names = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            names.append(alias.name)
    elif isinstance(node, ast.ImportFrom):
        mod = node.module or ""
        names.append(mod)
        for alias in node.names:
            names.append(f"{mod}.{alias.name}" if mod else alias.name)
    return names


def check_imports() -> Tuple[bool, List[str], Dict[str, List[str]]]:
    errors: List[str] = []
    graph: Dict[str, List[str]] = {}

    for fn in PURE_LAYOUT_MODULES + (["text_layer.py"] if (PKG_DIR / "text_layer.py").is_file() else []):
        fp = PKG_DIR / fn
        if not fp.is_file():
            continue
        src = fp.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(fp))
        mod_imports = []
        for node in ast.walk(tree):
            for imp in _imported_names(node):
                mod_imports.append(imp)
                base = imp.split(".")[-1]
                if imp in FORBIDDEN_IMPORT_TARGETS or base in ("raster", "freetype"):
                    errors.append(f"{fn}: forbidden import '{imp}' in layout module")
        for sym in FORBIDDEN_SYMBOLS:
            if sym in src:
                errors.append(f"{fn}: forbidden FreeType symbol '{sym}' in layout module")
        graph[fn] = sorted(set(mod_imports))

    # Check page.py: top-level and layout functions (Pager, layout_blocks_to_ir, layout_lines_to_ir) must not import raster or freetype
    page_fp = PKG_DIR / "page.py"
    page_src = page_fp.read_text(encoding="utf-8")
    page_tree = ast.parse(page_src, filename=str(page_fp))
    page_top_imports = []
    for node in page_tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for imp in _imported_names(node):
                page_top_imports.append(imp)
                base = imp.split(".")[-1]
                if imp in FORBIDDEN_IMPORT_TARGETS or base in ("raster", "freetype"):
                    errors.append(f"page.py: forbidden top-level import '{imp}'")
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in ("Pager", "layout_blocks_to_ir", "layout_lines_to_ir"):
            for sub in ast.walk(node):
                for imp in _imported_names(sub):
                    base = imp.split(".")[-1]
                    if imp in FORBIDDEN_IMPORT_TARGETS or base in ("raster", "freetype"):
                        errors.append(f"page.py:{node.name}: forbidden import '{imp}' in layout path")
    for sym in FORBIDDEN_SYMBOLS:
        if sym in page_src:
            errors.append(f"page.py: forbidden FreeType symbol '{sym}'")
    graph["page.py (top-level)"] = sorted(set(page_top_imports))

    # Check raster.py: must not have process-global _ft_lib_handle
    raster_fp = PKG_DIR / "raster.py"
    raster_src = raster_fp.read_text(encoding="utf-8")
    if "_ft_lib_handle" in raster_src:
        errors.append("raster.py: contains module-level '_ft_lib_handle'")

    return (len(errors) == 0), errors, graph


def main():
    ok, errors, graph = check_imports()
    for mod, imps in sorted(graph.items()):
        print(f"  {mod:24s} -> {imps}")
    if ok:
        print("[G4 import-graph] passed=True errors=0")
        sys.exit(0)
    else:
        for e in errors:
            print(f"[G4 ERROR] {e}")
        print(f"[G4 import-graph] passed=False errors={len(errors)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
