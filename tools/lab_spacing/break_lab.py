#!/usr/bin/env python3
"""S2: Fast zero-raster paragraph line-breaking harness for direct LBA optimization (S3).

Validates 100% exact equality against kindle_render.layout.break_kp on default params,
then exposes all cost-model knobs for fast parameter search and leave-one-theme-out validation.
"""
import json, math, os, sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
from kindle_render import Config
from kindle_render.epub import load_epub
from kindle_render.fonts import Family
from kindle_render.layout import Box, Glue, Penalty, TABLE_CONSEC, TABLE_WINDOW, build_items, break_kp, make_lines

GEO = {
    "Standard": (2880, 79, 1001),
    "Compact":  (2496, 39, 1041),
    "Large":    (3200, 131, 949),
}


def break_kp_param(items, line_w, cfg, ragged=False, params=None):
    """Parameterized copy of break_kp exposing every cost/validity knob."""
    p = params or {}
    g_frac = float(p.get("g_frac", 0.0))
    sh_mult = p.get("sh_mult", None)
    str_k = float(p.get("str_k", 2.0))
    sh_k = float(p.get("sh_k", 2.5))
    hyph_k = float(p.get("hyph_k", getattr(cfg, "word_spacing_hyph_k", 1.0) if (getattr(cfg, "word_spacing_step", None) or 1) > 1 else 1.5))
    line_pen = float(p.get("line_pen", 0.0))
    win_lo = float(p.get("win_lo", 0.8))
    win_hi = float(p.get("win_hi", 1.2))
    exp = float(p.get("exp", 2.0))
    max_st = float(p.get("max_st", 0.0))

    n_items = len(items)
    if n_items == 0:
        return []
    if n_items > getattr(cfg, "max_kp_items", 5000):
        return None

    L0 = float(line_w(0))
    L1 = float(line_w(1))
    indent_w = max(0.0, L1 - L0)

    ref_size26 = float(cfg.size26)
    for it in items:
        if isinstance(it, Box) and it.glyphs and it.glyphs[0][0] is not None:
            ref_size26 = float(it.glyphs[0][0].size26)
            break
    std_sp26 = ref_size26 * 0.25

    if sh_mult is None:
        _wstep = getattr(cfg, "word_spacing_step", 1)
        _cstep = getattr(cfg, "char_spacing_step", 1)
        sh_mult = 1.0
        if _wstep > 1:
            _minm = float(getattr(cfg, "word_spacing_shrink_mult", 0.10))
            _decay = float(getattr(cfg, "word_spacing_shrink_decay", 3.27))
            _extra_wem = (_wstep - 1) * float(getattr(cfg, "word_spacing_step_em", 0.22))
            sh_mult = min(sh_mult, max(_minm, 1.0 - _decay * _extra_wem))
        if _cstep > 1:
            sh_mult = min(sh_mult, float(getattr(cfg, "char_spacing_shrink_mult", 0.80)))

    W = [0.0] * (n_items + 1)
    SP = [0.0] * (n_items + 1)
    for idx, it in enumerate(items):
        W[idx + 1] = W[idx]
        SP[idx + 1] = SP[idx]
        if isinstance(it, Box):
            W[idx + 1] += float(it.width)
        elif isinstance(it, Glue):
            W[idx + 1] += float(it.width)
            if not getattr(it, "non_breaking", False):
                if getattr(it, "is_mono", False):
                    SP[idx + 1] += float(it.width)
                else:
                    base_g = min(float(it.width), std_sp26)
                    if g_frac > 0.0 and float(it.width) > std_sp26:
                        SP[idx + 1] += base_g + g_frac * (float(it.width) - std_sp26)
                    else:
                        SP[idx + 1] += base_g

    nodes = []
    for b, it in enumerate(items):
        if isinstance(it, Glue):
            if b == 0 or not isinstance(items[b - 1], Box) or getattr(it, "non_breaking", False):
                continue
            s_next = b + 1
            while s_next < n_items and isinstance(items[s_next], Glue):
                s_next += 1
            hang = 0.0
            if b > 0 and isinstance(items[b - 1], Box) and items[b - 1].glyphs:
                lg = items[b - 1].glyphs[-1]
                if lg[1] in ("period", "comma", "hyphen", "endash", "emdash", "quotedblright", "quoteright"):
                    hang = lg[2] * 0.35
            nodes.append(dict(item_idx=b, e_idx=b, s_next=s_next, is_hyph=False, is_forced=False, hyph_w=0.0, hang=hang))
        elif isinstance(it, Penalty):
            if it.penalty <= -1e8:
                s_next = b + 1
                while s_next < n_items and isinstance(items[s_next], Glue):
                    s_next += 1
                nodes.append(dict(item_idx=b, e_idx=b, s_next=s_next, is_hyph=False, is_forced=True, hyph_w=0.0, hang=0.0))
            elif it.flagged and it.penalty < 1e8:
                s_next = b + 1
                hang = float(it.width) * 0.35 if it.width > 0 else 0.0
                nodes.append(dict(item_idx=b, e_idx=b, s_next=s_next, is_hyph=True, is_forced=False, hyph_w=float(it.width), hang=hang))

    N = len(nodes)
    if N == 0:
        return [n_items]
    if not nodes[-1]["is_forced"]:
        nodes.append(dict(item_idx=n_items, e_idx=n_items, s_next=n_items, is_hyph=False, is_forced=True, hyph_w=0.0, hang=0.0))
        N += 1

    def get_L(start_i):
        return L0 if start_i == 0 else L1

    def get_start_off(start_i):
        return 0.0

    INF_COST = 1e18
    best_cost = [INF_COST] * (N + 1)
    next_break = [-1] * N
    hyph_mask = [0] * (N + 1)
    best_cost[N] = 0.0

    last_node = nodes[N - 1]
    first_invalid = N - 1
    for i in range(N - 1, -1, -1):
        s_idx = 0 if i == 0 else nodes[i - 1]["s_next"]
        w = (W[last_node["e_idx"]] - W[s_idx]) + last_node["hyph_w"]
        if w > get_L(i) + last_node["hang"]:
            first_invalid = i
            break
        best_cost[i] = 0.0
        next_break[i] = N
        if not ragged:
            fill = (w - last_node["hang"]) / get_L(i) if get_L(i) > 0 else 1.0
            if fill < 0.2:
                best_cost[i] = (0.2 - fill) * 4.2
        first_invalid = i - 1

    def compute_line_cost(start_i, end_j):
        nd_e = nodes[end_j]
        s_idx = 0 if start_i == 0 else nodes[start_i - 1]["s_next"]
        e_idx = nd_e["e_idx"]
        w = (W[e_idx] - W[s_idx]) + nd_e["hyph_w"] + get_start_off(start_i)
        G = (SP[e_idx] - SP[s_idx]) + 0.1
        L = get_L(start_i) + nd_e["hang"]
        s9 = best_cost[end_j + 1] if (end_j + 1 < N) else 0.0
        slack = L - w
        if slack < 0.0:
            max_sh = G * (0.099 if ragged else 0.179) * sh_mult
            if (-slack) > max_sh:
                return s9 + 1000000.0, w - nd_e["hang"]
            s0 = (slack / G) * sh_k
        else:
            if not ragged:
                if max_st > 0.0 and slack > G * max_st:
                    return s9 + 1000000.0, w - nd_e["hang"]
                s0 = (slack / G) * str_k
            else:
                s0 = (slack / ref_size26) * 0.61
                if nd_e["is_forced"]:
                    s0 *= 0.01
        cost = s9 + (abs(s0) ** exp) + line_pen
        w8 = hyph_mask[end_j + 1] if (end_j + 1 < N) else 0
        if start_i > 0:
            prev_h = 1 if nodes[start_i - 1]["is_hyph"] else 0
            w8 = ((w8 << 1) | prev_h) & 0xff
        else:
            w8 = w8 & 0xff
        if w8 != 0:
            inv = (~w8) & 0xff
            trail_ones = 8 if inv == 0 else ((inv & -inv).bit_length() - 1)
            pop = bin(w8).count("1")
            c_pen = TABLE_CONSEC[min(trail_ones, 8)] + TABLE_WINDOW[min(pop, 8)]
            cost += hyph_k * c_pen
        return cost, w - nd_e["hang"]

    last_valid_end = N - 1
    for i in range(first_invalid, -1, -1):
        if last_valid_end < i:
            last_valid_end = i
        best_c = INF_COST
        best_j = -1
        L_base = get_L(i)
        d10 = L_base * win_lo
        d11 = L_base * win_hi
        j = last_valid_end
        while j >= i:
            tot_c, w_line = compute_line_cost(i, j)
            if w_line > d11:
                last_valid_end = j - 1
            if tot_c < best_c:
                best_c = tot_c
                best_j = j
            elif w_line < d10:
                break
            j -= 1
        if best_j != -1 and best_c < 1000000.0:
            best_cost[i] = best_c
            next_break[i] = best_j + 1
            prev_m = hyph_mask[best_j + 1] if (best_j + 1 < N) else 0
            if i > 0:
                prev_h = 1 if nodes[i - 1]["is_hyph"] else 0
                hyph_mask[i] = ((prev_m << 1) | prev_h) & 0xff
            else:
                hyph_mask[i] = prev_m
        else:
            # fallback: pick tightest legal break >= i
            best_cost[i] = (best_cost[i + 1] if i + 1 < N else 0.0) + 1000000.0
            next_break[i] = i + 1

    breaks = []
    cur = 0
    while 0 <= cur < N:
        nb = next_break[cur]
        if nb <= cur:
            break
        breaks.append(nodes[nb - 1]["item_idx"])
        cur = nb
    if not breaks or breaks[-1] != n_items:
        breaks.append(n_items)
    return breaks


def validate_against_engine():
    """Assert break_kp_param matches kindle_render.layout.break_kp on Victorian paragraphs."""
    cfg = Config(size26=2880, x0=79, right=1001, line_spacing_step=1, word_spacing_step=1)
    fam = Family(cfg)
    blks = load_epub("exam/v2/kindle_exam_v2.epub", cfg)
    L = (1001 - 79) * 64
    ind = int(round(cfg.default_indent_em * 45 * 64))
    checked = 0; exact = 0
    for b in blks[19:27]:
        if b.kind == "text" and b.heading == 0 and b.runs:
            its = build_items(b.runs, fam, cfg, 2880, False, allow_hyphenation=True, lang="en")
            lw = lambda i: L - (ind if i == 0 else 0)
            b_eng = break_kp(its, lw, 4.0, cfg, False)
            b_lab = break_kp_param(its, lw, cfg, False, {})
            checked += 1
            if b_eng == b_lab:
                exact += 1
    print(f"[S2 break_lab validation] checked={checked} exact={exact}/{checked}")
    return exact == checked


if __name__ == "__main__":
    validate_against_engine()
