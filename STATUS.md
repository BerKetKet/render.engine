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
