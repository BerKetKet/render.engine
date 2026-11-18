#!/usr/bin/env python3
"""Gate G6 test for HarfBuzz loud failure on missing library or version mismatch."""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import kindle_render.fonts as fonts_mod
from kindle_render.config import Config
from kindle_render.fonts import Family, verify_harfbuzz


def main():
    # 1. Default matching environment must pass
    verify_harfbuzz(allow_unshaped=False)
    fam_ok = Family(Config(allow_unshaped=False))
    assert fam_ok is not None

    orig_cdll = fonts_mod._hb_cdll
    orig_ver = fonts_mod._HB_VERSION

    # 2. Simulate missing library: must raise RuntimeError when allow_unshaped=False
    missing_raised = False
    try:
        fonts_mod._hb_cdll = None
        verify_harfbuzz(allow_unshaped=False)
    except RuntimeError as e:
        missing_raised = ("could not be loaded" in str(e))
    finally:
        fonts_mod._hb_cdll = orig_cdll
    assert missing_raised, "Expected RuntimeError when _hb_cdll is None and allow_unshaped=False"

    # 3. Simulate missing library with allow_unshaped=True: must not raise
    try:
        fonts_mod._hb_cdll = None
        verify_harfbuzz(allow_unshaped=True)
    finally:
        fonts_mod._hb_cdll = orig_cdll

    # 4. Simulate wrong version: must raise RuntimeError when allow_unshaped=False
    wrong_ver_raised = False
    try:
        fonts_mod._HB_VERSION = "0.0.0-mismatch"
        os.environ["KINDLE_RENDER_STRICT_HARFBUZZ"] = "1"
        verify_harfbuzz(allow_unshaped=False)
    except RuntimeError as e:
        wrong_ver_raised = ("version mismatch" in str(e))
    finally:
        fonts_mod._HB_VERSION = orig_ver
        os.environ.pop("KINDLE_RENDER_STRICT_HARFBUZZ", None)
    assert wrong_ver_raised, "Expected RuntimeError when _HB_VERSION mismatches LOCKED_HARFBUZZ_VERSION"

    # 4b. Default (non-strict) mismatch must only warn, never raise
    try:
        fonts_mod._HB_VERSION = "0.0.0-mismatch"
        verify_harfbuzz(allow_unshaped=False)
    finally:
        fonts_mod._HB_VERSION = orig_ver

    # 5. Simulate wrong version with allow_unshaped=True: must not raise
    try:
        fonts_mod._HB_VERSION = "0.0.0-mismatch"
        verify_harfbuzz(allow_unshaped=True)
    finally:
        fonts_mod._HB_VERSION = orig_ver

    print(
        f"[test_harfbuzz_lock] loaded={fonts_mod._hb_cdll is not None} "
        f"version={fonts_mod._HB_VERSION} locked={fonts_mod.LOCKED_HARFBUZZ_VERSION} "
        f"missing_loud_fail={missing_raised} version_mismatch_loud_fail={wrong_ver_raised} PASSED"
    )


if __name__ == "__main__":
    main()
