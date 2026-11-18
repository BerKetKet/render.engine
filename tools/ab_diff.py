#!/usr/bin/env python3
"""Compare two score_all.py result files (BEFORE vs AFTER). Exit code 1 if any exact page was lost.
Usage: python3 tools/ab_diff.py before.json after.json"""
import json, sys
b, a = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
lost_any = False
print(f"{'dataset':11s} {'exact':>12s} {'diff_px':>26s} {'lost':>5s} {'gained':>6s}  pages with MORE diff than before")
for n in a:
    if n not in b: continue
    rb = {r['p']: r for r in b[n]['rows'] if not r.get('missing')}; ra = {r['p']: r for r in a[n]['rows'] if not r.get('missing')}
    com = sorted(set(rb) & set(ra))
    lost = [p for p in com if rb[p]['exact'] and not ra[p]['exact']]; gain = [p for p in com if not rb[p]['exact'] and ra[p]['exact']]
    worse = [p for p in com if ra[p]['diff'] > rb[p]['diff']]
    eb, ea = sum(r['exact'] for r in rb.values()), sum(r['exact'] for r in ra.values())
    db, da = sum(r['diff'] for r in rb.values()), sum(r['diff'] for r in ra.values())
    lost_any |= bool(lost)
    print(f"{n:11s} {f'{eb}->{ea}/{len(ra)}':>12s} {f'{db:,}->{da:,}':>26s} {len(lost):>5d} {len(gain):>6d}  {worse[:15]}{' …' if len(worse) > 15 else ''}"
          + (f"   LOST EXACT: {lost}" if lost else ""))
sys.exit(1 if lost_any else 0)
