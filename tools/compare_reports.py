#!/usr/bin/env python3
"""Compares tools/reports/baseline_v161.json and tools/reports/after_refactor.json
side by side and computes `identical: yes/no` across all per-page SHA-256 hashes,
exact page counts, differing pixel totals, positional exact lines, and position-independent exact lines.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main():
    base_p = REPO_ROOT / "tools" / "reports" / "baseline_v161.json"
    after_p = REPO_ROOT / "tools" / "reports" / "after_refactor.json"
    base = json.loads(base_p.read_text())["corpora"]
    after = json.loads(after_p.read_text())["corpora"]

    print(
        f"{'Corpus':8s} | {'Baseline Pages':14s} | {'After Pages':14s} | "
        f"{'Baseline PosLines':17s} | {'After PosLines':17s} | "
        f"{'Baseline PILines':16s} | {'After PILines':16s} | "
        f"{'Baseline DiffPx':15s} | {'After DiffPx':15s} | {'PageSHA==':9s}"
    )
    print("-" * 165)

    all_identical = True
    for cname in ("probe", "exam1", "exam2"):
        b_c = base[cname]
        a_c = after[cname]
        b_tot = b_c["totals"]
        a_tot = a_c["totals"]

        b_pg = f"{b_tot['exact_pages']}/{b_c['compared_pages']}"
        a_pg = f"{a_tot['exact_pages']}/{a_c['compared_pages']}"
        b_pl = f"{b_tot['pos_exact_lines']}/{b_tot['capture_lines']}"
        a_pl = f"{a_tot['pos_exact_lines']}/{a_tot['capture_lines']}"
        b_pi = f"{b_tot['pos_indep_lines']}/{b_tot['capture_lines']}"
        a_pi = f"{a_tot['pos_indep_lines']}/{a_tot['capture_lines']}"
        b_dp = f"{b_tot['diff_pixels']:,d}"
        a_dp = f"{a_tot['diff_pixels']:,d}"

        b_hashes = {k: v["sha256"] for k, v in b_c["pages"].items()}
        a_hashes = {k: v["sha256"] for k, v in a_c["pages"].items()}
        sha_eq = (b_hashes == a_hashes)
        metrics_eq = (b_tot == a_tot and b_c["compared_pages"] == a_c["compared_pages"] and sha_eq)
        if not metrics_eq:
            all_identical = False

        print(
            f"{cname:8s} | {b_pg:14s} | {a_pg:14s} | "
            f"{b_pl:17s} | {a_pl:17s} | "
            f"{b_pi:16s} | {a_pi:16s} | "
            f"{b_dp:>15s} | {a_dp:>15s} | {str(sha_eq):9s}"
        )

    print("-" * 165)
    print(f"identical: {'yes' if all_identical else 'no'}")
    if not all_identical:
        sys.exit(1)


if __name__ == "__main__":
    main()
