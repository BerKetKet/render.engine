#!/usr/bin/env python3
"""Single-command gate runner for kindle_render (clean-clone reproducible).

Runs:
  1. check_imports.py
  2. test_harfbuzz_lock.py
  3. test_text_layer.py
  4. test_parallel_raster.py
  5. test_boundary.py
  6. test_bugfixes.py
  7. Pixel-hash & layout-hash golden gate for synthetic, all corpora, and sizes_00..07

Prints one PASS/FAIL line per gate and a final summary. Exit 0 iff all gates pass.
"""
import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.corpus import run_single_corpus, run_synthetic_suite


def run_cmd_gate(name: str, cmd: list) -> bool:
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    ok = (proc.returncode == 0)
    status = "PASS" if ok else "FAIL"
    last_line = ""
    for ln in reversed(proc.stdout.strip().splitlines()):
        if ln.strip():
            last_line = ln.strip()
            break
    print(f"[GATE] {name:24s} {status}  {last_line}", flush=True)
    if not ok and proc.stderr.strip():
        print(proc.stderr.strip(), file=sys.stderr)
    return ok


def main() -> int:
    all_ok = True
    passed = 0
    total = 0

    unit_gates = [
        ("check_imports", [sys.executable, "tools/check_imports.py"]),
        ("test_harfbuzz_lock", [sys.executable, "tools/test_harfbuzz_lock.py"]),
        ("test_text_layer", [sys.executable, "tools/test_text_layer.py"]),
        ("test_parallel_raster", [sys.executable, "tools/test_parallel_raster.py"]),
        ("test_boundary", [sys.executable, "tools/test_boundary.py"]),
        ("test_bugfixes", [sys.executable, "tools/test_bugfixes.py"]),
    ]
    for gname, cmd in unit_gates:
        total += 1
        if run_cmd_gate(gname, cmd):
            passed += 1
        else:
            all_ok = False

    profiles = json.loads((REPO_ROOT / "tools" / "profiles.json").read_text())

    # Synthetic golden gate
    total += 1
    with contextlib.redirect_stdout(io.StringIO()):
        syn_res, syn_ok = run_synthetic_suite(
            profiles["corpora"]["exam2"]["config"],
            update_golden=False,
            check_golden=True,
            check_determinism=False,
        )
    status = "PASS" if syn_ok else "FAIL"
    print(
        f"[GATE] golden:{'synthetic':17s} {status}  "
        f"[synthetic] pages={syn_res.get('rendered_pages')} golden_passed={syn_res.get('golden_passed')} "
        f"layout_golden_passed={syn_res.get('layout_golden_passed')}",
        flush=True,
    )
    if syn_ok:
        passed += 1
    else:
        all_ok = False

    # Corpus & 8-size-series golden gates (in-process, sequential)
    for cname, cprof in profiles["corpora"].items():
        gfile = REPO_ROOT / "tools" / "golden" / f"{cname}.json"
        if not gfile.is_file():
            continue
        total += 1
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res, ok = run_single_corpus(
                cname=cname,
                cprof=cprof,
                search_paths=profiles["search_paths"],
                pages_limit=None,
                update_golden=False,
                check_golden=True,
                check_determinism=False,
                golden_only=True,
            )
        status = "PASS" if ok else "FAIL"
        print(
            f"[GATE] golden:{cname:17s} {status}  "
            f"[{cname}] pages={res['rendered_pages']} golden_passed={res['golden_passed']} "
            f"layout_golden_passed={res.get('layout_golden_passed', True)}",
            flush=True,
        )
        if ok:
            passed += 1
        else:
            all_ok = False

    print(f"SUMMARY: {passed}/{total} gates PASSED" if all_ok else f"SUMMARY: {passed}/{total} gates PASSED (FAILED)", flush=True)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
