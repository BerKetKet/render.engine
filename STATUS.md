# STATUS — kindle_render v1.6.1

## Completed in v1.6.0
1. **Step A (A1–A3)**: Removed all hardcoded table column widths, CSS class-name lists, and `cfg.size26 == 2688 and cfg.x0 == 79` geometry branches.
2. **Step B (B1–B10)**: Implemented general fixes across `config.py`, `epub.py`, `fonts.py`, `layout.py`, and `page.py` with **zero page regressions across all three corpora**:
   - `exam2`: `31/65 -> 35/65` bitwise identical (`2,312,009 -> 1,151,895` diff pixels, `1,321 / 1,529` positional exact lines).
   - `probe`: `36/86 -> 37/86` bitwise identical (`579,593 -> 486,515` diff pixels, `2,703 / 2,863` positional exact lines, Page 81 = `0` diff pixels).
   - `exam1`: `40/70 -> 42/70` bitwise identical (`1,756,396 -> 1,596,835` diff pixels, `1,401 / 1,568` positional exact lines).
3. **Synthetic Generalization Suite**: Verified on `tools/reports/synthetic/synthetic_generalization.epub`.

## Exact Commands to Resume / Verify
```bash
python3 tools/corpus.py --out-dir tools/reports
```

## v1.6.1 housekeeping (after independent verification)
- Golden hashes removed (tools/golden). Pixels unchanged vs 1.6.0.
- Independently measured (not from the Gemini report): exam2 35/65, probe 37/86, exam1 42/70 identical; no page that was identical in 1.5.0 became non-identical.
- Known open issue: table header cells can still break mid-word in narrow columns (e.g. "Recov-/ery"); see BACKLOG.md.
- Next: layout/raster refactor, then fidelity fixes. Re-generate golden hashes only right before the refactor, with `python3 tools/corpus.py --update-golden`.


## Phase 0 Completed (Adopt and Freeze Baseline v1.6.1)
- **What is done**:
  - 0.1: Initialized clean git repo, committed baseline tree as `import v1.6.1`, tagged `v1.6.1`. Verified `__version__ = "1.6.1"` in `kindle_render/__init__.py` matches `README.md` and `CHANGELOG.md`.
  - 0.2: Created `DATA_PROVENANCE.md` with SHA-256 digests and established embedded origin/licence metadata for all 14 font files and 15 hyphenation files (`unknown` where not embedded). Zero modifications to any font or hyphenation data file.
  - 0.3: Updated `tools/profiles.json` `search_paths` to relative paths (`["corpora", ".", ".."]`).
  - 0.4: Ran `tools/corpus.py --no-golden` across all three corpora and confirmed exact match with baseline figures:
    - `exam2`: `35/65` bitwise identical pages (`1,176,881` diff px, `1,318/1,529` pos lines, `1,339/1,529` PI lines).
    - `probe`: `37/86` bitwise identical pages (`486,515` diff px, `2,703/2,863` pos lines, `2,705/2,863` PI lines).
    - `exam1`: `42/70` bitwise identical pages (`1,607,042` diff px, `1,402/1,568` pos lines, `1,410/1,568` PI lines).
  - 0.5: Generated and committed `tools/golden/*.json` (`probe.json`, `exam1.json`, `exam2.json`, `synthetic.json`) as `golden v1.6.1` (`21eaa59`). Re-ran without `--update-golden` (all golden and double-render determinism checks passed) and saved `tools/reports/baseline_v161.json` and `tools/reports/baseline_v161.md`.
  - 0.6: Extended `tools/corpus.py` with `layout_pages` per-page layout IR hash checking (currently `{}` until Phase 2.1) and synthetic generalization suite verification (`--only synthetic`).
  - Tagged `prep-baseline-1.6.1`.
- **What is next**:
  - Phase 1: Inspect all code paths in `epub.py`, `fonts.py`, `layout.py`, `page.py`, `raster.py`, and `cli.py`, then write and commit `REFACTOR_PLAN.md` (at most 3 pages).
- **Exact commands to resume**:
  ```bash
  python3 tools/corpus.py --only probe
  python3 tools/corpus.py --only exam1
  python3 tools/corpus.py --only exam2
  python3 tools/corpus.py --only synthetic
  ```
- **Previous Git Commit**: `91c97164c179d6d6c740a2574849d74694c866c1`


## Phase 1 Completed (Design Before Code — `REFACTOR_PLAN.md`)
- **What is done**:
  - Reviewed `ARCHITECTURE_NOTES.md` sections 1, 2, and 5 and inspected all modules (`config.py`, `epub.py`, `fonts.py`, `hyphen.py`, `layout.py`, `page.py`, `raster.py`, `cli.py`).
  - Wrote and committed `REFACTOR_PLAN.md` defining: (1) the versioned `PositionedDocument` / `PositionedPage` / `RenderCommand` IR boundary, (2) the layout vs. raster dependency rule and why HarfBuzz lives in `fonts.py`, (3) the complete pixel-snapping ownership table, (4) the structured text layer design and `docs/text_layer_schema.md` contract, (5) instance-owned FreeType / `GlyphCache` state for thread/process parallelism, (6) staged commits 2.1–2.7 with risk estimates, and (7) out-of-scope items.
- **What is next**:
  - Phase 2.1: Introduce `kindle_render/ir.py`, build IR alongside the old drawing path in `page.py`, assert bitwise equality on every page between old path and IR rasterization, and record `layout_pages` hashes in `tools/golden/*.json`.
- **Exact commands to resume**:
  ```bash
  python3 tools/corpus.py --only probe
  python3 tools/corpus.py --only exam1
  python3 tools/corpus.py --only exam2
  python3 tools/corpus.py --only synthetic
  ```
- **Previous Git Commit**: `cc4c309`


## Phase 2.1 Completed (IR Data Classes, Dual-Path Verification & Layout Goldens)
- **What is done**:
  - Added `kindle_render/ir.py` (`PositionedDocument`, `PositionedPage`, `GlyphCommand`, `RectCommand`, `RuleCommand`, `RingBulletCommand`, `ImageCommand`, `TextBlockMeta`, `ir_version = "1.0"`, and canonical sorted-key JSON serialization with 6-decimal float formatting).
  - Updated `fonts.py`, `epub.py`, `layout.py`, `page.py`, and `raster.py` so `Pager` builds `PositionedPage` IR alongside the old canvas path and asserts `np.array_equal(old_im, ir_im)` on every rendered page.
  - Populated `layout_pages` SHA-256 hashes in `tools/golden/probe.json` (98 pages), `tools/golden/exam1.json` (70 pages), `tools/golden/exam2.json` (65 pages), and `tools/golden/synthetic.json` (4 pages), and verified G1, G2, G3, G5 pass with 100% identical pixel hashes.
- **What is next**:
  - Phase 2.2: Switch drawing to read only the IR (`Rasterizer.rasterize_page`) and delete the old direct canvas drawing path from `page.py`.
- **Exact commands to resume**:
  ```bash
  python3 tools/corpus.py --only probe
  python3 tools/corpus.py --only exam1
  python3 tools/corpus.py --only exam2
  python3 tools/corpus.py --only synthetic
  ```
- **Previous Git Commit**: `c0e3727`


## Phase 2.2 Completed (Switch Drawing to Read Only IR)
- **What is done**:
  - Removed the old direct canvas drawing path (`self.canvas`, `self.images`, `draw_glyph`, `_to_image`) from `Pager` in `kindle_render/page.py`.
  - Added `layout_blocks_to_ir` and `layout_lines_to_ir` returning `PositionedDocument` and `PositionedPage`, and delegated all bitmap rendering in `render_blocks` and `render_lines` exclusively to `Rasterizer.rasterize_document` / `Rasterizer.rasterize_page`.
  - Verified G1, G2, G3, and G5 pass across `probe`, `exam1`, `exam2`, and `synthetic`.
- **What is next**:
  - Phase 2.3: Add `tools/check_imports.py` to enforce the import-graph gate (G4) and ensure layout modules (`epub.py`, `fonts.py`, `hyphen.py`, `layout.py`, `ir.py`, and layout functions in `page.py`) have zero FreeType or raster dependencies.
- **Exact commands to resume**:
  ```bash
  python3 tools/corpus.py --only probe
  python3 tools/corpus.py --only exam1
  python3 tools/corpus.py --only exam2
  python3 tools/corpus.py --only synthetic
  ```
- **Previous Git Commit**: `1c5cc55`


## Phase 2.3 Completed (Isolate FreeType Behind Raster & Add Import-Graph Gate G4)
- **What is done**:
  - Verified that all layout modules (`config.py`, `epub.py`, `fonts.py`, `hyphen.py`, `layout.py`, `ir.py`, and `Pager` / `layout_blocks_to_ir` / `layout_lines_to_ir` in `page.py`) have zero imports of `raster` or `freetype` and zero references to `libfreetype`.
  - Added `tools/check_imports.py` and wired it directly into `tools/corpus.py` so Gate G4 runs automatically on every invocation.
  - Verified G1–G5 pass.
- **What is next**:
  - Phase 2.4: Add `tools/test_parallel_raster.py` testing concurrent rasterization of the same IR pages across both multiple threads (`ThreadPoolExecutor`) and multiple processes (`ProcessPoolExecutor`), comparing pixel SHA-256 hashes against the golden hashes.
- **Exact commands to resume**:
  ```bash
  python3 tools/check_imports.py
  python3 tools/corpus.py --only synthetic
  ```
- **Previous Git Commit**: `c1ffb06`


## Phase 2.4 Completed (Instance-Owned Raster State & Concurrency Verification)
- **What is done**:
  - Verified `Rasterizer` and `GlyphCache` own their `FT_Library` handle (`self._ft_lib`), face map, and glyph bitmap cache per instance with zero process-global FreeType state.
  - Added `tools/test_parallel_raster.py` and verified across `exam2` (65 pages), `exam1` (70 pages), and `probe` (98 pages) that two concurrent threads (`ThreadPoolExecutor`) and two concurrent processes (`ProcessPoolExecutor`) produce 100% identical SHA-256 hashes matching `tools/golden/*.json`.
- **What is next**:
  - Phase 2.5: Add `docs/text_layer_schema.md`, `kindle_render/text_layer.py`, CLI `kindle_render text` + `epub --text-layer`, and `tools/test_text_layer.py` verifying tests (a)–(d) across all three corpora.
- **Exact commands to resume**:
  ```bash
  python3 tools/test_parallel_raster.py
  python3 tools/corpus.py --only synthetic
  ```
- **Previous Git Commit**: `aafa698`


## Phase 2.5 Completed (Structured Text Layer, Schema & Tests a–d)
- **What is done**:
  - Defined the per-page (`page_NNN.json`) and document (`document.json`) structured text layer JSON schema in `docs/text_layer_schema.md`.
  - Implemented `kindle_render/text_layer.py` (`build_page_text_layer`, `build_document_text_layer`, `validate_page_text_layer`, `validate_document_text_layer`, `write_text_layer_files`).
  - Added CLI subcommand `kindle_render text IN.epub OUT_DIR` and `--text-layer` flag on `kindle_render epub`.
  - Added and executed `tools/test_text_layer.py` (saved results to `tools/reports/text_layer_tests.json`), confirming across all three corpora:
    - **(a) Chapter text equality after normalisation (ignoring hyphenation)**: `probe` 23/23 chapters match, `exam1` 16/16 chapters match, `exam2` 19/19 chapters match.
    - **(b) Glyph boxes equal glyph draw commands**: `probe` `73,580 == 73,580`, `exam1` `45,618 == 45,618`, `exam2` `46,635 == 46,635`.
    - **(c) All bounding boxes lie strictly inside the page**: `0` out-of-page boxes across all 233 pages (`probe` 98, `exam1` 70, `exam2` 65); schema validation passed on every page.
    - **(d) Identical pixels with and without text layer**: 100% bitwise identical SHA-256 hashes on all pages.
- **What is next**:
  - Phase 2.6: Expose public functions `render_to_ir(book, cfg)` and `rasterize(ir_page, cfg)` in `kindle_render/__init__.py` and document an example in `README.md`.
- **Exact commands to resume**:
  ```bash
  python3 tools/test_text_layer.py
  python3 tools/corpus.py --only synthetic
  ```
- **Previous Git Commit**: `f43ebbc`
