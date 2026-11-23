#!/usr/bin/env python3
"""Align device spacing capture lines with kindle_render item widths to learn the device line-acceptance region.

Outputs docs/data/spacing_acceptance_region.json with raw (r_acc, r_rej) pairs and per-(var, theme, step) summaries.
"""
import json, math, os, statistics, sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, os.getcwd())
from kindle_render import Config
from kindle_render.epub import load_epub
from kindle_render.fonts import Family
from kindle_render.layout import Box, Glue, Penalty, build_items

GEO = {
    "Standard": (2880, 79, 1001),
    "Compact":  (2496, 39, 1041),
    "Large":    (3200, 131, 949),
}


def find_text_bands(arr, y0=120, y1=2220):
    ink = (arr[y0:y1] < 200).any(axis=1)
    bands, in_b, s = [], False, 0
    for i, v in enumerate(ink):
        if v and not in_b:
            s = i; in_b = True
        elif not v and in_b:
            bands.append((y0 + s, y0 + i - 1)); in_b = False
    if in_b:
        bands.append((y0 + s, y1 - 1))
    return bands


def measure_capture_lines(cap_png, x0, right, size_px):
    """Return list of dicts for body lines on a capture page: y0, y1, lx, rx, indented, is_justified, gap_widths."""
    arr = np.asarray(Image.open(cap_png).convert("L"))
    bands = find_text_bands(arr)
    out = []
    for b0, b1 in bands:
        h = b1 - b0 + 1
        if h < int(size_px * 0.45) or h > int(size_px * 1.35):
            continue  # skip headings (>1.5x) and underlines (<0.4x)
        sub = arr[b0:b1 + 1, :]
        col_ink = (sub < 200).any(axis=0)
        xs = np.where(col_ink)[0]
        if len(xs) == 0:
            continue
        lx, rx = int(xs[0]), int(xs[-1])
        # Measure white runs (inter-word gaps) between lx and rx
        gaps = []
        in_gap, gs = False, 0
        for x in range(lx, rx + 1):
            if not col_ink[x] and not in_gap:
                gs = x; in_gap = True
            elif col_ink[x] and in_gap:
                gw = x - gs
                if gw >= 4:
                    gaps.append(gw)
                in_gap = False
        out.append(dict(
            y0=b0, y1=b1, lx=lx, rx=rx,
            indented=(lx - x0) > int(size_px * 0.8),
            is_justified=(right - rx) <= 22,
            gaps=gaps,
        ))
    return out


def align_paragraph_to_capture(items, cap_lines, L_px, indent_px, base_sp_px, actual_sp_px):
    """Infer device line breaks by matching each capture line's justified/ragged extent & word-gap count against item stream."""
    # Build word-level tokens (groups of Boxes separated by Glues)
    words = []
    cur_w = 0.0
    cur_hy_pts = []  # (prefix_w_with_hyph, suffix_w)
    cur_boxes = []
    for it in items:
        if isinstance(it, Box):
            cur_boxes.append(it)
            cur_w += it.width / 64.0
        elif isinstance(it, Penalty) and it.flagged and it.width > 0:
            cur_hy_pts.append((cur_w + it.width / 64.0, cur_w))
        elif isinstance(it, Glue) and not getattr(it, "non_breaking", False):
            if cur_boxes:
                words.append(dict(w=cur_w, sp=it.width / 64.0, hy=cur_hy_pts))
                cur_w = 0.0; cur_hy_pts = []; cur_boxes = []
    if cur_boxes:
        words.append(dict(w=cur_w, sp=0.0, hy=cur_hy_pts))

    # For each capture line (except last ragged line), find best break index i where natural width is closest to L
    pairs = []
    wi = 0
    for li, cl in enumerate(cap_lines):
        if wi >= len(words):
            break
        line_L = L_px - (indent_px if (li == 0 and cl["indented"]) else 0.0)
        if not cl["is_justified"]:
            # Ragged line (paragraph end): advance until natural width matches (rx - lx)
            target = cl["rx"] - cl["lx"]
            acc = 0.0; best_k = wi; best_err = 1e9
            for k in range(wi, len(words)):
                acc += words[k]["w"] + (words[k - 1]["sp"] if k > wi else 0.0)
                if abs(acc - target) < best_err:
                    best_err = abs(acc - target); best_k = k
                if acc > target + 120:
                    break
            wi = best_k + 1
            continue

        # Justified line: estimate number of words from capture inter-word gaps (filtering out small tracking gaps)
        # Try every candidate break k (whole word or hyphenated) and score by closeness to capture gap count + tightest fit
        cand = []
        acc_w = 0.0
        for k in range(wi, len(words)):
            if k > wi:
                acc_w += words[k - 1]["sp"]
            # Check hyphenation points inside words[k]
            for hy_w, raw_pre in words[k]["hy"]:
                w_tot = acc_w + hy_w
                n_g = k - wi
                if n_g >= 1 and 0.45 * line_L <= w_tot <= 1.12 * line_L:
                    r = (line_L - w_tot) / n_g
                    cand.append((abs(r), k, True, w_tot, n_g, r))
            acc_w += words[k]["w"]
            n_g = k - wi
            if n_g >= 1 and 0.45 * line_L <= acc_w <= 1.12 * line_L:
                r = (line_L - acc_w) / n_g
                cand.append((abs(r), k, False, acc_w, n_g, r))
            if acc_w > 1.25 * line_L:
                break
        if not cand:
            wi += 1
            continue
        # Match against capture median gap: capture actual average space ~= (line_L - sum_word_w) / n_g
        # Pick candidate whose implied space width (actual_sp_px + r) best matches capture's large gaps median
        big_gaps = [g for g in cl["gaps"] if g >= max(6, int(actual_sp_px * 0.55))]
        if big_gaps:
            cap_med = statistics.median(big_gaps)
            # In capture, ink gap ~= space_advance + ~2px sidebearings
            best = min(cand, key=lambda c: abs((actual_sp_px + c[5]) - cap_med) + 0.15 * abs(c[4] - len(big_gaps)))
        else:
            best = min(cand, key=lambda c: c[0])
        _, bk, is_hy, w_acc, n_g, r_acc = best
        # Compute rejected continuation (next word or next hyphen fragment)
        r_rej = None
        if not is_hy and bk + 1 < len(words):
            w_next = w_acc + words[bk]["sp"] + words[bk + 1]["w"]
            r_rej = (line_L - w_next) / (n_g + 1)
        elif is_hy:
            w_full = w_acc - words[bk]["hy"][0][0] + words[bk]["w"]
            r_rej = (line_L - w_full) / max(1, n_g)
        pairs.append(dict(
            line_idx=li, n_glue=n_g, is_hyph=is_hy,
            r_acc=round(r_acc, 2), r_rej=round(r_rej, 2) if r_rej is not None else None,
            r_acc_norm_base=round(r_acc / base_sp_px, 4),
            r_acc_norm_act=round(r_acc / actual_sp_px, 4),
            r_rej_norm_base=round(r_rej / base_sp_px, 4) if r_rej is not None else None,
            r_rej_norm_act=round(r_rej / actual_sp_px, 4) if r_rej is not None else None,
        ))
        wi = bk + (0 if is_hy else 1)
    return pairs


def main():
    cap_root = Path("data/spacing_caps")
    epub = "exam/v2/kindle_exam_v2.epub"
    out = {"summary": {}, "pairs": {}}

    for th, (s26, x0, right) in GEO.items():
        sz = s26 / 64.0
        L_px = float(right - x0)
        base_sp = 0.25 * sz
        for var in ("word", "char"):
            for step in range(1, 6):
                kw = dict(size26=s26, x0=x0, right=right, top=168, page_bottom=2203, line_spacing_step=1)
                kw[f"{var}_spacing_step"] = step
                cfg = Config(**kw)
                fam = Family(cfg)
                blocks = load_epub(epub, cfg)
                # Find first Victorian body paragraph (blk 20: "It was the unanimous opinion...")
                para_blks = [b for b in blocks if b.kind == "text" and b.heading == 0 and b.runs and "unanimous opinion" in "".join(r.text for r in b.runs)]
                if not para_blks:
                    continue
                b0 = para_blks[0]
                items = build_items(b0.runs, fam, cfg, s26, False, allow_hyphenation=True, lang="en")
                # Measure capture page 3 body lines (after heading)
                cap_p3 = cap_root / th / f"theme_{th}" / f"{var}_step_{step}_of_5" / "page_003.png"
                cap_lines = measure_capture_lines(cap_p3, x0, right, sz)
                # Filter to first paragraph (stops at first indented line after line 0)
                p0_lines = []
                for idx, cl in enumerate(cap_lines):
                    if idx > 0 and cl["indented"]:
                        break
                    p0_lines.append(cl)
                actual_sp = base_sp + (cfg.user_word_spacing_26() + cfg.user_char_spacing_26()) / 64.0
                pairs = align_paragraph_to_capture(items, p0_lines, L_px, cfg.default_indent_em * sz, base_sp, actual_sp)
                key = f"{th}.{var}{step}"
                out["pairs"][key] = pairs
                accs = [p["r_acc"] for p in pairs]
                rejs = [p["r_rej"] for p in pairs if p["r_rej"] is not None]
                sh_accs = [p["r_acc"] for p in pairs if p["r_acc"] < 0]
                st_accs = [p["r_acc"] for p in pairs if p["r_acc"] >= 0]
                out["summary"][key] = dict(
                    n_lines=len(pairs),
                    max_stretch_px=max(st_accs) if st_accs else 0.0,
                    max_shrink_px=min(sh_accs) if sh_accs else 0.0,
                    min_rej_px=max(rejs) if rejs else None,
                    max_shrink_base=round((min(sh_accs) / base_sp), 3) if sh_accs else 0.0,
                    max_stretch_base=round((max(st_accs) / base_sp), 3) if st_accs else 0.0,
                    max_stretch_act=round((max(st_accs) / actual_sp), 3) if st_accs else 0.0,
                )
                s = out["summary"][key]
                print(f"{key:16s} n={s['n_lines']:2d} max_sh={s['max_shrink_px']:6.2f}px ({s['max_shrink_base']:+.3f}*sp0) max_st={s['max_stretch_px']:6.2f}px ({s['max_stretch_act']:+.3f}*sp) min_rej={str(s['min_rej_px']):>7s}", flush=True)

    os.makedirs("docs/data", exist_ok=True)
    json.dump(out, open("docs/data/spacing_acceptance_region.json", "w"), indent=1)
    print("Wrote docs/data/spacing_acceptance_region.json")


if __name__ == "__main__":
    main()
