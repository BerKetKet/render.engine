# Environment & HarfBuzz Policy (`kindle_render` v1.11.5)

## 1. HarfBuzz Lock Enforcement Audit
- **Prior inconsistency**: `verify_harfbuzz(allow_unshaped=...)` (`kindle_render/fonts.py:36`) was previously called only by `tools/test_harfbuzz_lock.py`. Production and tool entry points (`kindle_render/cli.py`, `kindle_render/__init__.py:render_epub`/`render_to_ir`, `tools/corpus.py`, `tools/test_text_layer.py`, `tools/test_parallel_raster.py`, `tools/test_boundary.py`, `tools/test_bugfixes.py`) instantiated `Family(cfg)` directly without calling `verify_harfbuzz()`, so a non-locked HarfBuzz runtime (such as `8.3.0`) passed `cli.py` and `corpus.py` silently while failing `tools/test_harfbuzz_lock.py`.
- **Unified enforcement (`v1.11.5`)**: `Family.__init__(self, cfg)` (`kindle_render/fonts.py`) now calls `verify_harfbuzz(allow_unshaped=getattr(cfg, "allow_unshaped", False))`, and `kindle_render/cli.py` exposes `--allow-unshaped` on `epub`, `text`, and `lines` subcommands. Every entry point now enforces the exact same rule.

## 2. HarfBuzz Version Policy (v1.11.6): lock = reference, not a gate
- **Reference**: HarfBuzz `6.0.0` (`requirements.lock`). Missing library is still a hard error (unless `--allow-unshaped`).
- **Different version**: the engine RUNS. Versions in `VERIFIED_IDENTICAL_HARFBUZZ` (`6.0.0`, `8.3.0`) run silently; any other version prints one warning to stderr. 8.3.0 was observed to give identical pages on the corpora (owner-run). Keep re-checking with a hash comparison when adding a version to the set.
- **Strict mode** (CI, parity oracle for the Rust port): set `KINDLE_RENDER_STRICT_HARFBUZZ=1` to make any mismatch an error.

## 3. Pinned Runtime Dependencies (`requirements.lock`)
- **Python**: `3.11.x`
- **HarfBuzz**: `6.0.0` (`libharfbuzz.so.0.60000.0`)
- **FreeType**: `2.12.1` (bundled / system `libfreetype.so.6`)
- **Pillow**: `10.2.0`
- **NumPy**: `1.26.x`
- **fontTools**: `4.47.x`
