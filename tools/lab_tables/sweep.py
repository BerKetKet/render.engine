"""Grid sweep of experiment env hooks against the 3-theme table score.
usage (repo root): python3 tools/lab_tables/sweep.py KR_CAP=7,7.5,8 KR_PAD=1.3,1.37 [--engine .]
Runs score_tables.py once per grid point (about 2 minutes each), prints one line per point and writes
tools/lab_tables/work/sweep.csv. Do not run several points in parallel on a small machine (memory)."""
import sys, os, itertools, subprocess, re, csv
args = [a for a in sys.argv[1:] if not a.startswith("--")]
eng = "."
for a in sys.argv[1:]:
    if a.startswith("--engine="): eng = a.split("=", 1)[1]
grid = {}
for a in args:
    k, v = a.split("=", 1); grid[k] = v.split(",")
os.makedirs("tools/lab_tables/work", exist_ok=True)
rows = []
for combo in itertools.product(*grid.values()):
    env = dict(os.environ); env.update(dict(zip(grid.keys(), combo)))
    tag = "sw_" + "_".join(combo)
    out = subprocess.run([sys.executable, "tools/lab_tables/score_tables.py", eng, tag], capture_output=True, text=True, env=env).stdout
    tot = re.search(r"TOTAL diff_px ([\d,]+)", out); exact = sum(int(x) for x in re.findall(r"exact (\d+)", out))
    pages = re.findall(r"pages (\d+)/(\d+)", out); ok = all(a == b for a, b in pages)
    t = int(tot.group(1).replace(",", "")) if tot else -1
    rows.append(list(combo) + [t, exact, "pages_ok" if ok else "PAGES_CHANGED"])
    print(dict(zip(grid.keys(), combo)), "total", t, "exact", exact, "pages_ok" if ok else "PAGES_CHANGED", flush=True)
with open("tools/lab_tables/work/sweep.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(list(grid.keys()) + ["total_diff", "exact_pages", "pages"]); w.writerows(rows)
