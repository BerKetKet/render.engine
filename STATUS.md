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
