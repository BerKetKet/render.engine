# Stage G `[P]` — Layout / Raster IR Boundary Hardening Report

## Summary of Boundary Hardening Verification Across All 5 Corpora
- **Import-Graph Gate (`G4`, `tools/check_imports.py`)**: `passed=True` (`0` FreeType or `raster` references in `config.py`, `epub.py`, `fonts.py`, `hyphen.py`, `ir.py`, `layout.py`, `page.py`, `text_layer.py`).
- **IR Schema & Coordinate Invariant Validation (`validate_ir_document`)**: `0` errors across all `369` rendered pages (`probe` 98, `exam1` 70, `exam2` 65, `exam3_normal` 82, `exam3_small` 54).
- **Canonical Dictionary/JSON Round-Trip (`PositionedDocument.from_dict(ir_doc.to_dict())`)**: `369/369` pages preserve identical `layout_sha256` hashes after serialization and deserialization.
- **Pixel Round-Trip Verification**: `25/25` sampled pages (covering cover images, TOC subpixel link underlines, collapsed/uncollapsed tables, ring/square bullets, and verse/prose pages) produce `100%` byte-identical pixel SHA-256 digests when rasterized from deserialized IR.
