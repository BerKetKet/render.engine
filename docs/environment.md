# Environment & HarfBuzz Policy (`kindle_render` v1.11.5)

## 1. HarfBuzz Lock Enforcement Audit
- **Prior inconsistency**: `verify_harfbuzz(allow_unshaped=...)` (`kindle_render/fonts.py:36`) was previously called only by `tools/test_harfbuzz_lock.py`. Production and tool entry points (`kindle_render/cli.py`, `kindle_render/__init__.py:render_epub`/`render_to_ir`, `tools/corpus.py`, `tools/test_text_layer.py`, `tools/test_parallel_raster.py`, `tools/test_boundary.py`, `tools/test_bugfixes.py`) instantiated `Family(cfg)` directly without calling `verify_harfbuzz()`, so a non-locked HarfBuzz runtime (such as `8.3.0`) passed `cli.py` and `corpus.py` silently while failing `tools/test_harfbuzz_lock.py`.
- **Unified enforcement (`v1.11.5`)**: `Family.__init__(self, cfg)` (`kindle_render/fonts.py`) now calls `verify_harfbuzz(allow_unshaped=getattr(cfg, "allow_unshaped", False))`, and `kindle_render/cli.py` exposes `--allow-unshaped` on `epub`, `text`, and `lines` subcommands. Every entry point now enforces the exact same rule.

## 2. HarfBuzz Version Policy: Exact Pin (`6.0.0`)
- **Policy**: **Exact pin to HarfBuzz `6.0.0`** (matching `requirements.lock`: `# HarfBuzz runtime: 6.0.0`), enforced at `Family.__init__` unless `allow_unshaped=True` (`--allow-unshaped`) is explicitly passed for debugging.
- **Cross-version testing status**: On the reference VM (`libharfbuzz.so.0.60000.0`, `uharfbuzz` not installed, offline sandbox), only HarfBuzz `6.0.0` is available, so all-corpus pixel/layout hash equivalence under a second HarfBuzz version (e.g., `8.3.0`) could not be measured here. While the owner observed matching page outputs on `8.3.0` (`HYPOTHESIS` for cross-version equivalence), the Rust port should link a pinned HarfBuzz (`harfbuzz-rs` / `rustybuzz` or `libharfbuzz` `6.0.0`) until a full-corpus `8.3.0` vs `6.0.0` hash-comparison run is recorded.

## 3. Pinned Runtime Dependencies (`requirements.lock`)
- **Python**: `3.11.x`
- **HarfBuzz**: `6.0.0` (`libharfbuzz.so.0.60000.0`)
- **FreeType**: `2.12.1` (bundled / system `libfreetype.so.6`)
- **Pillow**: `10.2.0`
- **NumPy**: `1.26.x`
- **fontTools**: `4.47.x`
