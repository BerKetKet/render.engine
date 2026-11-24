#!/usr/bin/env python3
"""S1: Recover device line breaks per paragraph from spacing captures -> docs/data/device_lines.jsonl.

Also computes baseline LBA (line-break agreement) and PAG (page-boundary agreement) for the current engine.
"""
import json, os, statistics, sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, os.getcwd())
from kindle_render import Config, render_to_ir
from kindle_render.epub import load_epub
from kindle_render.fonts import Family
from kindle_render.layout import Box, Glue, Penalty, build_items, make_lines

GEO = {
    "Standard": (2880, 79, 1001),
    "Compact":  (2496, 39, 1041),
    "Large":    (3200, 131, 949),
}


def extract_body_lines(png_path, x0, right, sz):
    """Extract body-text ink lines with lx, rx, indented, justified, trailing_hyphen, and large-gap count."""
    arr = np.asarray(Image.open(png_path).convert("L"))
    y0, y1 = 150, 2210
    ink_row = (arr[y0:y1] < 160).any(axis=1)
    bands, in_b, s = [], False, 0
    for i, v in enumerate(ink_row):
        if v and not in_b:
            s = i; in_b = True
        elif not v and in_b:
            bands.append((y0 + s, y0 + i - 1)); in_b = False
    if in_b:
        bands.append((y0 + s, y1 - 1))

    lines = []
    for b0, b1 in bands:
        h = b1 - b0 + 1
        if h < int(sz * 0.45) or h > int(sz * 1.30):
            continue
        sub = arr[b0:b1 + 1, :]
        col_ink = (sub < 160).any(axis=0)
        xs = np.where(col_ink)[0]
        if len(xs) == 0:
            continue
        lx, rx = int(xs[0]), int(xs[-1])
        # Check rightmost ink blob for hyphen shape: narrow (<0.42*sz) and short vertically (<0.26*sz)
        # Find start of rightmost contiguous ink run
        r_start = rx
        while r_start > lx and col_ink[r_start - 1]:
            r_start -= 1
        blob_w = rx - r_start + 1
        blob_rows = np.where((sub[:, r_start:rx + 1] < 160).any(axis=1))[0]
        blob_h = (int(blob_rows[-1]) - int(blob_rows[0]) + 1) if len(blob_rows) else h
        # Hyphen sits in middle vertical region and is wider than tall (or very short)
        is_hyph = (3 <= blob_w <= int(sz * 0.45)) and (blob_h <= int(sz * 0.22)) and (len(blob_rows) > 0 and blob_rows[0] > int(h * 0.25))
        # White gaps
        gaps = []
        in_g, gs = False, 0
        for x in range(lx, rx + 1):
            if not col_ink[x] and not in_g:
                gs = x; in_g = True
            elif col_ink[x] and in_g:
                if x - gs >= 4:
                    gaps.append(x - gs)
                in_g = False
        lines.append(dict(
            y0=b0, y1=b1, lx=lx, rx=rx,
            indented=(lx - x0) > int(sz * 0.8),
            justified=(right - rx) <= 22,
            hyphenated=bool(is_hyph),
            gaps=gaps,
        ))
    return lines


def items_to_tokens(items):
    """Flatten items into a list of candidate break points: (tok_idx, word_idx, hyph_idx, is_hyph, w_cum, n_glue_cum)."""
    # Group into words with their hyphenation sub-boxes
    words = []
    cur_boxes = []
    cur_hy = []
    cur_w = 0.0
    for it in items:
        if isinstance(it, Box):
            cur_boxes.append(it)
            cur_w += it.width / 64.0
        elif isinstance(it, Penalty) and it.flagged and it.width > 0:
            cur_hy.append((cur_w, it.width / 64.0))
        elif isinstance(it, Glue) and not getattr(it, "non_breaking", False):
            if cur_boxes:
                words.append(dict(w=cur_w, sp=it.width / 64.0, hy=cur_hy))
                cur_boxes, cur_hy, cur_w = [], [], 0.0
    if cur_boxes:
        words.append(dict(w=cur_w, sp=0.0, hy=cur_hy))
    return words


def align_book_pages(cap_dir, th, var, step, cfg, fam, blocks):
    """Align capture pages 3..5 (X01 Victorian chapter) against paragraph item streams."""
    sz = cfg.size_px()
    L_px = float(cfg.right - cfg.x0)
    indent_px = cfg.default_indent_em * sz
    base_sp = 0.25 * sz
    actual_sp = base_sp + (cfg.user_word_spacing_26() + cfg.user_char_spacing_26()) / 64.0

    # Victorian chapter body paragraphs (from "It was the unanimous opinion..." onward)
    start_idx = next(i for i, b in enumerate(blocks) if b.kind == "text" and b.runs and "unanimous opinion" in "".join(r.text for r in b.runs))
    paras = []
    for bi in range(start_idx, len(blocks)):
        b = blocks[bi]
        if b.heading > 0:
            break
        if b.kind == "text" and b.runs:
            its = build_items(b.runs, fam, cfg, cfg.size26, False, allow_hyphenation=True, lang="en")
            paras.append((bi, b, its, items_to_tokens(its)))

    # Collect capture lines from pages 3..5 in order (skipping pages before X01 starts)
    cap_seq = []
    for pg in (3, 4, 5):
        p_path = f"{cap_dir}/{th}/theme_{th}/{var}_step_{step}_of_5/page_{pg:03d}.png"
        if not os.path.exists(p_path):
            continue
        cls = extract_body_lines(p_path, cfg.x0, cfg.right, sz)
        # Skip TOC pages (lines that start with "1.".. indented and short)
        if pg == 3 and cls and all((not c["justified"] and c["rx"] < cfg.right - 250) for c in cls[:3]):
            continue
        for cl in cls:
            cap_seq.append((pg, cl))

    # Group capture lines into paragraphs by indented flag (first paragraph is NOT indented)
    cap_paras = []
    cur_p = []
    for pg, cl in cap_seq:
        if cur_p and cl["indented"]:
            cap_paras.append(cur_p)
            cur_p = [(pg, cl)]
        else:
            cur_p.append((pg, cl))
    if cur_p:
        cap_paras.append(cur_p)

    # Align each capture paragraph against corresponding EPUB paragraph
    records = []
    for pi in range(min(len(cap_paras), len(paras))):
        bi, b, its, words = paras[pi]
        c_lines = cap_paras[pi]
        wi = 0
        rem_w = 0.0  # leftover suffix width if previous line hyphenated
        prev_hy_idx = -1
        for li, (pg, cl) in enumerate(c_lines):
            if wi >= len(words):
                break
            line_L = L_px - (indent_px if (li == 0 and cl["indented"]) else 0.0)
            first_w = wi
            if not cl["justified"]:
                target = cl["rx"] - cl["lx"]
                acc = rem_w
                best_k, best_err = wi, 1e9
                start_k = wi + (1 if rem_w > 0 else 0)
                if rem_w > 0:
                    best_err = abs(acc - target)
                for k in range(start_k, len(words)):
                    if k > wi or rem_w > 0:
                        acc += words[k - 1]["sp"]
                    acc += words[k]["w"]
                    if abs(acc - target) < best_err:
                        best_err = abs(acc - target); best_k = k
                    if acc > target + 150:
                        break
                records.append(dict(
                    corpus="spacing_exam", theme=th, variable=var, step=step, page=pg,
                    para_id=bi, line_idx=li, first_word_idx=first_w, last_word_idx=best_k,
                    hyphenated=False, hyphen_point=-1, justified=False,
                    gap_px_median=round(statistics.median(cl["gaps"]), 1) if cl["gaps"] else 0.0,
                    ink_x0=cl["lx"], ink_x1=cl["rx"],
                ))
                wi = best_k + 1; rem_w = 0.0; prev_hy_idx = -1
                continue

            # Justified line: enumerate candidate breaks (whole word or hyphenated)
            cands = []
            acc = rem_w
            start_k = wi + (1 if rem_w > 0 else 0)
            n_g_base = 1 if rem_w > 0 else 0
            big_gaps = [g for g in cl["gaps"] if g >= max(5, int(actual_sp * 0.50))]
            cap_med = statistics.median(big_gaps) if big_gaps else actual_sp
            for k in range(start_k, len(words)):
                if k > wi or rem_w > 0:
                    acc += words[k - 1]["sp"]
                n_g = (k - wi)
                # Hyphen candidates inside words[k]
                for hi, (pre_w, hy_w) in enumerate(words[k]["hy"]):
                    w_tot = acc + pre_w + hy_w
                    if 0.45 * line_L <= w_tot <= 1.15 * line_L and n_g >= 1:
                        r = (line_L - w_tot) / n_g
                        # Score: match median gap + strong bonus if hyphenated flag matches capture!
                        sc = abs((actual_sp + r) - cap_med) + 2.0 * abs(n_g - len(big_gaps)) + (0.0 if cl["hyphenated"] else 25.0)
                        cands.append((sc, k, True, hi, words[k]["w"] - pre_w))
                acc += words[k]["w"]
                if 0.45 * line_L <= acc <= 1.15 * line_L and n_g >= 1:
                    r = (line_L - acc) / n_g
                    sc = abs((actual_sp + r) - cap_med) + 2.0 * abs(n_g - len(big_gaps)) + (25.0 if cl["hyphenated"] else 0.0)
                    cands.append((sc, k, False, -1, 0.0))
                if acc > 1.25 * line_L:
                    break
            if not cands:
                wi += 1; rem_w = 0.0
                continue
            _, bk, is_hy, hi, next_rem = min(cands, key=lambda x: x[0])
            records.append(dict(
                corpus="spacing_exam", theme=th, variable=var, step=step, page=pg,
                para_id=bi, line_idx=li, first_word_idx=first_w, last_word_idx=bk,
                hyphenated=is_hy, hyphen_point=hi, justified=True,
                gap_px_median=round(cap_med, 1),
                ink_x0=cl["lx"], ink_x1=cl["rx"],
            ))
            if is_hy:
                wi = bk; rem_w = next_rem; prev_hy_idx = hi
            else:
                wi = bk + 1; rem_w = 0.0; prev_hy_idx = -1
    return records


def engine_para_breaks(its, line_w_fn, cfg):
    """Return list of (last_word_idx, hyphenated, hyphen_point) for each line of a paragraph."""
    lines = make_lines(its, line_w_fn, cfg, False)
    out = []
    # Map each Box/Penalty object id to (word_idx, hyph_idx)
    w_idx = 0; h_idx = 0
    box_w = {}; pen_h = {}
    for it in its:
        if isinstance(it, Box):
            box_w[id(it)] = w_idx
        elif isinstance(it, Penalty) and it.flagged and it.width > 0:
            pen_h[id(it)] = (w_idx, h_idx)
            h_idx += 1
        elif isinstance(it, Glue) and not getattr(it, "non_breaking", False):
            w_idx += 1; h_idx = 0
    for seg, hy in lines:
        if hy is not None and id(hy) in pen_h:
            wi, hi = pen_h[id(hy)]
            out.append((wi, True, hi))
        else:
            last_w = max((box_w[id(it)] for it in seg if isinstance(it, Box) and id(it) in box_w), default=0)
            out.append((last_w, False, -1))
    return out


def main():
    cap_dir = "data/spacing_caps"
    epub = "exam/v2/kindle_exam_v2.epub"
    all_recs = []
    lba_summary = {}

    for th, (s26, x0, right) in GEO.items():
        base_cfg = Config(size26=s26, x0=x0, right=right, top=168, page_bottom=2203, line_spacing_step=1)
        blocks = load_epub(epub, base_cfg)
        fam = Family(base_cfg)
        for var in ("word", "char"):
            for step in range(1, 6):
                kw = dict(size26=s26, x0=x0, right=right, top=168, page_bottom=2203, line_spacing_step=1)
                kw[f"{var}_spacing_step"] = step
                cfg = Config(**kw)
                recs = align_book_pages(cap_dir, th, var, step, cfg, fam, blocks)
                all_recs.extend(recs)
                # Compute LBA vs current engine
                by_p = {}
                for r in recs:
                    by_p.setdefault(r["para_id"], []).append(r)
                n_lines_tot = 0; n_lines_hit = 0
                n_paras_tot = 0; n_paras_hit = 0
                L = (right - x0) * 64
                ind = int(round(cfg.default_indent_em * cfg.size_px() * 64))
                for pid, precs in by_p.items():
                    b = blocks[pid]
                    its = build_items(b.runs, fam, cfg, s26, False, allow_hyphenation=True, lang="en")
                    has_ind = precs[0]["ink_x0"] - x0 > int(cfg.size_px() * 0.8)
                    eng_br = engine_para_breaks(its, lambda i, hi=has_ind: L - (ind if (i == 0 and hi) else 0), cfg)
                    dev_br = [(r["last_word_idx"], r["hyphenated"], r["hyphen_point"]) for r in precs]
                    # Compare up to min length (excluding last truncated line if page ended mid-para)
                    m = min(len(dev_br), len(eng_br))
                    if m < 2:
                        continue
                    hits = sum(1 for i in range(m) if dev_br[i] == eng_br[i])
                    n_lines_tot += m; n_lines_hit += hits
                    n_paras_tot += 1
                    if hits == m:
                        n_paras_hit += 1
                key = f"{th}.{var}{step}"
                lba = (n_lines_hit / n_lines_tot) if n_lines_tot else 0.0
                lba_summary[key] = dict(lba=round(lba, 4), hits=n_lines_hit, total=n_lines_tot, para_exact=n_paras_hit, paras=n_paras_tot)
                print(f"{key:15s}: LBA={lba*100:5.1f}% ({n_lines_hit:2d}/{n_lines_tot:2d}) para_exact={n_paras_hit}/{n_paras_tot}", flush=True)

    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/device_lines.jsonl", "w") as f:
        for r in all_recs:
            f.write(json.dumps(r) + "\n")
    json.dump(lba_summary, open("docs/data/lba_baseline_1_11_18.json", "w"), indent=1)
    print(f"Wrote docs/data/device_lines.jsonl ({len(all_recs)} lines) and lba_baseline_1_11_18.json")


if __name__ == "__main__":
    main()
