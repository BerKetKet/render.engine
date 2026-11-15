
def _to_roman(n: int) -> str:
    vals = [(1000,"m"),(900,"cm"),(500,"d"),(400,"cd"),(100,"c"),(90,"xc"),(50,"l"),(40,"xl"),(10,"x"),(9,"ix"),(5,"v"),(4,"iv"),(1,"i")]
    res = []
    for v, s in vals:
        while n >= v:
            res.append(s)
            n -= v
    return "".join(res) or "i"

"""EPUB -> list of Blocks. Supports CSS, <pre>, <table>, <dl>/<dt>/<dd>, <ol>/<ul> nesting, inline/block <img>, cover canvas, and drop caps."""
import re, zipfile, posixpath, io, warnings
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from bs4 import BeautifulSoup, NavigableString, Tag, XMLParsedAsHTMLWarning
from PIL import Image
from .layout import Run

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

@dataclass
class Block:
    kind: str = "text"
    runs: List[Run] = field(default_factory=list)
    align: Optional[str] = None
    indent_em: Optional[float] = None
    left_em: float = 0.0
    right_em: float = 0.0
    scale: float = 1.0
    line_height: Optional[float] = None
    display: bool = False
    mt_em: float = 0.0
    mb_em: float = 0.0
    image: Optional[Image.Image] = None
    img_width_pct: Optional[float] = None
    is_cover: bool = False
    table_rows: list = field(default_factory=list)
    table_caption: Optional[str] = None
    pre_lines: List[str] = field(default_factory=list)
    bullet: Optional[str] = None
    ol_number: Optional[str] = None
    list_level: int = 0
    page_break_before: bool = False
    heading: int = 0
    next_is_heading: bool = False
    first_in_doc: bool = False
    first_after_heading: bool = False
    hyphenate: Optional[bool] = None
    lang: str = "en"
    drop_cap_letter: Optional[str] = None
    drop_cap_lines: int = 2
    drop_cap_bold: bool = False
    drop_cap_display: bool = True
    first_line_small_caps: bool = False
    border_collapse: bool = False
    is_spacer: bool = False
    chapter: str = ""

BLOCK_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "li", "ul", "ol", "pre",
              "hr", "table", "tr", "section", "article", "aside", "header", "footer", "figure", "figcaption",
              "dd", "dt", "dl", "nav", "body", "html", "td", "th", "tbody", "thead"}
INLINE_BOLD = {"b", "strong"}
INLINE_ITAL = {"i", "em", "cite", "dfn", "var"}
INLINE_CODE = {"code", "kbd", "tt", "samp"}

def _parse_css(text):
    rules = []
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    for m in re.finditer(r"([^{}]+)\{([^}]*)\}", text):
        sels, body = m.group(1), m.group(2)
        if sels.strip().startswith("@"):
            continue
        props = {}
        for decl in body.split(";"):
            if ":" in decl:
                k, v = decl.split(":", 1)
                props[k.strip().lower()] = v.strip().lower()
        for sel in sels.split(","):
            sel = sel.strip().lower()
            if sel:
                rules.append((sel, props))
    return rules

def _matches(sel, el):
    if "::first-letter" in sel or ":first-letter" in sel or "::first-line" in sel or ":first-line" in sel:
        return None
    sel = sel.split()[-1] if sel.split() else sel
    m = re.fullmatch(r"([a-z0-9*]*)(?:\.([a-z0-9_-]+))?(?:#([a-z0-9_-]+))?", sel)
    if not m:
        return None
    tag, cls, ident = m.groups()
    if tag and tag != "*" and tag != el.name:
        return None
    if cls and cls not in [c.lower() for c in (el.get("class") or [])]:
        return None
    if ident and ident != (el.get("id") or "").lower():
        return None
    return (100 if ident else 0) + (10 if cls else 0) + (1 if tag and tag != "*" else 0)

def _first_letter_lines(el, rules):
    for sel, props in rules:
        if "first-letter" in sel:
            base_sel = sel.split(":")[0]
            if _matches(base_sel, el) is not None:
                fs_v = props.get("font-size", "300%").strip()
                if fs_v.endswith("%"):
                    try:
                        if float(fs_v[:-1]) < 280.0:
                            return 2
                    except ValueError:
                        pass
                return 3
    return 0

def _has_first_line_sc_rule(el, rules):
    for sel, props in rules:
        if "first-line" in sel and props.get("font-variant") == "small-caps":
            base_sel = sel.split(":")[0]
            if _matches(base_sel, el) is not None:
                return True
    return False

def _style(el, rules):
    props = {}
    scored = []
    for sel, p in rules:
        s = _matches(sel, el)
        if s is not None:
            scored.append((s, p))
    for s, p in sorted(scored, key=lambda t: t[0]):
        props.update(p)
    inline = el.get("style")
    if inline:
        for decl in inline.split(";"):
            if ":" in decl:
                k, v = decl.split(":", 1)
                props[k.strip().lower()] = v.strip().lower()
    return props

CSS_FONT_SIZE_KEYWORDS = {
    "xx-small": 0.6,
    "x-small": 0.75,
    "small": 8.0 / 9.0,
    "medium": 1.0,
    "large": 1.2,
    "x-large": 1.5,
    "xx-large": 2.0,
    "smaller": 5.0 / 6.0,
    "larger": 1.2,
}

def _em(val, cfg, pct_base_px=None, use_root_em=False):
    if val is None:
        return None
    v_str = val.strip().lower()
    if v_str in CSS_FONT_SIZE_KEYWORDS:
        return CSS_FONT_SIZE_KEYWORDS[v_str]
    m = re.match(r"(-?[\d.]+)\s*(em|rem|px|pt|%)?", v_str)
    if not m:
        return None
    v, u = float(m.group(1)), m.group(2) or "px"
    sz = cfg.size26 / 64.0
    if u in ("em", "rem"):
        if use_root_em and abs(v) >= 1.99:
            return v * cfg.base_root_em_px() / sz
        return v
    if u == "px":
        return v * cfg.css_px_scale / sz
    if u == "pt":
        return v * (4 / 3.0) * cfg.css_px_scale / sz
    if u == "%":
        if pct_base_px is not None:
            return (v / 100.0) * pct_base_px / sz
        return v / 100.0
    return None

def _parse_color(val):
    if not val:
        return None
    val = val.strip().lower()
    if val.startswith("#"):
        h = val[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) == 6:
            try:
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            except ValueError:
                return None
    named = {
        "red": (192, 0, 0),
        "blue": (0, 0, 192),
        "black": (0, 0, 0),
    }
    return named.get(val)

def load_epub(path, cfg):
    z = zipfile.ZipFile(path)
    cont = BeautifulSoup(z.read("META-INF/container.xml"), "xml")
    opf_path = cont.find("rootfile")["full-path"]
    opf = BeautifulSoup(z.read(opf_path), "xml")
    base = posixpath.dirname(opf_path)
    manifest = {i["id"]: i for i in opf.find_all("item")}
    spine = [manifest[r["idref"]] for r in opf.find_all("itemref") if r["idref"] in manifest]
    blocks = []

    cover_item = None
    for item in manifest.values():
        props = item.get("properties", "")
        if "cover-image" in props:
            cover_item = item
            break
    if not cover_item:
        meta_cover = opf.find("meta", attrs={"name": "cover"})
        if meta_cover and meta_cover.get("content") in manifest:
            cover_item = manifest[meta_cover["content"]]

    if cover_item:
        cover_href = posixpath.normpath(posixpath.join(base, cover_item["href"]))
        try:
            im = Image.open(io.BytesIO(z.read(cover_href))).convert("RGB")
            blocks.append(Block(kind="image", image=im, is_cover=True, page_break_before=True, chapter="cover"))
        except Exception:
            pass

    for item in spine:
        if "html" not in item.get("media-type", ""):
            continue
        href = posixpath.normpath(posixpath.join(base, item["href"]))
        try:
            html = z.read(href)
        except KeyError:
            continue
        ch_name = posixpath.splitext(posixpath.basename(href))[0]
        doc_bs = _doc_blocks(z, href, html, cfg)
        for db in doc_bs:
            db.chapter = ch_name
        blocks.extend(doc_bs)
    return blocks

def _doc_blocks(z, href, html, cfg):
    soup = BeautifulSoup(html, "lxml")
    html_tag = soup.find("html")
    doc_lang = (html_tag.get("lang") or html_tag.get("xml:lang") or "en") if html_tag else "en"
    rules = []
    for st in soup.find_all("style"):
        rules += _parse_css(st.get_text())
    if z is not None:
        for ln in soup.find_all("link"):
            if "stylesheet" in (ln.get("rel") or []) or ln.get("type") == "text/css":
                p = posixpath.normpath(posixpath.join(posixpath.dirname(href), ln.get("href", "")))
                try:
                    rules += _parse_css(z.read(p).decode("utf-8", "ignore"))
                except KeyError:
                    pass
    body = soup.find("body") or soup
    out = []
    buf = []
    box_w = cfg.right - cfg.x0

    def flush(el_props=None, **kw):
        nonlocal buf
        has_img = any(getattr(r, 'image', None) is not None for r in buf)
        raw_txt = "".join(r.text for r in buf)
        txt = raw_txt.strip()
        if txt or has_img:
            runs = _collapse(buf)
            if kw.get("drop_cap_letter") is None and kw.get("_auto_first_letter", 0) > 0 and runs:
                first_txt = runs[0].text.lstrip()
                if first_txt and first_txt[0].isalpha():
                    kw["drop_cap_letter"] = first_txt[0]
                    kw["drop_cap_lines"] = int(kw["_auto_first_letter"])
                    kw["drop_cap_display"] = False
                    kw["drop_cap_bold"] = runs[0].bold
                    runs[0].text = first_txt[1:]
            kw.pop("_auto_first_letter", None)
            b = Block(runs=runs, **kw)
            out.append(b)
        elif "\u00a0" in raw_txt:
            kw.pop("_auto_first_letter", None)
            b = Block(runs=[], is_spacer=True, **kw)
            out.append(b)
        buf = []

    def walk(el, bold, italic, props_stack, in_phrasing=False,
             inh_left=0.0, inh_right=0.0, list_level=0, lang=doc_lang,
             inline_state=None, in_nav=False, parent_kw=None, outer_list=None):
        nonlocal buf
        if inline_state is None:
            inline_state = dict(
                scale=1.0, baseline_shift_em=0.0, small_caps=False,
                underline=False, strike=False, code=False,
                letter_spacing_em=0.0, word_spacing_em=0.0, fg=None, bg=None,
                text_transform=None, nowrap=False
            )
        try:
            ol_counter = int(el.get("start", 1)) if (el and el.name and el.name.lower() == "ol") else 1
        except (ValueError, TypeError):
            ol_counter = 1

        for ch in el.children:
            if isinstance(ch, NavigableString):
                if type(ch).__name__ in ("Comment", "Doctype", "ProcessingInstruction"):
                    continue
                s_txt = str(ch)
                tt = inline_state.get("text_transform")
                if tt == "uppercase":
                    s_txt = s_txt.upper()
                elif tt == "capitalize":
                    s_txt = re.sub(r"\b([a-z])", lambda m: m.group(1).upper(), s_txt)
                buf.append(Run(
                    s_txt, bold, italic,
                    scale=inline_state["scale"],
                    baseline_shift_em=inline_state["baseline_shift_em"],
                    small_caps=inline_state["small_caps"],
                    underline=inline_state["underline"],
                    strike=inline_state["strike"],
                    code=inline_state["code"],
                    letter_spacing_em=inline_state["letter_spacing_em"],
                    word_spacing_em=inline_state["word_spacing_em"],
                    fg=inline_state["fg"],
                    bg=inline_state.get("bg"),
                    nowrap=inline_state["nowrap"],
                    from_text_transform=(tt == "uppercase" and (parent_kw or {}).get("align") != "left")
                ))
                continue
            if not isinstance(ch, Tag):
                continue
            nm = ch.name.lower()
            props = _style(ch, rules)
            if props.get("display") == "none" or nm in ("script", "style", "head", "title"):
                continue

            ch_lang = ch.get("lang") or ch.get("xml:lang") or lang
            cur_in_nav = in_nav or (nm == "nav")

            is_dropcap = (props.get("float") == "left" and nm == "span")
            if is_dropcap and not buf:
                dc_text = ch.get_text().strip()
                if dc_text and len(dc_text) == 1 and dc_text.isalpha():
                    kw_dc = dict(
                        drop_cap_letter=dc_text,
                        drop_cap_lines=2,
                        drop_cap_display=True,
                        drop_cap_bold=bold or nm in INLINE_BOLD or props.get("font-weight") in ("bold", "700")
                    )
                    props_stack = kw_dc
                    continue

            b2 = bold or nm in INLINE_BOLD or props.get("font-weight") in ("bold", "700", "800", "900", "bolder")
            i2 = italic or nm in INLINE_ITAL or props.get("font-style") in ("italic", "oblique")
            if props.get("font-weight") in ("normal", "400"):
                b2 = False
            if props.get("font-style") == "normal":
                i2 = False

            new_inline = dict(inline_state)
            fs_em = _em(props.get("font-size"), cfg)
            if fs_em is not None and nm not in BLOCK_TAGS:
                new_inline["scale"] = inline_state["scale"] * fs_em
            if nm == "sup":
                new_inline["scale"] = inline_state["scale"] * (5.0 / 6.0)
                new_inline["baseline_shift_em"] = (-0.21 * cfg.pitch_px()) / (cfg.size_px() * (5.0 / 6.0))
            elif nm == "sub":
                new_inline["scale"] = inline_state["scale"] * (5.0 / 6.0)
                new_inline["baseline_shift_em"] = 13.0 / (cfg.size_px() * (5.0 / 6.0))
            elif nm == "small":
                new_inline["scale"] = inline_state["scale"] * (5.0 / 6.0)
            if props.get("font-variant") == "small-caps":
                new_inline["small_caps"] = True
            if props.get("text-transform") in ("uppercase", "capitalize"):
                new_inline["text_transform"] = props.get("text-transform")
            if props.get("white-space") == "nowrap":
                new_inline["nowrap"] = True

            if nm == "mark":
                new_inline["bg"] = (255, 255, 0)
            tdec = props.get("text-decoration", "")
            if nm in ("u", "ins") or "underline" in tdec or (nm == "a" and ch.get("href") and cur_in_nav):
                new_inline["underline"] = True
            if nm in ("s", "strike", "del") or "line-through" in tdec:
                new_inline["strike"] = True
            if nm in INLINE_CODE or "monospace" in props.get("font-family", ""):
                new_inline["code"] = True
            ls_em = _em(props.get("letter-spacing"), cfg)
            if ls_em is not None:
                new_inline["letter_spacing_em"] = ls_em
            ws_em = _em(props.get("word-spacing"), cfg)
            if ws_em is not None:
                new_inline["word_spacing_em"] = ws_em
            col = _parse_color(props.get("color"))
            if col is not None:
                new_inline["fg"] = col
            elif nm == "a" and ch.get("href") and cur_in_nav and new_inline["fg"] is None:
                new_inline["fg"] = (0, 0, 255)

            if nm == "br":
                buf.append(Run("\n", bold, italic))
                continue
            if nm == "img":
                im = _load_img(z, href, ch)
                if im is not None:
                    parent_txt = el.get_text().strip() if el else ""
                    if (in_phrasing and parent_txt) or props.get("display") == "inline":
                        buf.append(Run("", bold, italic, image=im))
                    else:
                        flush(**(parent_kw or {}))
                        if parent_kw:
                            parent_kw["bullet"] = None
                            parent_kw["ol_number"] = None
                        w_pct = None
                        if props.get("width") and "%" in props.get("width", ""):
                            try:
                                w_pct = float(props["width"].replace("%", "").strip()) / 100.0
                            except ValueError:
                                w_pct = None
                        has_col_css = any(sel == "table" and p.get("border-collapse") == "collapse" for sel, p in rules)
                        out.append(Block(kind="image", image=im, img_width_pct=w_pct, align="center", left_em=inh_left, right_em=inh_right, border_collapse=has_col_css))
                continue
            if nm == "hr":
                flush(**(parent_kw or {}))
                if parent_kw:
                    parent_kw["bullet"] = None
                    parent_kw["ol_number"] = None
                has_col_css = any(sel == "table" and p.get("border-collapse") == "collapse" for sel, p in rules)
                out.append(Block(kind="hr", border_collapse=has_col_css))
                continue
            if nm == "pre":
                flush(**(parent_kw or {}))
                if parent_kw:
                    parent_kw["bullet"] = None
                    parent_kw["ol_number"] = None
                raw_pre = ch.get_text().strip("\r\n")
                has_col_css = any(sel == "table" and p.get("border-collapse") == "collapse" for sel, p in rules)
                out.append(Block(kind="pre", pre_lines=raw_pre.splitlines(), border_collapse=has_col_css))
                continue
            if nm == "table":
                flush(**(parent_kw or {}))
                if parent_kw:
                    parent_kw["bullet"] = None
                    parent_kw["ol_number"] = None
                cap_el = ch.find("caption")
                cap_txt = cap_el.get_text().strip() if cap_el else None
                rows = []
                for tr in ch.find_all("tr"):
                    row = []
                    for cell in tr.find_all(["th", "td"]):
                        c_props = _style(cell, rules)
                        is_h = (cell.name.lower() == "th")
                        c_align = c_props.get("text-align") or ("center" if is_h else "left")
                        try:
                            cs = max(1, int(cell.get("colspan", 1)))
                        except (ValueError, TypeError):
                            cs = 1
                        try:
                            rs = max(1, int(cell.get("rowspan", 1)))
                        except (ValueError, TypeError):
                            rs = 1
                        row.append((cell.get_text().strip(), is_h, c_align, cs, rs))
                    if row:
                        rows.append(row)
                if rows:
                    is_col_tbl = (props.get("border-collapse") == "collapse") or any(sel == "table" and p.get("border-collapse") == "collapse" for sel, p in rules)
                    out.append(Block(kind="table", table_rows=rows, table_caption=cap_txt, border_collapse=is_col_tbl))
                continue

            if nm in BLOCK_TAGS:
                if parent_kw:
                    flush(**parent_kw)
                    parent_kw["bullet"] = None
                    parent_kw["ol_number"] = None
                else:
                    flush()
                hyph_prop = props.get("hyphens") or props.get("-webkit-hyphens")
                hyph_flag = False if hyph_prop in ("none", "manual") else (True if hyph_prop == "auto" else None)

                has_col_css = any(sel == "table" and p.get("border-collapse") == "collapse" for sel, p in rules)
                ml_val = _em(props.get("margin-left"), cfg, pct_base_px=box_w, use_root_em=True) or 0.0
                cur_left = inh_left + ml_val
                cur_right = inh_right + (_em(props.get("margin-right"), cfg, pct_base_px=box_w, use_root_em=True) or 0.0)
                cur_list_level = list_level

                if nm in ("blockquote", "figure"):
                    bq_em = (cfg.blockquote_margin_ratio * (cfg.right - cfg.x0)) / cfg.size_px()
                    cur_left += bq_em
                    cur_right += bq_em
                elif nm in ("ul", "ol"):
                    cur_list_level += 1

                lh_val = None
                if props.get("line-height"):
                    m_lh = re.match(r"([\d.]+)", props.get("line-height").strip())
                    if m_lh:
                        lh_val = float(m_lh.group(1))

                ti_raw = (props.get("text-indent") or "").strip()
                kw = dict(
                    align=props.get("text-align") or ("right" if (ch.get("dir") == "rtl" or props.get("direction") == "rtl") else None),
                    indent_em=_em(props.get("text-indent"), cfg, pct_base_px=box_w, use_root_em=ti_raw.startswith("-")),
                    scale=(fs_em if (fs_em is not None and nm in ("p", "div", "li", "dd", "dt")) else 1.0),
                    left_em=cur_left,
                    right_em=cur_right,
                    line_height=lh_val,
                    mt_em=_em(props.get("margin-top"), cfg) or 0.0,
                    mb_em=_em(props.get("margin-bottom"), cfg) or 0.0,
                    hyphenate=hyph_flag,
                    lang=ch_lang,
                    list_level=cur_list_level,
                    first_line_small_caps=_has_first_line_sc_rule(ch, rules),
                    border_collapse=has_col_css,
                    _auto_first_letter=_first_letter_lines(ch, rules),
                    page_break_before=props.get("page-break-before") in ("always", "page") or
                                      props.get("break-before") in ("page", "always")
                )
                if props_stack and isinstance(props_stack, dict):
                    kw.update(props_stack)
                    props_stack = None

                if nm[0] == "h" and len(nm) == 2 and nm[1].isdigit():
                    lvl = min(int(nm[1]), 6) - 1
                    scale_val = cfg.heading_scale[lvl]
                    use_disp = cfg.use_display_for_headings or (
                        cfg.optical_sizing and scale_val * (cfg.size26 / 64.0) >= cfg.display_threshold_px
                    )
                    kw.update(
                        scale=scale_val,
                        display=use_disp,
                        mt_em=kw["mt_em"] if kw["mt_em"] else cfg.heading_margin_top_em[lvl],
                        mb_em=kw["mb_em"] if kw["mb_em"] else cfg.heading_margin_bottom_em[lvl],
                        heading=int(nm[1])
                    )
                    if kw["align"] is None:
                        kw["align"] = "left"
                    if kw["right_em"] == 0.0:
                        kw["right_em"] = getattr(cfg, "heading_right_margin_em", 0.0)

                if nm in ("blockquote", "figure"):
                    kw["mt_em"] = max(kw["mt_em"], 1.0)
                    kw["mb_em"] = max(kw["mb_em"], 1.0)
                is_multi_dd_dl = bool(el and el.name == "dl" and len(el.find_all("dd", recursive=False)) > len(el.find_all("dt", recursive=False)))
                if nm == "dd":
                    kw["left_em"] += (1.0 if is_multi_dd_dl else (cfg.blockquote_margin_ratio * (cfg.right - cfg.x0)) / cfg.size_px())
                    if not is_multi_dd_dl:
                        kw["mb_em"] = max(kw["mb_em"], 1.0)
                if nm == "dt":
                    if kw["align"] is None and not is_multi_dd_dl:
                        kw["align"] = "left"
                    if not is_multi_dd_dl:
                        kw["mt_em"] = max(kw["mt_em"], 1.0)
                if nm == "li":
                    lvl_eff = max(1, cur_list_level)
                    parent_nm = el.name.lower() if el and el.name else "ul"
                    p_props = _style(el, rules) if el else {}
                    lst_type = p_props.get("list-style-type") or props.get("list-style-type") or ""
                    ol_type = (el.get("type") if el else None) or ""
                    if lst_type == "none":
                        kw["left_em"] = inh_left + 1.0
                        kw["bullet"] = None
                        kw["ol_number"] = None
                    elif parent_nm == "ol":
                        ol_start_val = 1
                        try:
                            ol_start_val = int(el.get("start", 1))
                        except (ValueError, TypeError):
                            pass
                        ol_max_val = ol_start_val + len(el.find_all("li", recursive=False)) - 1
                        extra_digits_em = 0.625 * max(0, len(str(max(1, ol_max_val))) - 2)
                        if ol_type == "a" or lst_type in ("lower-alpha", "lower-latin"):
                            kw["left_em"] = inh_left + (lvl_eff - 1) * 2.0 + 2.0
                            kw["ol_number"] = f"{chr(ord('a') + (ol_counter - 1) % 26)}."
                        elif ol_type == "A" or lst_type in ("upper-alpha", "upper-latin"):
                            kw["left_em"] = inh_left + (lvl_eff - 1) * 2.0 + 2.0
                            kw["ol_number"] = f"{chr(ord('A') + (ol_counter - 1) % 26)}."
                        elif ol_type == "i" or lst_type == "lower-roman":
                            kw["left_em"] = inh_left + (lvl_eff - 1) * 2.0 + (132.0 / cfg.size_px())
                            kw["ol_number"] = f"{_to_roman(ol_counter)}."
                        elif ol_type == "I" or lst_type == "upper-roman":
                            kw["left_em"] = inh_left + (lvl_eff - 1) * 2.0 + (132.0 / cfg.size_px())
                            kw["ol_number"] = f"{_to_roman(ol_counter).upper()}."
                        else:
                            base_ol = getattr(cfg, "ol_indent_em", 2.0952)
                            kw["left_em"] = inh_left + ((lvl_eff - 1) * 2.0 + base_ol if outer_list == "ul" else lvl_eff * base_ol) + extra_digits_em
                            kw["ol_number"] = f"{ol_counter}."
                        ol_counter += 1
                    else:
                        ul_base = getattr(cfg, "ul_indent_em", 2.0000)
                        ul_nest = getattr(cfg, "ul_nested_indent_em", 1.9762)
                        kw["left_em"] = inh_left + ul_base + (lvl_eff - 1) * ul_nest
                        if lst_type == "square":
                            kw["bullet"] = "\u25a0"
                        else:
                            kw["bullet"] = "\u2022" if lvl_eff == 1 else ("\u25e6" if lvl_eff == 2 else "\u25aa")
                    if cur_in_nav and kw["align"] is None:
                        kw["align"] = "left"

                is_p_like = nm in ("p", "dd", "dt", "li", "figcaption", "h1", "h2", "h3", "h4", "h5", "h6")
                p_before = len(out)
                walk(ch, b2 if nm[0] != "h" else True, i2, None,
                     in_phrasing=is_p_like, inh_left=cur_left, inh_right=cur_right,
                     list_level=cur_list_level, lang=ch_lang, inline_state=new_inline,
                     in_nav=cur_in_nav, parent_kw=kw if is_p_like else None, outer_list=(outer_list or (nm if nm in ("ul", "ol") else None)))
                flush(**kw)
                if nm in ("ul", "ol") and cur_list_level == 1 and len(out) > p_before and not cur_in_nav:
                    out[p_before].mt_em = max(out[p_before].mt_em, 1.0)
                    out[-1].mb_em = max(out[-1].mb_em, 1.0)
                elif nm in ("blockquote", "figure", "dl") and len(out) > p_before:
                    out[p_before].mt_em = max(out[p_before].mt_em, 1.0)
                    out[-1].mb_em = max(out[-1].mb_em, 1.0)
            else:
                walk(ch, b2, i2, props_stack, in_phrasing=in_phrasing,
                     inh_left=inh_left, inh_right=inh_right,
                     list_level=list_level, lang=ch_lang, inline_state=new_inline,
                     in_nav=cur_in_nav, parent_kw=parent_kw)

    walk(body, False, False, None)
    flush()
    for idx_b in range(len(out) - 1):
        out[idx_b].next_is_heading = (out[idx_b + 1].heading > 0)
    if out:
        out[0].page_break_before = True
        seen_text = False
        after_heading = False
        for b in out:
            if b.kind == "text":
                if b.heading > 0:
                    after_heading = True
                else:
                    if not seen_text:
                        b.first_in_doc = True
                        seen_text = True
                    if after_heading:
                        b.first_after_heading = True
                        after_heading = False
    return out

def _collapse(runs):
    res, prev_space = [], True
    for r in runs:
        if getattr(r, 'image', None) is not None:
            res.append(r)
            prev_space = False
            continue
        t = r.text
        if t == "\n":
            res.append(r)
            prev_space = True
            continue
        t = t.replace("\u200b", "")
        out = []
        for c in t:
            if c in " \t\r\n":
                if not prev_space:
                    out.append(" ")
                    prev_space = True
            else:
                out.append(c)
                prev_space = False
        if out:
            r_copy = Run(
                "".join(out), r.bold, r.italic, r.image,
                scale=r.scale, baseline_shift_em=r.baseline_shift_em,
                small_caps=r.small_caps, underline=r.underline,
                strike=r.strike, code=r.code,
                letter_spacing_em=r.letter_spacing_em,
                word_spacing_em=r.word_spacing_em, fg=r.fg,
                nowrap=getattr(r, 'nowrap', False),
                from_text_transform=getattr(r, 'from_text_transform', False)
            )
            res.append(r_copy)
    while res and getattr(res[-1], 'image', None) is None and res[-1].text.strip(" \t\r\n") == "" and res[-1].text != "\n":
        res.pop()
    if res and getattr(res[-1], 'image', None) is None and res[-1].text.endswith(" "):
        res[-1].text = res[-1].text.rstrip(" ")
    return res

def _load_img(z, href, tag):
    src = tag.get("src") or tag.get("xlink:href")
    if not src or z is None:
        return None
    p = posixpath.normpath(posixpath.join(posixpath.dirname(href), src))
    try:
        return Image.open(io.BytesIO(z.read(p))).convert("RGB")
    except Exception:
        return None
