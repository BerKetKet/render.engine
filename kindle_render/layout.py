"""Paragraph layout: items -> line breaks (Knuth-Plass, balanced ragged DP, or greedy) -> justified lines.
Implements:
1. Unified standard slot_offset=2 Liang hyphenation trie (EN/DE/FR) with French elision prefix handling
2. Knuth-Plass dynamic programming across both justified and ragged text, plus balanced ragged DP for headings/centered blocks
3. Whole-word shaping across explicit soft hyphens (\u00ad), hard hyphens, URL slashes, and post-punctuation ellipses (\u2026)
4. Contiguous small-caps shaping, Arabic contextual joining, Devanagari GSUB shaping, and BiDi segment isolation
"""
import math
import re
from dataclasses import dataclass
from typing import List, Tuple, Optional

INF = float('inf')

RIGHT_HANGING_GLYPHS = {
    'period', 'comma', 'semicolon', 'colon', 'hyphen',
    'quotedbl', 'quotesingle', 'quoteright', 'quotedblright',
    'emdash', 'endash'
}

LEFT_HANGING_GLYPHS = {
    'quotedbl', 'quotesingle', 'quoteleft', 'quotedblleft'
}

@dataclass
class Box:
    glyphs: list
    width: int
    inline_image: object = None
    word_idx: int = -1
    direction: str = "ltr"

@dataclass
class Glue:
    width: int
    stretch: float
    shrink: float
    non_breaking: bool = False
    style_meta: dict = None
    is_mono: bool = False

@dataclass
class Penalty:
    width: int
    penalty: float
    flagged: bool = False
    glyphs: list = None

@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    image: object = None
    scale: float = 1.0
    baseline_shift_em: float = 0.0
    small_caps: bool = False
    underline: bool = False
    strike: bool = False
    code: bool = False
    letter_spacing_em: float = 0.0
    word_spacing_em: float = 0.0
    fg: Optional[Tuple[int, int, int]] = None
    bg: Optional[Tuple[int, int, int]] = None
    nowrap: bool = False
    from_text_transform: bool = False
    link_href: Optional[str] = None


def _make_g_meta(base_meta, ctxt: str, direction: str = "ltr", l_char_idx: int = 0, is_lig: bool = False, is_synth_hy: bool = False, dx_px: int = 0, dy_px_override: Optional[int] = None):
    m = dict(base_meta) if base_meta else {
        "dy_px": 0,
        "underline": False,
        "strike": False,
        "fg": None,
        "bg": None,
        "link_href": None,
    }
    if dx_px != 0:
        m["dx_px"] = m.get("dx_px", 0) + dx_px
    if dy_px_override is not None:
        m["dy_px"] = dy_px_override
    m["cluster_text"] = ctxt
    m["direction"] = direction
    m["logical_char_idx"] = l_char_idx
    m["is_ligature"] = is_lig
    m["is_synthetic_hyphen"] = is_synth_hy
    return m


def _shape_token_with_fallbacks(tok: str, face, family, run: Run, size26: int, display: bool, extra_track26: int = 0):
    from .fonts import PRECOMPOSED_LIGATURES
    for k, v in PRECOMPOSED_LIGATURES.items():
        if k in tok:
            tok = tok.replace(k, v)

    style_meta = dict(
        dy_px=int(round(run.baseline_shift_em * (size26 / 64.0))),
        underline=run.underline,
        strike=run.strike,
        fg=run.fg,
        bg=getattr(run, "bg", None),
        link_href=getattr(run, "link_href", None),
    )

    if run.small_caps:
        out = []
        sc_face = family.face(run.bold, run.italic, int(round(size26 * 0.70)), display)
        i, n_len = 0, len(tok)
        c_idx = 0
        while i < n_len:
            is_low = tok[i].islower()
            j = i + 1
            while j < n_len and tok[j].islower() == is_low:
                j += 1
            sub = tok[i:j]
            use_f = sc_face if is_low else face
            sh = use_f.shape_with_clusters(sub.upper() if is_low else sub, extra_track26=extra_track26)
            pos_sub = 0
            for n, a, ctxt_up in sh:
                orig_ctxt = sub[pos_sub:pos_sub + len(ctxt_up)] if is_low else ctxt_up
                pos_sub += len(ctxt_up)
                is_lig = (len(orig_ctxt) > 1 or n in ("uniFB00", "uniFB01", "uniFB02", "uniFB03", "uniFB04", "uniFB05", "uniFB06"))
                gm = _make_g_meta(style_meta, orig_ctxt, "ltr", c_idx, is_lig=is_lig)
                out.append((use_f, n, a, gm))
                c_idx += 1
            i = j
        return out

    needs_fallback = any(ord(c) > 0x024F and ord(c) not in face.cmap for c in tok)
    if not needs_fallback:
        sh = face.shape_with_clusters(tok, extra_track26=extra_track26)
        out = []
        for c_idx, (n, a, ctxt) in enumerate(sh):
            is_lig = (len(ctxt) > 1 or n in ("uniFB00", "uniFB01", "uniFB02", "uniFB03", "uniFB04", "uniFB05", "uniFB06"))
            gm = _make_g_meta(style_meta, ctxt, "ltr", c_idx, is_lig=is_lig)
            out.append((face, n, a, gm))
        return out

    # Arabic shaping (U+0600..U+06FF)
    if any(0x0600 <= ord(c) <= 0x06FF for c in tok):
        ar_face = family.special_face('arabic', size26)
        trail = ""
        core = tok
        if core and core[-1] in ",!?:;\u061f\u060c\u061b":
            trail = core[-1]
            core = core[:-1]
        g_tuples = ar_face.shape_arabic_word_with_clusters(core)
        g_names = [gt[0] for gt in g_tuples]
        out = []
        if trail:
            use_tf = face if ord(trail) in face.cmap else ar_face
            tn = use_tf.cmap.get(ord(trail), '.notdef')
            ta = use_tf.adv26(tn) + extra_track26
            gm = _make_g_meta(style_meta, trail, "rtl", len(core))
            out.append((use_tf, tn, ta, gm))
        for i_g, (gn, ctxt, l_idx) in enumerate(g_tuples):
            adv = ar_face.adv26(gn)
            if ar_face.use_kern and i_g + 1 < len(g_names):
                adv += math.floor(ar_face.kern_units(gn, g_names[i_g + 1]) * ar_face.S)
            adv += extra_track26
            gm = _make_g_meta(style_meta, ctxt, "rtl", l_idx, is_lig=(len(ctxt) > 1))
            out.append((ar_face, gn, adv, gm))
        return out

    # Hebrew shaping (U+0590..U+05FF)
    if any(0x0590 <= ord(c) <= 0x05FF for c in tok):
        hb_face = family.special_face('hebrew', size26)
        trail = ""
        core = tok
        if core and core[-1] in ",!?:;":
            trail = core[-1]
            core = core[:-1]
        out = []
        if trail:
            cp = ord(trail)
            use_f = hb_face if cp in hb_face.cmap else face
            n = use_f.cmap.get(cp, '.notdef')
            a = use_f.adv26(n) + extra_track26
            gm = _make_g_meta(style_meta, trail, "rtl", len(core))
            out.append((use_f, n, a, gm))
        for rev_i, ch in enumerate(core[::-1]):
            l_idx = len(core) - 1 - rev_i
            cp = ord(ch)
            use_f = hb_face if cp in hb_face.cmap else face
            n = use_f.cmap.get(cp, '.notdef')
            a = use_f.adv26(n) + extra_track26
            gm = _make_g_meta(style_meta, ch, "rtl", l_idx)
            out.append((use_f, n, a, gm))
        return out

    # Thai shaping (U+0E00..U+0E7F) via native HarfBuzz
    if any(0x0E00 <= ord(c) <= 0x0E7F for c in tok):
        th_face = family.special_face('thai', size26)
        hb_items = th_face.shape_devanagari_word_with_clusters(tok)
        out = []
        for c_idx, (gn, x_adv26, x_off_px, y_off_px, ctxt) in enumerate(hb_items):
            a = x_adv26 + extra_track26
            dy_ov = style_meta["dy_px"] - y_off_px if (x_off_px != 0 or y_off_px != 0) else None
            gm = _make_g_meta(style_meta, ctxt, "ltr", c_idx, is_lig=(len(ctxt) > 1), dx_px=x_off_px, dy_px_override=dy_ov)
            out.append((th_face, gn, a, gm))
        return out

    # Devanagari shaping (U+0900..U+097F) via native HarfBuzz
    if any(0x0900 <= ord(c) <= 0x097F for c in tok):
        dv_face = family.special_face('devanagari', size26)
        hb_items = dv_face.shape_devanagari_word_with_clusters(tok)
        out = []
        for c_idx, (gn, x_adv26, x_off_px, y_off_px, ctxt) in enumerate(hb_items):
            a = x_adv26 + extra_track26
            dy_ov = style_meta["dy_px"] - y_off_px if (x_off_px != 0 or y_off_px != 0) else None
            gm = _make_g_meta(style_meta, ctxt, "ltr", c_idx, is_lig=(len(ctxt) > 1), dx_px=x_off_px, dy_px_override=dy_ov)
            out.append((dv_face, gn, a, gm))
        return out

    # Ethiopic shaping (U+1200..U+137F)
    if any(0x1200 <= ord(c) <= 0x137F for c in tok):
        et_face = family.special_face('ethiopic', size26)
        sh = et_face.shape_with_clusters(tok, extra_track26=extra_track26)
        return [(et_face, n, a, _make_g_meta(style_meta, ctxt, "ltr", c_idx)) for c_idx, (n, a, ctxt) in enumerate(sh)]

    # CJK & Hangul shaping (U+3000..U+9FFF, U+AC00..U+D7AF, U+FF00..U+FFEF) via native HarfBuzz (GPOS halt/kern/chws)
    if any(0x3000 <= ord(c) <= 0x9FFF or 0xAC00 <= ord(c) <= 0xD7AF or 0xFF00 <= ord(c) <= 0xFFEF for c in tok):
        cjk_face = family.special_face('cjk', size26)
        hb_items = cjk_face.shape_devanagari_word_with_clusters(tok)
        out = []
        for c_idx, (gn, x_adv26, x_off_px, y_off_px, ctxt) in enumerate(hb_items):
            a = x_adv26 + extra_track26
            dy_ov = style_meta["dy_px"] + 1 - y_off_px
            gm = _make_g_meta(style_meta, ctxt, "ltr", c_idx, dx_px=x_off_px, dy_px_override=dy_ov)
            out.append((cjk_face, gn, a, gm))
        return out

    if len(tok) > 1 and any(ord(c) == 0x200D or (0x1F3FB <= ord(c) <= 0x1F3FF) for c in tok):
        ef = family.special_face('emoji', size26)
        if ef is not None:
            hb_em = ef.shape_devanagari_word_with_clusters(tok)
            if hb_em and all(it[0] != '.notdef' for it in hb_em):
                out = []
                for c_idx, (gn, x_adv26, _, _, ctxt) in enumerate(hb_em):
                    a = x_adv26 + extra_track26
                    use_txt = tok if (len(hb_em) == 1 and c_idx == 0) else ctxt
                    gm = _make_g_meta(style_meta, use_txt, "ltr", c_idx, is_lig=(len(use_txt) > 1))
                    out.append((ef, gn, a, gm))
                return out

    out = []
    i_ch = 0
    c_idx = 0
    while i_ch < len(tok):
        ch = tok[i_ch]
        cp = ord(ch)
        if cp in (0xFE0E, 0xFE0F, 0x200D):
            if out:
                out[-1][3]["cluster_text"] = out[-1][3].get("cluster_text", "") + ch
            i_ch += 1
            continue
        cluster_s = ch
        while i_ch + 1 < len(tok) and ord(tok[i_ch + 1]) in (0xFE0E, 0xFE0F):
            cluster_s += tok[i_ch + 1]
            i_ch += 1
        use_f = face if cp in face.cmap else family.fallback_face_for_char(ch, size26)
        n = use_f.cmap.get(cp, '.notdef')
        a = use_f.adv26(n) + extra_track26
        gm = _make_g_meta(style_meta, cluster_s, "ltr", c_idx)
        out.append((use_f, n, a, gm))
        c_idx += 1
        i_ch += 1
    return out


def build_items(runs, family, cfg, size26, display=False, hyphenator=None, allow_hyphenation=True, lang="en", allow_sc_hyph=False):
    items = []
    word_counter = 0

    if hyphenator is None and cfg.hyphenate and allow_hyphenation:
        from .hyphen import LiangHyphenator
        dic_path = cfg.resolve_hyphen_dic(lang=lang)
        if dic_path:
            lp_h = (lang or "en").lower().split("-")[0]
            hyphenator = LiangHyphenator.get_cached(
                dic_path,
                left_min=cfg.left_hyphen_min,
                right_min=cfg.right_hyphen_min,
                min_word_len=(6 if lp_h != "en" else cfg.min_word_length)
            )

    token_re = re.compile(r'(\n|[ \t\r]+|\u00a0+|[\u2013\u2014]+|[^ \t\n\r\u00a0\-\u2010\u2013\u2014]+[\-\u2010]?|[\-\u2010]+)')

    for run in runs:
        if getattr(run, 'image', None) is not None:
            im = run.image
            sc = cfg.dpi_scale
            w_sc = max(1, int(round(im.width * sc)))
            h_sc = max(1, int(round(im.height * sc)))
            from PIL import Image as PILImage
            im_scaled = im.resize((w_sc, h_sc), PILImage.BILINEAR) if sc != 1.0 else im
            w26 = int(round(im_scaled.width * 64))
            items.append(Box([], w26, inline_image=im_scaled, word_idx=word_counter))
            word_counter += 1
            continue

        r_size26 = int(round(size26 * getattr(run, 'scale', 1.0)))
        if getattr(run, 'code', False):
            face = family.special_face('mono', r_size26)
        else:
            face = family.face(run.bold, run.italic, r_size26, display)

        text = run.text
        if not text:
            continue

        extra_track26 = int(round(getattr(run, 'letter_spacing_em', 0.0) * r_size26))
        extra_word26 = int(round(getattr(run, 'word_spacing_em', 0.0) * r_size26))
        if extra_word26 > 0 and items and isinstance(items[-1], Glue):
            items[-1].width += extra_word26
        is_nowrap = getattr(run, 'nowrap', False)
        if is_nowrap:
            nw_w = sum(g[2] for g in _shape_token_with_fallbacks(text, face, family, run, r_size26, display, extra_track26))
            max_lw = (cfg.right - cfg.x0) * 64
            if nw_w > max_lw:
                if items:
                    items.append(Glue(0, 1e9, 0))
                    items.append(Penalty(0, -INF, False))
                acc_w = 0
                split_idx = None
                for ch_i, ch_c in enumerate(text):
                    sh_c = _shape_token_with_fallbacks(ch_c, face, family, run, r_size26, display, extra_track26) if ch_c != " " else [(face, "space", face.space26() + extra_word26 + extra_track26)]
                    w_c = sum(g[2] for g in sh_c)
                    if acc_w + w_c > max_lw:
                        split_idx = ch_i
                        break
                    acc_w += w_c
                if split_idx is not None:
                    text = text[:split_idx] + "\u200b" + text[split_idx:]

        run_style_meta = None
        if (run.baseline_shift_em != 0.0 or run.underline or run.strike or run.fg is not None or getattr(run, "bg", None) is not None or getattr(run, "link_href", None) is not None):
            run_style_meta = dict(
                dy_px=int(round(run.baseline_shift_em * (r_size26 / 64.0))),
                underline=run.underline,
                strike=run.strike,
                fg=run.fg,
                bg=getattr(run, "bg", None),
                link_href=getattr(run, "link_href", None)
            )

        tokens = token_re.findall(text)
        for t_idx, tok in enumerate(tokens):
            if not tok:
                continue

            if tok == "\n":
                items.append(Glue(0, 1e9, 0))
                items.append(Penalty(0, -INF, False))
                word_counter += 1
                continue

            if tok[0] in " \t\r":
                sp_base = family.face(run.bold, run.italic, int(round(r_size26 * 0.70)), display).space26() if getattr(run, "small_caps", False) else face.space26()
                if t_idx > 0 and t_idx + 1 < len(tokens):
                    t_prev, t_next = tokens[t_idx - 1], tokens[t_idx + 1]
                    if any(0x1200 <= ord(c) <= 0x137F for c in t_prev) and any(0x1200 <= ord(c) <= 0x137F for c in t_next):
                        sp_base = family.special_face('ethiopic', r_size26).space26()
                    elif any(0x0600 <= ord(c) <= 0x06FF for c in t_prev) and any(0x0600 <= ord(c) <= 0x06FF for c in t_next):
                        sp_base = family.special_face('arabic', r_size26).space26()
                    elif any(0x0590 <= ord(c) <= 0x05FF for c in t_prev) and any(0x0590 <= ord(c) <= 0x05FF for c in t_next):
                        sp_base = family.special_face('hebrew', r_size26).space26()
                    elif any(0x0900 <= ord(c) <= 0x097F for c in t_prev) and any(0x0900 <= ord(c) <= 0x097F for c in t_next):
                        sp_base = family.special_face('devanagari', r_size26).space26()
                    elif any(0xAC00 <= ord(c) <= 0xD7AF for c in t_prev) and any(0xAC00 <= ord(c) <= 0xD7AF for c in t_next):
                        sp_base = family.special_face('cjk', r_size26).space26() + (int(round(0.0536 * r_size26)) if len(runs) == 1 else 0)
                    elif any(ord(c) >= 0x1F000 or ord(c) in (0x2615, 0x2764, 0x2665) for c in t_prev) and any(ord(c) >= 0x1F000 or ord(c) in (0x2615, 0x2764, 0x2665) for c in t_next):
                        sp_base = family.special_face('emoji', r_size26).space26()
                sp = sp_base + extra_word26 + extra_track26
                sh_u = math.floor(sp * cfg.space_shrink)
                items.append(Glue(sp, sp * cfg.space_stretch, sh_u, non_breaking=is_nowrap, style_meta=run_style_meta, is_mono=getattr(run, 'code', False)))
                word_counter += 1

            elif tok[0] == "\u00a0":
                sp = (face.space26() + extra_word26 + extra_track26) * len(tok)
                sh_u = math.floor(sp * cfg.space_shrink)
                items.append(Glue(sp, sp * cfg.space_stretch, sh_u, non_breaking=True, style_meta=run_style_meta))
                word_counter += 1

            elif tok in ("-", "\u2010", "\u2013", "\u2014"):
                prev_was_glue = bool(items and isinstance(items[-1], Glue))
                shaped = _shape_token_with_fallbacks(tok, face, family, run, r_size26, display, extra_track26)
                w = sum(g[2] for g in shaped)
                items.append(Box(shaped, w, word_idx=word_counter))
                if not prev_was_glue and not is_nowrap:
                    items.append(Penalty(0, 0, False))

            elif "/" in tok and len(tok) > 3 and not is_nowrap:
                parts = re.split(r'(?<=/)(?=.)', tok)
                for p_i, part in enumerate(parts):
                    shaped = _shape_token_with_fallbacks(part, face, family, run, r_size26, display, extra_track26)
                    w = sum(g[2] for g in shaped)
                    items.append(Box(shaped, w, word_idx=word_counter))
                    if p_i < len(parts) - 1:
                        items.append(Penalty(0, 0, False))

            else:
                has_trailing_hyphen = tok.endswith(("-", "\u2010")) and len(tok) > 1
                core_tok = tok[:-1] if has_trailing_hyphen else tok

                if "\u200b" in core_tok:
                    p0, p1 = core_tok.split("\u200b", 1)
                    for p_i, pt in enumerate((p0, p1)):
                        sh_p = _shape_token_with_fallbacks(pt, face, family, run, r_size26, display, extra_track26)
                        items.append(Box(sh_p, sum(g[2] for g in sh_p), word_idx=word_counter))
                        if p_i == 0:
                            items.append(Penalty(0, 0, False))
                    continue
                elif len(core_tok) > 1 and not is_nowrap and any(0x3040 <= ord(c) <= 0x9FFF or 0xAC00 <= ord(c) <= 0xD7AF for c in core_tok):
                    cjk_closing = set("。、．，」』）】！？!?,.:;)")
                    cjk_chunks = []
                    for ch_c in core_tok:
                        if cjk_chunks and ch_c in cjk_closing:
                            cjk_chunks[-1] += ch_c
                        else:
                            cjk_chunks.append(ch_c)
                    for c_i, ck in enumerate(cjk_chunks):
                        sh_c = _shape_token_with_fallbacks(ck, face, family, run, r_size26, display, extra_track26)
                        items.append(Box(sh_c, sum(g[2] for g in sh_c), word_idx=word_counter))
                        if c_i < len(cjk_chunks) - 1:
                            items.append(Penalty(0, 0, False))
                    continue
                elif "\u00ad" in core_tok and not is_nowrap:
                    syllables = [s for s in core_tok.split("\u00ad") if s]
                    if has_trailing_hyphen and syllables:
                        syllables[-1] = syllables[-1] + tok[-1]
                    clean_tok = "".join(syllables)
                else:
                    no_lead = core_tok.lstrip('([\u201c\u2018"\'\u00ab')
                    lead_punct = core_tok[:len(core_tok) - len(no_lead)]
                    alpha = no_lead.rstrip('.,!?:;\u201d\u2019"\')]\u00bb\u2026')
                    trail_punct = no_lead[len(alpha):] + (tok[-1] if has_trailing_hyphen else "")

                    for apos in ("\u2019", "'"):
                        if apos in alpha:
                            a_idx = alpha.index(apos)
                            if 1 <= a_idx <= 6 and alpha[:a_idx].isalpha() and alpha[a_idx + 1:].isalpha():
                                lead_punct = lead_punct + alpha[:a_idx + 1]
                                alpha = alpha[a_idx + 1:]
                                break

                    is_all_caps_word = alpha.isupper() and len(alpha) < 8 and not getattr(run, 'from_text_transform', False) and not has_trailing_hyphen
                    if (alpha and alpha.isalpha() and len(alpha) >= cfg.min_word_length
                            and cfg.hyphenate and allow_hyphenation and hyphenator
                            and not is_nowrap and not is_all_caps_word
                            and not getattr(run, 'code', False) and (not getattr(run, 'small_caps', False) or allow_sc_hyph)):
                        sylls = hyphenator.hyphenate_word(alpha)
                        if len(sylls) > 1:
                            sylls[0] = lead_punct + sylls[0]
                            sylls[-1] = sylls[-1] + trail_punct
                        else:
                            sylls = [tok]
                        syllables = sylls
                    else:
                        syllables = [tok]
                    clean_tok = tok

                is_rtl_tok = any(0x0590 <= ord(c) <= 0x06FF for c in clean_tok)
                b_dir = "rtl" if is_rtl_tok else "ltr"

                if len(syllables) <= 1:
                    shaped = _shape_token_with_fallbacks(clean_tok, face, family, run, r_size26, display, extra_track26)
                    w = sum(g[2] for g in shaped)
                    items.append(Box(shaped, w, word_idx=word_counter, direction=b_dir))
                else:
                    hy_face = family.face(run.bold, run.italic, int(round(r_size26 * 0.70)), display) if getattr(run, 'small_caps', False) else face
                    hn = hy_face.names("-")
                    hw = 0 if (getattr(run, 'small_caps', False) and allow_sc_hyph) else sum(hy_face.adv26(n) for n in hn)
                    hy_meta = _make_g_meta(run_style_meta, "-", "ltr", 0, is_synth_hy=True)
                    hy_glyphs = [(hy_face, n, hy_face.adv26(n), hy_meta) for n in hn]
                    shaped = _shape_token_with_fallbacks(clean_tok, face, family, run, r_size26, display, extra_track26)
                    if len(shaped) == len(clean_tok):
                        curr = 0
                        for s_idx, syll in enumerate(syllables):
                            chunk = shaped[curr:curr + len(syll)]
                            curr += len(syll)
                            w = sum(g[2] for g in chunk)
                            items.append(Box(chunk, w, word_idx=word_counter, direction=b_dir))
                            if s_idx < len(syllables) - 1:
                                items.append(Penalty(hw, cfg.hyphen_penalty, True, hy_glyphs))
                    else:
                        lig_map = getattr(face, "lig_len_map", {})
                        curr_char = 0
                        target_char = 0
                        g_idx = 0
                        chunk = []
                        for s_idx, syll in enumerate(syllables):
                            target_char += len(syll)
                            while g_idx < len(shaped) and curr_char < target_char:
                                chunk.append(shaped[g_idx])
                                g_name = shaped[g_idx][1]
                                c_len = lig_map.get(
                                    g_name,
                                    3 if g_name in ("ffi", "ffl", "glyph00323", "glyph00324")
                                    else (2 if g_name in ("fi", "fl", "ff", "glyph00320", "glyph00321", "glyph00322") else 1)
                                )
                                curr_char += c_len
                                g_idx += 1
                            if curr_char == target_char or s_idx == len(syllables) - 1:
                                if chunk:
                                    w = sum(g[2] for g in chunk)
                                    items.append(Box(chunk, w, word_idx=word_counter, direction=b_dir))
                                    chunk = []
                                if s_idx < len(syllables) - 1:
                                    items.append(Penalty(hw, cfg.hyphen_penalty, True, hy_glyphs))

                if items and isinstance(items[-1], Box) and len(items[-1].glyphs) >= 2 and not is_nowrap:
                    if items[-1].glyphs[-1][1] == "ellipsis" and items[-1].glyphs[-2][1] in ("period", "comma", "question", "exclam", "colon", "semicolon"):
                        last_box = items.pop()
                        g_pre = last_box.glyphs[:-1]
                        g_ell = [last_box.glyphs[-1]]
                        items.append(Box(g_pre, sum(g[2] for g in g_pre), word_idx=last_box.word_idx, direction=last_box.direction))
                        items.append(Penalty(0, 0, False))
                        items.append(Box(g_ell, g_ell[0][2], word_idx=last_box.word_idx, direction=last_box.direction))

                if has_trailing_hyphen and not is_nowrap:
                    items.append(Penalty(0, 0, False))

    while items and isinstance(items[0], Glue):
        items.pop(0)
    while items and isinstance(items[-1], Glue):
        items.pop()

    if len(items) >= 3 and isinstance(items[-1], Box) and isinstance(items[-2], Glue) and isinstance(items[-3], Box):
        if items[-1].glyphs and items[-1].glyphs[0][1] == "bracketleft" and items[-1].glyphs[-1][1] == "bracketright":
            if items[-3].glyphs and items[-3].glyphs[-1][1] in ("quotedblright", "quoteright", "guillemotright"):
                items[-2].non_breaking = True

    return items

def _badness(r):
    if r < -1:
        return INF
    if r < 0:
        return 150.0 * (r * r)
    return 100.0 * (r * r)

def _hanging_overhang(it, prev_it, cfg):
    if not cfg.optical_margin:
        return 0
    if isinstance(it, Penalty) and it.width > 0:
        return math.floor(cfg.optical_margin_ratio * it.width)
    if prev_it and isinstance(prev_it, Box) and prev_it.glyphs:
        last_name = prev_it.glyphs[-1][1]
        if last_name in RIGHT_HANGING_GLYPHS:
            return math.floor(cfg.optical_margin_ratio * prev_it.glyphs[-1][2])
    return 0

def break_balanced_ragged(items, line_w, w_last: float = 0.7):
    """Universal balanced ragged dynamic programming for headings and centered blocks."""
    n = len(items)
    if n == 0:
        return []
    W = [0]
    for it in items:
        W.append(W[-1] + (it.width if isinstance(it, (Box, Glue)) else 0))

    cands = []
    for i, it in enumerate(items):
        if isinstance(it, Glue) and i > 0 and isinstance(items[i - 1], Box) and not getattr(it, "non_breaking", False):
            cands.append(i)
        elif isinstance(it, Penalty) and it.penalty < INF:
            cands.append(i)
    cands.append(n)

    dp = {-1: (0.0, 0, [])}
    for b in cands:
        is_forced = (b < n and isinstance(items[b], Penalty) and items[b].penalty <= -INF)
        after_comma = (0 < b < n and isinstance(items[b - 1], Box) and items[b - 1].glyphs and items[b - 1].glyphs[-1][1] == "comma")
        best = None
        for a, (cost_a, ln_a, path_a) in list(dp.items()):
            s = a + 1
            while s < b and not isinstance(items[s], Box):
                s += 1
            pen_w = items[b].width if (b < n and isinstance(items[b], Penalty)) else 0
            w = W[b] - W[s] + pen_w
            L = line_w(ln_a)
            if w > L and s < b:
                continue
            short = max(0.0, (L - w) / float(max(1, L)))
            wt = w_last if (b == n or is_forced) else 1.0
            c = cost_a + 1.0 + wt * (short ** 2) - (0.05 if after_comma else 0.0)
            if best is None or c < best[0]:
                best = (c, ln_a + 1, path_a + [b])
        if is_forced:
            dp = {b: best} if best else {}
        elif best:
            dp[b] = best

    if n in dp:
        return dp[n][2]
    return None

def _orig_break_kp(items, line_w, tolerance, cfg, ragged):
    """Knuth-Plass global dynamic programming break selection with augmented state (fit, h_run)."""
    n = len(items)
    if n == 0:
        return []
    its = list(items)
    its.append(Glue(0, 1e9, 0))
    its.append(Penalty(0, -INF, False))

    W = [0.0]; Y = [0.0]; Z = [0.0]
    for it in its:
        if isinstance(it, Box):
            W.append(W[-1] + it.width); Y.append(Y[-1]); Z.append(Z[-1])
        elif isinstance(it, Glue):
            W.append(W[-1] + it.width); Y.append(Y[-1] + it.stretch); Z.append(Z[-1] + it.shrink)
        else:
            W.append(W[-1]); Y.append(Y[-1]); Z.append(Z[-1])

    active = [dict(pos=-1, line=0, fit=1, dem=0.0, prev=None, flag=False, h_run=0)]

    for b, it in enumerate(its):
        if isinstance(it, Glue):
            if b == 0 or not isinstance(its[b-1], Box) or getattr(it, "non_breaking", False):
                continue
        elif isinstance(it, Penalty):
            if it.penalty >= INF:
                continue
        else:
            continue

        best = {}
        new_active = []
        prev_it = its[b-1] if b > 0 else None
        hang = 0 if ragged else _hanging_overhang(it, prev_it, cfg)
        is_forced = isinstance(it, Penalty) and it.penalty <= -INF

        for a in active:
            s = a['pos'] + 1
            while s < b and not isinstance(its[s], Box):
                s += 1
            width = W[b] - W[s] + (it.width if isinstance(it, Penalty) else 0)
            L = line_w(a['line']) + hang

            if width < L:
                if ragged or is_forced:
                    r = 0.0
                else:
                    st = Y[b] - Y[s]
                    if st > 0:
                        r = (L - width) / st
                    elif width >= 0.85 * L:
                        r = (L - width) / (0.15 * L)
                    else:
                        r = INF
            elif width > L:
                sh = Z[b] - Z[s]
                r = (L - width) / sh if sh > 0 else -INF
                if ragged and r < -0.5:
                    r = -INF
            else:
                r = 0.0

            if (r >= -1 and not is_forced):
                new_active.append(a)

            if r < -1 and not is_forced:
                continue

            bad = _badness(r) if r != INF else INF
            if ragged and r != INF:
                bad = 0.0
            if r == INF and not ragged and not is_forced:
                continue
            if bad > 100 * tolerance ** 3 and not is_forced and not ragged:
                continue

            pen = it.penalty if isinstance(it, Penalty) else 0
            if ragged and isinstance(it, Penalty) and it.flagged and pen > 0:
                pen = getattr(cfg, "ragged_hyphen_penalty", 100)
            flagged = isinstance(it, Penalty) and it.flagged

            if ragged and not is_forced:
                short = max(0.0, (L - width)) / max(L, 1)
                r_sf = cfg.ragged_shortfall
                p_short = r_sf * short * short
                d = (1 + bad + p_short + max(0, pen)) ** 2
            elif pen >= 0:
                d = (1 + bad + pen) ** 2
            elif pen > -INF:
                d = (1 + bad) ** 2 - pen ** 2
            else:
                d = (1 + max(0.0, bad if bad != INF else 0.0)) ** 2

            h_run = (a.get('h_run', 0) + 1) if flagged else 0
            if h_run == 2:
                d += cfg.ladder2
            elif h_run >= 3:
                d += cfg.ladder2 + getattr(cfg, 'ladder3', 10000)

            fit = 0 if r < -0.5 else (1 if r <= 0.5 else (2 if r <= 1 else 3))
            if abs(fit - a['fit']) > 1:
                d += cfg.fitness_gap

            tot = a['dem'] + d
            state_key = (fit, min(h_run, 2), a.get('any_h', False) or flagged)
            if state_key not in best or tot < best[state_key][0]:
                best[state_key] = (tot, a, flagged, h_run)

        active = new_active
        if best:
            mn = min(v[0] for v in best.values())
            for state_key, (tot, a, flagged, h_run) in best.items():
                if tot <= mn + cfg.fitness_gap:
                    nd = dict(pos=b, line=a['line'] + 1, fit=state_key[0], dem=tot, prev=a, flag=flagged, h_run=h_run, any_h=(a.get('any_h', False) or flagged))
                    active.append(nd)
        if not active:
            return None

    finals = [a for a in active if a['pos'] == len(its) - 1]
    if not finals:
        return None
    node = min(finals, key=lambda a: a['dem'])
    breaks = []
    while node and node['pos'] >= 0:
        breaks.append(node['pos'])
        node = node['prev']
    breaks.reverse()
    return [b for b in breaks if b < len(items) or b == len(items) + 1][:-1] + [len(items)]

TABLE_CONSEC = (0.0, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0)
TABLE_WINDOW = (0.0, 0.0, 0.0, 1.0, 3.0, 8.0, 9.0, 10.0, 10.0)

def break_kp(items, line_w, tolerance, cfg, ragged):
    """
    Backward Dynamic Programming Paragraph Composer.
    """
    n_items = len(items)
    if n_items == 0:
        return []
    if n_items > 1000:
        return None

    l0 = float(line_w(0))
    l1 = float(line_w(1))
    l2 = float(line_w(2))
    l3 = float(line_w(3))
    varies_dropcap = (abs(l1 - l2) > 1.0 or abs(l2 - l3) > 1.0 or abs(l1 - l0) > 0.078 * l1)

    ref_size26 = float(cfg.size26)
    for it in items:
        if isinstance(it, Box) and it.glyphs and it.glyphs[0][0] is not None:
            ref_size26 = float(it.glyphs[0][0].size26)
            break
    std_sp26 = ref_size26 * 0.25

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
                SP[idx + 1] += (float(it.width) if getattr(it, 'is_mono', False) else min(float(it.width), std_sp26))

    nodes = []
    for b, it in enumerate(items):
        if isinstance(it, Glue):
            if b == 0 or not isinstance(items[b - 1], Box) or getattr(it, "non_breaking", False):
                continue
            is_hyph = False
            is_forced = False
            hyph_w = 0.0
        elif isinstance(it, Penalty):
            if it.penalty >= INF:
                continue
            is_hyph = bool(it.flagged or it.width > 0)
            is_forced = bool(it.penalty <= -INF)
            hyph_w = float(it.width)
        else:
            continue

        prev_it = items[b - 1] if b > 0 else None
        hang = 0.0 if ragged else float(_hanging_overhang(it, prev_it, cfg))
        e_idx = b
        while e_idx > 0 and isinstance(items[e_idx - 1], Glue):
            e_idx -= 1
        s_next = b + 1
        while s_next < n_items and not isinstance(items[s_next], Box):
            s_next += 1
        nodes.append({
            "item_idx": b,
            "e_idx": e_idx,
            "s_next": s_next,
            "hyph_w": hyph_w,
            "hang": hang,
            "is_hyph": is_hyph,
            "is_forced": is_forced,
        })

    e_idx = n_items
    while e_idx > 0 and isinstance(items[e_idx - 1], Glue):
        e_idx -= 1
    prev_it = items[e_idx - 1] if e_idx > 0 else None
    hang = 0.0 if ragged else float(_hanging_overhang(Penalty(0, -INF, False), prev_it, cfg))
    nodes.append({
        "item_idx": n_items,
        "e_idx": e_idx,
        "s_next": n_items,
        "hyph_w": 0.0,
        "hang": hang,
        "is_hyph": False,
        "is_forced": True,
    })

    N = len(nodes)
    has_internal_forced = any(nd["is_forced"] for nd in nodes[:-1])
    if varies_dropcap or has_internal_forced:
        return _orig_break_kp(items, line_w, tolerance, cfg, ragged)

    indent_w = (l1 - l0)

    def get_L(start_i):
        return l1

    def get_start_off(start_i):
        return indent_w if start_i == 0 else 0.0

    INF_COST = 3.4028235e38
    best_cost = [INF_COST] * N
    next_break = [-1] * N
    hyph_mask = [0] * N

    last_node = nodes[N - 1]
    first_invalid = -1
    w28 = 1

    for i in range(N - 1, -1, -1):
        s_idx = 0 if i == 0 else nodes[i - 1]["s_next"]
        e_idx = last_node["e_idx"]
        w = (W[e_idx] - W[s_idx]) + last_node["hyph_w"] + get_start_off(i)
        L = get_L(i) + last_node["hang"]
        if w >= L:
            first_invalid = i
            break

        next_break[i] = N
        if i == 0:
            c = 0.5
            s1 = 0.5
            w9 = 0
            w28 = 0
        else:
            w9_flag = 1 if nodes[i - 1]["is_hyph"] else 0
            w10 = w28 & w9_flag
            if w10 == 1:
                c = 5.0
                s1 = 5.0
                w9 = 1
            else:
                c = 0.5
                s1 = 0.5
                w9 = w9_flag
                w28 = w10
        hyph_mask[i] = w9
        if not ragged:
            fill = (w - last_node["hang"]) / get_L(i) if get_L(i) > 0 else 1.0
            if fill < 0.2:
                c = s1 + (0.2 - fill) * 4.2
        best_cost[i] = c

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
            n_mono_boxes = sum(
                1 for k_it in range(s_idx, min(e_idx, n_items))
                if isinstance(items[k_it], Box) and items[k_it].glyphs and items[k_it].glyphs[0][0] is not None and "Mono" in getattr(items[k_it].glyphs[0][0], "path", "")
            )
            if n_mono_boxes >= 4 or (n_mono_boxes >= 2 and indent_w > 0):
                return s9 + 1000000.0, w - nd_e["hang"]
            max_sh = G * (0.099 if ragged else 0.179)
            if (-slack) > max_sh:
                return s9 + 1000000.0, w - nd_e["hang"]

            s0 = (slack / G) * 2.5
        else:
            has_cjk_line = any(
                isinstance(items[k_it], Box) and items[k_it].glyphs and items[k_it].glyphs[0][0] is not None and "CJK" in getattr(items[k_it].glyphs[0][0], "path", "")
                for k_it in range(s_idx, min(e_idx, n_items))
            )
            if not ragged and not has_cjk_line:
                s0 = (slack / G) * 2.0
            elif has_cjk_line:
                s0 = (slack / ref_size26) * 0.61
            else:
                s0 = (slack / ref_size26) * 0.61
                if nd_e["is_forced"]:
                    s0 *= 0.01

        cost = s9 + s0 * s0

        if start_i > 0:
            nd_s = nodes[start_i]
            if abs((W[nd_s["e_idx"]] + nd_s["hyph_w"]) - W[s_idx]) < 0.0001:
                cost += 5.0

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
            cost += 1.5 * c_pen

        return cost, w - nd_e["hang"]

    last_valid_end = N - 1
    for i in range(first_invalid, -1, -1):
        if last_valid_end < i:
            last_valid_end = i
        best_c = INF_COST
        best_j = -1
        L_base = get_L(i)
        d10 = L_base * 0.8
        d11 = L_base * 1.2
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

    if next_break[0] == -1 or best_cost[0] >= 1000000.0:
        return None

    out_breaks = []
    cur = 0
    while cur < N and cur != -1:
        nxt = next_break[cur]
        if nxt == -1 or nxt <= cur:
            return None
        end_node = nodes[nxt - 1]
        out_breaks.append(end_node["item_idx"])
        cur = nxt

    return out_breaks

def break_greedy(items, line_w, cfg, ragged=False, allow_shrink=True):
    """Greedy first-fit break selection supporting explicit forced breaks (Penalty -INF)."""
    breaks, start, width, line, last_ok = [], 0, 0, 0, None
    allowed_shrink = 0
    i = 0
    n = len(items)
    L = line_w(0)
    while i < n:
        it = items[i]
        if isinstance(it, Penalty) and it.penalty <= -INF:
            breaks.append(i)
            line += 1
            L = line_w(line)
            start = i + 1
            i = start
            width = 0
            allowed_shrink = 0
            last_ok = None
            continue
        pw = width + (it.width if isinstance(it, (Box, Penalty)) else 0)
        hang = 0 if ragged else _hanging_overhang(it, items[i-1] if i > 0 else None, cfg)
        if pw > L + hang + allowed_shrink and last_ok is not None and i > start:
            b = last_ok
            breaks.append(b)
            line += 1
            L = line_w(line)
            start = b + 1
            i = start
            width = 0
            allowed_shrink = 0
            last_ok = None
            continue
        if isinstance(it, Box):
            width += it.width
        elif isinstance(it, Glue):
            if i > start and not getattr(it, "non_breaking", False):
                last_ok = i
            width += it.width
            if allow_shrink:
                allowed_shrink += int(it.shrink if not ragged else 0.5 * it.shrink)
        elif isinstance(it, Penalty):
            if i > start and it.penalty < INF:
                last_ok = i
        i += 1
    breaks.append(n)
    return breaks

def _split_overwide_boxes(items, line_w, cfg):
    """Universal emergency splitter for any Box wider than the line measure."""
    out = []
    for idx, it in enumerate(items):
        max_lw = line_w(0) if idx == 0 else line_w(1)
        if isinstance(it, Box) and it.glyphs and it.width > max_lw and max_lw > 0 and not all(g[1] == ".notdef" for g in it.glyphs) and not any("Thai" in getattr(g[0], "path", "") for g in it.glyphs if g[0] is not None):
            rem = list(it.glyphs)
            while len(rem) > 1 and sum(g[2] for g in rem) > max_lw:
                f0 = rem[0][0]
                hn = f0.names("-") if f0 is not None else ["hyphen"]
                hw = sum(f0.adv26(n) for n in hn) if f0 is not None else 0
                base_m = rem[0][3] if len(rem[0]) > 3 else None
                hy_m = _make_g_meta(base_m, "-", "ltr", 0, is_synth_hy=True)
                hy_g = [(f0, n, f0.adv26(n), hy_m) for n in hn] if f0 is not None else []
                acc = 0
                cut = 1
                for k, g in enumerate(rem[:-1], 1):
                    if acc + g[2] + hw <= max_lw:
                        acc += g[2]
                        cut = k
                    else:
                        break
                chunk = rem[:cut]
                out.append(Box(chunk, sum(g[2] for g in chunk), word_idx=it.word_idx, direction=it.direction))
                out.append(Penalty(hw, cfg.hyphen_penalty, True, hy_g))
                rem = rem[cut:]
            if rem:
                out.append(Box(rem, sum(g[2] for g in rem), word_idx=it.word_idx, direction=it.direction))
        else:
            out.append(it)
    return out

def make_lines(items, line_w, cfg, ragged, is_heading=False, align=None):
    """Splits item sequence into lines."""
    if not items:
        return []
    items = _split_overwide_boxes(items, line_w, cfg)

    if is_heading:
        n_boxes = sum(1 for it in items if isinstance(it, Box))
        w_all_but_last = sum(it.width for it in items[:-2] if isinstance(it, (Box, Glue))) if len(items) >= 3 else 0
        if (n_boxes >= 5 or (n_boxes == 4 and w_all_but_last > 0.72 * line_w(0))) and isinstance(items[-1], Box) and len(items[-1].glyphs) <= getattr(cfg, "runt_min_chars", 7):
            if len(items) >= 3 and isinstance(items[-2], Glue) and isinstance(items[-3], Box):
                pair_w = items[-3].width + items[-2].width + items[-1].width
                if pair_w <= line_w(0):
                    items[-2].non_breaking = True
        for idx, it in enumerate(items[:-1]):
            if isinstance(it, Box) and it.glyphs:
                if it.glyphs[0][1] == 'parenleft' and it.glyphs[-1][1] != 'parenright':
                    if isinstance(items[idx + 1], Glue):
                        items[idx + 1].non_breaking = True
        is_all_caps_hd = all(
            not any(97 <= k <= 122 for g in it.glyphs if g[0] is not None for k, v in g[0].cmap.items() if v == g[1])
            for it in items if isinstance(it, Box)
        )
        has_colon_long_end = (
            len(items) >= 3 and isinstance(items[-1], Box) and items[-1].width > 0.65 * line_w(0)
            and isinstance(items[-3], Box) and items[-3].glyphs and items[-3].glyphs[-1][1] == "colon"
        )
        is_large_hd = any(isinstance(it, Box) and it.glyphs and it.glyphs[0][0].size26 > cfg.size26 for it in items)
        w_last_hd = 0.15 if (is_all_caps_hd or has_colon_long_end) else (0.7 if is_large_hd else 0.62)
        br = break_balanced_ragged(items, line_w, w_last=w_last_hd)
        if not br:
            br = break_greedy(items, line_w, cfg, ragged=True, allow_shrink=False)
    elif align == "center":
        br = break_balanced_ragged(items, line_w, w_last=0.7)
        if not br:
            br = break_greedy(items, line_w, cfg, ragged=True, allow_shrink=False)
    elif align == "right":
        br = break_greedy(items, line_w, cfg, ragged=False, allow_shrink=True)
    else:
        br = None
        has_long_compound = sum(1 for it in items if isinstance(it, Penalty) and not it.flagged and it.penalty > -INF) >= 5
        use_kp = (cfg.breaker == "kp") and not (ragged and cfg.ragged_greedy) and not has_long_compound
        if use_kp:
            for tol in (cfg.tolerance, cfg.tolerance * 2, cfg.tolerance * 4):
                br = break_kp(items, line_w, tol, cfg, ragged)
                if br:
                    break
        if not br:
            br = break_greedy(items, line_w, cfg, ragged=ragged, allow_shrink=(not is_heading and align != 'center'))

    if not br:
        br = [i + 1 for i, it in enumerate(items) if isinstance(it, Box)] or [len(items)]
    lines, start = [], 0
    for k, b in enumerate(br):
        seg = items[start:b]
        while seg and not isinstance(seg[0], Box):
            seg = seg[1:]
        while seg and isinstance(seg[-1], Glue):
            seg = seg[:-1]
        hy = None
        if b < len(items) and isinstance(items[b], Penalty) and items[b].width > 0:
            hy = items[b]
        if seg:
            def _is_rtl_box(it):
                return isinstance(it, Box) and it.glyphs and any(
                    g[0] is not None and any(k in getattr(g[0], "path", "") for k in ("Arabic", "Naskh", "Hebrew"))
                    for g in it.glyphs
                )
            def _is_num_box(it):
                return isinstance(it, Box) and it.glyphs and all(
                    str(g[1]) in {"zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"}
                    for g in it.glyphs
                )
            new_seg = []
            idx_s = 0
            while idx_s < len(seg):
                if _is_rtl_box(seg[idx_s]):
                    idx_e = idx_s + 1
                    while idx_e < len(seg):
                        if _is_rtl_box(seg[idx_e]):
                            idx_e += 1
                        elif _is_num_box(seg[idx_e]) and any(_is_rtl_box(seg[k]) for k in range(idx_e + 1, min(len(seg), idx_e + 4))):
                            idx_e += 1
                        elif isinstance(seg[idx_e], Glue) and idx_e + 1 < len(seg) and (
                            _is_rtl_box(seg[idx_e + 1]) or (
                                _is_num_box(seg[idx_e + 1]) and any(_is_rtl_box(seg[k]) for k in range(idx_e + 2, min(len(seg), idx_e + 5)))
                            )
                        ):
                            idx_e += 2
                        else:
                            break
                    sub_rtl = list(reversed(seg[idx_s:idx_e]))
                    if len(sub_rtl) > 1 and sub_rtl[0].glyphs and sub_rtl[0].glyphs[0][1] == "period":
                        per_g = sub_rtl[0].glyphs.pop(0)
                        if len(per_g) > 3 and isinstance(per_g[3], dict):
                            per_g = (per_g[0], per_g[1], per_g[2], dict(per_g[3], moved_rtl_period_word_idx=sub_rtl[0].word_idx))
                        sub_rtl[0].width -= per_g[2]
                        sub_rtl[-1].glyphs.append(per_g)
                        sub_rtl[-1].width += per_g[2]
                    new_seg.extend(sub_rtl)
                    idx_s = idx_e
                else:
                    new_seg.append(seg[idx_s])
                    idx_s += 1
            seg = new_seg
        if seg or hy:
            lines.append((seg, hy))
        start = b + 1
    return lines

def layout_line(seg, hy, width26, justify, last, cfg):
    """Computes exact glyph placements for a single line."""
    if not seg and not hy:
        return [], 0, 0

    overhang26 = 0
    if getattr(cfg, "overhang_shift", True) and seg and isinstance(seg[0], Box) and seg[0].glyphs:
        f0, n0 = seg[0].glyphs[0][0], seg[0].glyphs[0][1]
        if f0 is not None:
            overhang26 = max(0, -f0.lsb26(n0))

    hang_right = 0
    hang_left = 0
    if getattr(cfg, "optical_margin_draw", False):
        if hy:
            hang_right = math.floor(cfg.optical_margin_ratio * hy.width)
        elif seg and isinstance(seg[-1], Box) and seg[-1].glyphs:
            last_name = seg[-1].glyphs[-1][1]
            if last_name in RIGHT_HANGING_GLYPHS:
                hang_right = math.floor(cfg.optical_margin_ratio * seg[-1].glyphs[-1][2])
        if getattr(cfg, "left_optical_margin", False) and seg and isinstance(seg[0], Box) and seg[0].glyphs:
            first_name = seg[0].glyphs[0][1]
            if first_name in LEFT_HANGING_GLYPHS:
                hang_left = math.floor(cfg.optical_margin_ratio * seg[0].glyphs[0][2])

    effective_target_w = width26 - overhang26 + hang_right + hang_left

    glues = [i for i, it in enumerate(seg) if isinstance(it, Glue)]
    nat = sum(it.width for it in seg if isinstance(it, (Box, Glue))) + (hy.width if hy else 0)
    extra_glue = [0] * len(seg)
    track_per_box = [0] * len(seg)

    delta = int(effective_target_w - nat)

    if ((justify and not (last and cfg.last_line_flush_left)) or delta < 0) and glues:
        k = len(glues)
        max_stretch = int(round(sum(seg[gi].stretch for gi in glues)))
        max_shrink = int(round(sum(seg[gi].shrink for gi in glues)))

        if cfg.micro_tracking and (delta > max_stretch or delta < -max_shrink):
            tier1_delta = max(-max_shrink, min(max_stretch, delta))
            resid = delta - tier1_delta
            total_gaps = sum(max(0, len(it.glyphs) - 1) for it in seg if isinstance(it, Box))
            if total_gaps > 0:
                ref_size26 = cfg.size26
                for it in seg:
                    if isinstance(it, Box) and it.glyphs and it.glyphs[0][0] is not None:
                        ref_size26 = it.glyphs[0][0].size26
                        break
                min_t = int(round(cfg.tracking_min_em * ref_size26))
                max_t = int(round(cfg.tracking_max_em * ref_size26))
                t_gap = max(min_t, min(max_t, int(resid / total_gaps)))
                resid -= t_gap * total_gaps
                tier1_delta += resid
            else:
                t_gap = 0

            base, rem = divmod(tier1_delta, k)
            for j, gi in enumerate(glues):
                if getattr(cfg, "remainder", "bresenham") == "bresenham":
                    extra_glue[gi] = ((j + 1) * tier1_delta) // k - (j * tier1_delta) // k
                else:
                    e = base + (1 if (cfg.remainder == "first" and j < rem) or (cfg.remainder == "last" and j >= k - rem) else 0)
                    extra_glue[gi] = e

            for i, it in enumerate(seg):
                if isinstance(it, Box):
                    track_per_box[i] = t_gap
        else:
            if not justify and delta < 0:
                delta = max(-max_shrink, delta)
            base, rem = divmod(delta, k)
            has_mixed_face = len({(g[0].path, g[0].size26) for x in seg if isinstance(x, Box) for g in x.glyphs if g[0] is not None}) > 1
            tot_gw = sum(max(1, seg[gi].width) for gi in glues)
            cum_gw = 0
            for j, gi in enumerate(glues):
                if has_mixed_face:
                    nxt_gw = cum_gw + max(1, seg[gi].width)
                    extra_glue[gi] = (nxt_gw * delta) // tot_gw - (cum_gw * delta) // tot_gw
                    cum_gw = nxt_gw
                elif getattr(cfg, "remainder", "bresenham") == "bresenham":
                    extra_glue[gi] = ((j + 1) * delta) // k - (j * delta) // k
                else:
                    e = base + (1 if (cfg.remainder == "first" and j < rem) or (cfg.remainder == "last" and j >= k - rem) else 0)
                    extra_glue[gi] = e

    out = []
    pen = 0
    vis_word_idx = 0
    last_logical_w = None

    for i, it in enumerate(seg):
        if isinstance(it, Box):
            if getattr(it, 'inline_image', None) is not None:
                out.append((None, '__inline_img__', (pen, it.inline_image)))
                pen += it.width
                vis_word_idx += 1
                last_logical_w = None
                continue
            if last_logical_w is not None and it.word_idx != last_logical_w:
                vis_word_idx += 1
            last_logical_w = it.word_idx
            t_gap = track_per_box[i]
            for g_idx, g_tup in enumerate(it.glyphs):
                face, name, adv = g_tup[0], g_tup[1], g_tup[2]
                s_meta = dict(g_tup[3]) if (len(g_tup) > 3 and g_tup[3] is not None) else {}
                s_meta["word_idx"] = vis_word_idx
                s_meta["logical_word_idx"] = s_meta.get("moved_rtl_period_word_idx", it.word_idx)
                s_meta["direction"] = s_meta.get("direction", it.direction)
                out.append((face, name, pen, adv, s_meta))
                pen += adv
                if g_idx < len(it.glyphs) - 1:
                    pen += t_gap
                elif name == "hyphen":
                    nxt_box = next((seg[j] for j in range(i + 1, min(len(seg), i + 3)) if isinstance(seg[j], Box)), None)
                    nxt_ok = (i + 1 < len(seg) and isinstance(seg[i + 1], Box)) or (i + 2 < len(seg) and isinstance(seg[i + 1], Penalty) and isinstance(seg[i + 2], Box))
                    if nxt_ok and nxt_box and nxt_box.glyphs:
                        nxt_g = nxt_box.glyphs[0]
                        if face is not None and nxt_g[0] is face and face.use_kern:
                            pen += math.floor(face.kern_units(name, nxt_g[1]) * face.S)
        elif isinstance(it, Glue):
            sp_w = it.width + extra_glue[i]
            s_meta = getattr(it, 'style_meta', None)
            if s_meta and (s_meta.get('underline') or s_meta.get('strike') or s_meta.get('bg')):
                out.append((None, '__space__', pen, sp_w, s_meta))
            pen += sp_w
            vis_word_idx += 1
            last_logical_w = None

    if hy:
        for h_tup in hy.glyphs:
            face, name, adv = h_tup[0], h_tup[1], h_tup[2]
            s_meta = dict(h_tup[3]) if (len(h_tup) > 3 and h_tup[3] is not None) else _make_g_meta(None, "-", "ltr", 0, is_synth_hy=True)
            s_meta["word_idx"] = vis_word_idx
            s_meta["logical_word_idx"] = last_logical_w if last_logical_w is not None else vis_word_idx
            s_meta["is_synthetic_hyphen"] = True
            out.append((face, name, pen, adv, s_meta))
            pen += adv

    return out, pen, hang_left
