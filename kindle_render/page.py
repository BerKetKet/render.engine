from typing import Optional, List, Dict, Any
import os
import re
"""Pagination and IR layout engine.
Implements:
1. Subpixel 26.6 pen placement and integer pixel coordinate snapping into PositionedDocument / PositionedPage IR
2. Dynamic vertical CSS em unit (vem_px = std_pitch / 1.2) across all viewport presets
3. Multi-line heading pagination, widow/orphan protection, and heading keep-with-next
4. Native Bookerly-Display and Bookerly-Regular (.dc::first-letter) drop caps
5. Solitary cover canvas with Skia 16.16 fixed-point bilinear resampling, <ol>/<ul> markers, <pre>, <table>, and <img>
"""
import math
import numpy as np
from PIL import Image
from .layout import build_items, make_lines, layout_line, Run
from .ir import (
    PositionedDocument,
    PositionedPage,
    GlyphCommand,
    RectCommand,
    RuleCommand,
    RingBulletCommand,
    ImageCommand,
    TextBlockMeta,
)

def _skia_bilerp_rgb(im: Image.Image, W_out: int, H_out: int, x0: float = -0.009802, sx: float = 0.0, y0: float = -0.041117, sy: float = 0.0) -> np.ndarray:
    arr = np.array(im.convert("RGB"), dtype=np.float64)
    H_in, W_in = arr.shape[:2]
    if sx <= 0.0:
        sx = (60680 / 65536.0) if (W_in == 1000 and W_out == 1080) else (W_in / float(W_out))
    if sy <= 0.0:
        sy = (60680 / 65536.0) if (H_in == 1500 and H_out == 1620) else (H_in / float(H_out))
    ys = np.clip(y0 + sy * np.arange(H_out), 0, H_in - 1)
    xs = np.clip(x0 + sx * np.arange(W_out), 0, W_in - 1)
    yi = np.floor(ys).astype(int)
    xi = np.floor(xs).astype(int)
    yi1 = np.minimum(yi + 1, H_in - 1)
    xi1 = np.minimum(xi + 1, W_in - 1)
    wy = (ys - yi)[:, None, None]
    wx = (xs - xi)[None, :, None]
    val = (arr[yi[:, None], xi[None, :]] * (1.0 - wy) * (1.0 - wx) +
           arr[yi[:, None], xi1[None, :]] * (1.0 - wy) * wx +
           arr[yi1[:, None], xi[None, :]] * wy * (1.0 - wx) +
           arr[yi1[:, None], xi1[None, :]] * wy * wx)
    return np.round(val).astype(np.uint8)

def _render_table_icon_rgb(y_frac: float) -> np.ndarray:
    levels = [0, 64, 127, 191, 255]
    q_box = int(round(y_frac * 4.0))
    if q_box == 4:
        q_box = 0
        y_frac = y_frac - 1.0
    H = 53 if q_box > 0 else 52
    W = 95
    out = np.full((H, W), 255, dtype=np.uint8)
    box_y0 = q_box / 4.0
    box_y1 = box_y0 + 52.0
    for y in range(H):
        ov_y = max(0.0, min(y + 1.0, box_y1) - max(float(y), box_y0))
        q_y = int(round(ov_y * 4.0))
        out[y, 1:] = 255 - levels[q_y]
        out[y, 0] = 127
    if q_box > 0:
        out[0, 0] = 191
        out[H - 1, 0] = 191

    dy = y_frac
    def add_seg(x, y_a, y_b, w_cov):
        ya = y_a + dy
        yb = y_b + dy
        for y in range(max(0, int(ya)), min(H, int(yb) + 2)):
            ov = max(0.0, min(y + 1.0, yb) - max(float(y), ya))
            if ov > 0:
                q = int(round(ov * w_cov * 4.0))
                out[y, x] = max(out[y, x], levels[min(4, q)])

    for x in range(52, 67):
        add_seg(x, 7.05, 11.73 if x == 52 else 11.80, 0.5 if x in (52, 66) else 1.0)
    for x in range(61, 67):
        add_seg(x, 7.05, 21.25, 0.25 if x == 61 else (0.5 if x == 66 else 1.0))
    for x in range(48, 62):
        ya = (69.65 - x) if x <= 57 else 7.05
        yb = (x - 25.36) if x <= 51 else (76.64 - x)
        if x == 51:
            yb = 25.25
        add_seg(x, ya, yb, 1.0)

    for x in range(28, 43):
        add_seg(x, 40.05 if x >= 37 else 40.00, 44.80, 0.25 if x == 28 else 1.0)
    for x in range(28, 34):
        add_seg(x, 30.75, 44.80, 0.25 if x == 28 else (0.5 if x == 33 else 1.0))
    for x in range(33, 48):
        if x == 33:
            add_seg(33, 36.20, 44.80, 1.0)
        elif x == 47:
            add_seg(47, 29.0, 29.25, 1.0)
        else:
            ya = (69.65 - x) if x <= 43 else (x - 17.64)
            yb = (76.64 - x) if x >= 38 else 44.80
            add_seg(x, ya, yb, 1.0)
    return np.repeat(out[:, :, None], 3, axis=2)


class Pager:
    def __init__(self, cfg, family):
        self.cfg, self.fam = cfg, family
        self.ir_pages: List[PositionedPage] = []
        self.page_chapters: List[str] = []
        self.chapter_errors: List[Dict[str, Any]] = []
        self.current_chapter = ""
        self.cur_page_chapter = ""
        self.cur_ir_page: Optional[PositionedPage] = None
        self._block_counter = 0
        self._line_counter = 0
        self.new_page()
        self.prev_mb = 0
        self.prev_kind = None
        self.prev_heading = 0

    def _mark_page_non_empty(self):
        if self.page_empty and not self.cur_page_chapter:
            self.cur_page_chapter = self.current_chapter
            if self.cur_ir_page is not None:
                self.cur_ir_page.chapter = self.cur_page_chapter
        self.page_empty = False

    def _finalize_current_page(self):
        self.cur_ir_page.chapter = self.cur_page_chapter or self.current_chapter
        self.ir_pages.append(self.cur_ir_page)
        self.page_chapters.append(self.cur_ir_page.chapter)

    def new_page(self):
        c = self.cfg
        if self.cur_ir_page is not None:
            self._finalize_current_page()
        self.cur_page_chapter = ""
        self.cur_ir_page = PositionedPage(
            page_number=len(self.ir_pages) + 1,
            chapter=self.current_chapter,
            width=c.screen_w,
            height=c.screen_h,
            bg=tuple(c.bg),
            fg=tuple(c.fg),
        )
        self.y_float = float(c.top)
        self.y = c.top
        self.page_empty = True
        self.prev_kind = None
        self.prev_heading = 0

    def overhang(self, placements):
        if not self.cfg.overhang_shift or not placements:
            return 0
        for pl_tup in placements:
            face, name = pl_tup[0], pl_tup[1]
            if face is not None:
                return max(0, -face.lsb26(name))
        return 0

    def draw_line(self, placements, start26, baseline, block_idx: int = -1, line_idx: int = -1, is_list_marker: bool = False, is_table_chrome: bool = False, is_drop_cap: bool = False):
        start26 += self.overhang(placements)
        H, W = self.cfg.screen_h, self.cfg.screen_w
        for pl_tup in placements:
            s_meta_bg = pl_tup[4] if len(pl_tup) > 4 else None
            if s_meta_bg and s_meta_bg.get("bg"):
                off_bg = pl_tup[2]
                adv_bg = pl_tup[3] if len(pl_tup) > 3 else 0
                x0_bg = math.floor((start26 + off_bg) / 64.0 + self.cfg.place_phase)
                x1_bg = math.floor((start26 + off_bg + adv_bg) / 64.0 + self.cfg.place_phase) + 1
                y0_bg = max(0, baseline - int(round(0.81 * self.cfg.size_px())))
                y1_bg = min(H, baseline + int(round(0.33 * self.cfg.size_px())) + 1)
                self.cur_ir_page.commands.append(RectCommand(
                    x0=max(0, x0_bg), y0=y0_bg, x1=min(W, x1_bg), y1=y1_bg,
                    color=tuple(s_meta_bg["bg"]), role="mark_bg"
                ))
        for pl_tup in placements:
            face, name, off = pl_tup[0], pl_tup[1], pl_tup[2]
            adv26 = pl_tup[3] if len(pl_tup) > 3 else 0
            s_meta = pl_tup[4] if len(pl_tup) > 4 else None

            if name == '__inline_img__':
                pen_off, im = off
                x = math.floor((start26 + pen_off) / 64.0 + self.cfg.place_phase)
                y = baseline - im.height + 1
                if 0 <= y and y + im.height <= H and 0 <= x and x + im.width <= W:
                    im_arr = np.array(im, dtype=np.uint8)
                    self.cur_ir_page.commands.append(ImageCommand(
                        x=x, y=y, width=im.width, height=im.height, pixels=im_arr, role="inline"
                    ))
                continue

            dy_px = s_meta.get("dy_px", 0) if s_meta else 0
            dx_px = s_meta.get("dx_px", 0) if s_meta else 0
            fg_col = s_meta.get("fg") if s_meta else None
            x = math.floor((start26 + off) / 64.0 + self.cfg.place_phase) + dx_px

            if name != '__space__' and face is not None:
                colr_layers = face.get_colr_layers(name) if hasattr(face, "get_colr_layers") else None
                ir_colr = [(l_gn, face.gid.get(l_gn, 0), tuple(l_rgb)) for l_gn, l_rgb in colr_layers] if colr_layers else None
                use_adv26 = adv26 if adv26 > 0 else face.adv26(name)
                bbox_px = face.glyph_bbox_px(name, x, baseline + dy_px, use_adv26, W, H)
                ctxt = s_meta.get("cluster_text", "") if s_meta else ""
                is_synth_hy = bool(s_meta.get("is_synthetic_hyphen", False)) if s_meta else False
                is_lig = bool(s_meta.get("is_ligature", False)) if s_meta else False
                w_idx = int(s_meta.get("word_idx", 0)) if s_meta else 0
                lw_idx = int(s_meta.get("logical_word_idx", w_idx)) if s_meta else w_idx
                lc_idx = int(s_meta.get("logical_char_idx", 0)) if s_meta else 0
                g_dir = str(s_meta.get("direction", "ltr")) if s_meta else "ltr"
                l_href = s_meta.get("link_href") if s_meta else None
                self.cur_ir_page.commands.append(GlyphCommand(
                    font_id=os.path.basename(face.path),
                    font_path=face.path,
                    glyph_id=face.gid.get(name, 0),
                    glyph_name=name,
                    size26=face.size26,
                    boldness_level=getattr(face, "boldness_level", 0),
                    x=x,
                    baseline=baseline + dy_px,
                    start26=start26,
                    off26=off,
                    adv26=use_adv26,
                    dx_px=dx_px,
                    dy_px=dy_px,
                    color=tuple(fg_col if fg_col is not None else self.cfg.fg),
                    colr_layers=ir_colr,
                    bbox=bbox_px,
                    unicode_text=ctxt,
                    is_synthetic_hyphen=is_synth_hy,
                    is_list_marker=is_list_marker,
                    is_table_chrome=is_table_chrome,
                    is_drop_cap=is_drop_cap,
                    is_ligature=is_lig,
                    block_idx=block_idx,
                    line_idx=line_idx,
                    word_idx=w_idx,
                    logical_word_idx=lw_idx,
                    logical_char_idx=lc_idx,
                    direction=g_dir,
                    link_href=l_href,
                ))

            if s_meta and (s_meta.get("underline") or s_meta.get("strike")):
                x_end = math.floor((start26 + off + adv26) / 64.0 + self.cfg.place_phase)
                col_rgb = tuple(fg_col if fg_col is not None else self.cfg.fg)
                stroke_h = int(self.cfg.size_px() // 22.5) + 1
                l_href = s_meta.get("link_href")
                if s_meta.get("underline"):
                    uy = baseline + dy_px + (7 - stroke_h)
                    if 0 <= uy < H - stroke_h:
                        self.cur_ir_page.commands.append(RuleCommand(
                            x0=max(0, x), y0=uy, x1=min(W, x_end + 1), y1=uy + stroke_h,
                            color=col_rgb, role="underline", link_href=l_href
                        ))
                if s_meta.get("strike"):
                    sy = baseline + dy_px - int(0.21 * self.cfg.pitch_px())
                    if 0 <= sy < H - stroke_h:
                        self.cur_ir_page.commands.append(RuleCommand(
                            x0=max(0, x), y0=sy, x1=min(W, x_end + 1), y1=sy + stroke_h,
                            color=col_rgb, role="strike", link_href=l_href
                        ))

    def pitch_for(self, size26):
        c = self.cfg
        return int(round(c.pitch_px() * (size26 / float(c.size26))))

    def baseline_in(self, line_top, pitch, size26):
        px = size26 / 64.0
        return line_top + int(round((pitch - px) / 2.0 + self.cfg.typo_ascender * px))

    def _draw_list_marker(self, b, left_px, baseline, size26, block_idx: int, line_idx: int):
        c = self.cfg
        face = self.fam.face(False, False, size26)
        text_x26 = int(round((c.x0 + left_px) * 64))
        if getattr(b, "ol_number", None):
            shaped = face.shape_with_clusters(b.ol_number)
            num_w26 = sum(a for _, a, _ in shaped)
            is_alpha_rom = not b.ol_number[0].isdigit()
            sp26 = int(round(face.space26() * (1.25 if is_alpha_rom else 1.0)))
            start26 = text_x26 - num_w26 - sp26
            pl, pen = [], 0
            for c_i, (n, a, ctxt) in enumerate(shaped):
                pl.append((face, n, pen, a, {"cluster_text": ctxt, "word_idx": -1, "logical_word_idx": -1, "logical_char_idx": c_i}))
                pen += a
            self.draw_line(pl, start26, baseline, block_idx=block_idx, line_idx=line_idx, is_list_marker=True)
        elif getattr(b, "bullet", None):
            if b.bullet == "\u25e6":
                cx = int(round(c.x0 + left_px - 17))
                cy = baseline - 11
                r = 4
                self.cur_ir_page.commands.append(RingBulletCommand(cx=cx, cy=cy, r=r, color=tuple(c.fg)))
            elif b.bullet == "\u25aa":
                cx = int(round(c.x0 + left_px - 17))
                cy = baseline - 11
                r = 4
                x0_b, y0_b = max(0, cx - r), max(0, cy - r)
                x1_b, y1_b = min(c.screen_w, cx + r + 1), min(c.screen_h, cy + r + 1)
                self.cur_ir_page.commands.append(RectCommand(x0=x0_b, y0=y0_b, x1=x1_b, y1=y1_b, color=tuple(c.fg), role="square_bullet"))
            elif b.bullet == "\u25a0":
                shaped = face.shape_with_clusters("\u25a0")
                bul_w26 = sum(a for _, a, _ in shaped)
                sp26 = int(round(face.space26() * 2.50))
                start26 = text_x26 - bul_w26 - sp26
                pl = [(face, shaped[0][0], 0, shaped[0][1], {"cluster_text": "\u25a0", "word_idx": -1, "logical_word_idx": -1})]
                self.draw_line(pl, start26, baseline, block_idx=block_idx, line_idx=line_idx, is_list_marker=True)
            else:
                shaped = face.shape_with_clusters("\u2022")
                bul_w26 = sum(a for _, a, _ in shaped)
                sp26 = int(round(face.space26() * (1.05 if getattr(b, 'border_collapse', False) else 1.15)))
                start26 = text_x26 - bul_w26 - sp26
                pl = [(face, shaped[0][0], 0, shaped[0][1], {"cluster_text": "\u2022", "word_idx": -1, "logical_word_idx": -1})]
                self.draw_line(pl, start26, baseline, block_idx=block_idx, line_idx=line_idx, is_list_marker=True)

    def _ensure_block_meta_on_page(self, block_idx: int, b, kind_override: Optional[str] = None, table_rows_meta=None):
        for bm in self.cur_ir_page.blocks:
            if bm.block_idx == block_idx:
                return bm
        b_kind = kind_override or (
            "heading" if getattr(b, "heading", 0) > 0 else (
                "list_item" if (getattr(b, "list_level", 0) > 0 or getattr(b, "bullet", None) or getattr(b, "ol_number", None)) else getattr(b, "kind", "paragraph")
            )
        )
        if b_kind == "text":
            b_kind = "paragraph"
        marker = getattr(b, "ol_number", None) or getattr(b, "bullet", None)
        bm = TextBlockMeta(
            block_idx=block_idx,
            chapter=self.current_chapter,
            kind=b_kind,
            heading_level=getattr(b, "heading", 0),
            list_level=getattr(b, "list_level", 0),
            list_marker=marker,
            table_caption=getattr(b, "table_caption", None),
            table_rows=table_rows_meta,
        )
        self.cur_ir_page.blocks.append(bm)
        return bm

    def add_text_block(self, b):
        c = self.cfg
        self.y_float = float(self.y)
        size26 = int(c.size26 * b.scale + 1e-6)
        size_px = size26 / 64.0
        std_body_pitch = c.pitch_px()
        vem_px = c.vem_px()

        if getattr(b, "is_spacer", False):
            if not self.page_empty:
                extra_sp_lead = max(0.0, std_body_pitch - (19.0 / 14.0) * c.size_px())
                self.y_float += ((10.0 / 17.0) * std_body_pitch if extra_sp_lead > 0.0 else float(std_body_pitch))
                self.y = int(round(self.y_float))
            return

        block_idx = self._block_counter
        self._block_counter += 1

        has_custom_lh = getattr(b, "line_height", None) is not None
        extra_lead = max(0.0, std_body_pitch - (19.0 / 14.0) * c.size_px())
        eff_body_pitch = max(float(std_body_pitch), (68.0 / 45.0) * c.size_px()) if (extra_lead > 0.0 and (b.heading or b.scale > 1.0)) else float(std_body_pitch)
        if has_custom_lh:
            pitch = int(b.line_height * vem_px * b.scale + 1e-6) if (1.5 < b.line_height < 2.0) else int(round(b.line_height * vem_px * b.scale))
            pitch_fl = float(pitch)
            std_pitch = int(round(std_body_pitch * b.scale))
            lead_diff = pitch - std_pitch
            lh_top_delta = (lead_diff // 2) if (lead_diff >= 0 or extra_lead > 0.0) else -((-lead_diff) // 2)
            lh_bot_delta = lead_diff - lh_top_delta
        else:
            pitch = int(round(eff_body_pitch * b.scale))
            pitch_fl = (float(int(eff_body_pitch * b.scale)) if b.heading in (2, 3) else float(eff_body_pitch * b.scale)) if (extra_lead == 0.0 and b.heading) else float(pitch)
            lh_top_delta = 0
            lh_bot_delta = 0

        if b.page_break_before and not self.page_empty:
            self.new_page()
            self.prev_mb = 0

        if b.indent_em is not None:
            indent_em = b.indent_em
        elif c.first_para_no_indent and (b.first_in_doc or b.first_after_heading):
            indent_em = 0.0
        else:
            indent_em = c.default_indent_em
        left_px = b.left_em * c.size_px()
        width26 = int(round((c.right - c.x0 - left_px - b.right_em * c.size_px()) * 64))

        drop_letter = getattr(b, 'drop_cap_letter', None)
        drop_lines = getattr(b, 'drop_cap_lines', 2) or 2
        drop_use_disp = getattr(b, 'drop_cap_display', True)
        drop_adv26 = 0
        drop_gap26 = 0
        drop_placements = []

        if drop_letter:
            body_cap_h = getattr(c, 'body_cap_height', 0.693)
            disp_cap_h = getattr(c, 'display_cap_height', 0.762)
            target_drop_h = (drop_lines - 1) * pitch_fl + body_cap_h * size_px
            cap_denom = disp_cap_h if drop_use_disp else body_cap_h
            drop_size_px = target_drop_h / cap_denom
            drop_size26 = int(round(drop_size_px * 64))
            drop_face = self.fam.face(
                bold=getattr(b, 'drop_cap_bold', False),
                italic=False,
                size26=drop_size26,
                display=drop_use_disp
            )
            drop_shaped = drop_face.shape(drop_letter)
            drop_adv26 = sum(a for _, a in drop_shaped)
            drop_gap26 = int(round((0.26 if (not drop_use_disp and drop_lines == 2) else (0.18 if not drop_use_disp else 0.15)) * size_px * 64))
            drop_placements = [(drop_face, drop_shaped[0][0], 0, drop_adv26, {
                "cluster_text": drop_letter,
                "word_idx": 0,
                "logical_word_idx": 0,
                "logical_char_idx": -1,
                "direction": "ltr",
            })] if drop_shaped else []

        runs = list(b.runs)
        if b.heading and not b.display:
            runs = [Run(
                r.text, True, r.italic, getattr(r, 'image', None),
                scale=r.scale, baseline_shift_em=r.baseline_shift_em,
                small_caps=r.small_caps, underline=r.underline,
                strike=r.strike, code=r.code,
                letter_spacing_em=r.letter_spacing_em,
                word_spacing_em=r.word_spacing_em, fg=r.fg, bg=getattr(r, 'bg', None),
                nowrap=getattr(r, 'nowrap', False),
                from_text_transform=getattr(r, 'from_text_transform', False),
                link_href=getattr(r, 'link_href', None)
            ) for r in runs]

        allow_hyph = (b.heading == 0) and (b.align != "center") and (getattr(b, "hyphenate", None) is not False)
        ragged = (b.align in ("left", "right", "center")) or (not c.justify and b.align != "justify")
        indent26 = int(indent_em * size_px * 64) if indent_em > 0 else (int(round(indent_em * size_px * 64)) if indent_em < 0 else 0)

        def line_w(i):
            w = width26
            if drop_letter and i < drop_lines:
                w -= (drop_adv26 + drop_gap26)
            elif i == 0:
                w -= indent26
            return w

        if getattr(b, "first_line_small_caps", False) and runs:
            sc_runs = [Run(
                r.text, r.bold, r.italic, getattr(r, 'image', None),
                scale=r.scale, baseline_shift_em=r.baseline_shift_em,
                small_caps=True, underline=r.underline,
                strike=r.strike, code=r.code,
                letter_spacing_em=r.letter_spacing_em,
                word_spacing_em=r.word_spacing_em, fg=r.fg, bg=getattr(r, 'bg', None),
                nowrap=getattr(r, 'nowrap', False),
                from_text_transform=getattr(r, 'from_text_transform', False),
                link_href=getattr(r, 'link_href', None)
            ) for r in runs]
            sc_items = build_items(sc_runs, self.fam, c, size26, b.display, allow_hyphenation=allow_hyph, lang=getattr(b, "lang", "en"), allow_sc_hyph=True)
            if not sc_items:
                return
            sc_lines = make_lines(sc_items, line_w, c, ragged, is_heading=(b.heading > 0), align=b.align)
            if len(sc_lines) <= 1:
                lines = sc_lines
            else:
                from .layout import Box
                line0_seg, line0_hy = sc_lines[0]
                n_glyphs_l0 = sum(len(it.glyphs) for it in line0_seg if isinstance(it, Box))
                full_txt = "".join(r.text for r in runs)
                pos_t = 0
                g_cnt = 0
                while pos_t < len(full_txt) and g_cnt < n_glyphs_l0:
                    if not full_txt[pos_t].isspace():
                        g_cnt += 1
                    pos_t += 1
                l0_broke_inside_word = (pos_t < len(full_txt) and not full_txt[pos_t].isspace())
                rem_txt = full_txt[pos_t:].lstrip(" ")
                r0 = runs[0]
                rem_runs = [Run(rem_txt, r0.bold, r0.italic, scale=r0.scale, fg=r0.fg, bg=getattr(r0, 'bg', None), link_href=getattr(r0, 'link_href', None))] if rem_txt else []
                rem_items = build_items(rem_runs, self.fam, c, size26, b.display, allow_hyphenation=allow_hyph, lang=getattr(b, "lang", "en"))
                if rem_items:
                    l0_max_w = max((it.word_idx for it in line0_seg if isinstance(it, Box)), default=0)
                    w_off = l0_max_w if l0_broke_inside_word else (l0_max_w + 1)
                    for it in rem_items:
                        if isinstance(it, Box):
                            it.word_idx += w_off
                rem_lines = make_lines(rem_items, lambda idx: line_w(idx + 1), c, ragged, is_heading=(b.heading > 0), align=b.align) if rem_items else []
                lines = [(line0_seg, line0_hy)] + rem_lines
        else:
            items = build_items(runs, self.fam, c, size26, b.display, allow_hyphenation=allow_hyph, lang=getattr(b, "lang", "en"))
            if not items:
                return
            lines = make_lines(items, line_w, c, ragged, is_heading=(b.heading > 0), align=b.align)
        justify = (b.align == "justify") or (b.align is None and c.justify and not ragged)
        placed = []

        for i, (seg, hy) in enumerate(lines):
            last = (i == len(lines) - 1)
            pl, nat, hang_left = layout_line(seg, hy, line_w(i), justify, last, c)
            off26 = -hang_left
            if drop_letter and i < drop_lines:
                off26 += drop_adv26 + drop_gap26
            elif i == 0:
                off26 += indent26

            if b.align == "center":
                off26 += int((line_w(i) - nat) / 2)
            elif b.align == "right":
                off26 += int(line_w(i) - nat)
            placed.append((pl, off26))

        if b.heading:
            h_idx = b.heading - 1
            mt_base_em = (0.66, 0.81, 0.963, 1.32, 1.64, 2.29)[h_idx]
            mb_base_em = (0.66, 0.822, 0.963, 1.32, 1.64, 2.30)[h_idx]
            is_tall_lead = std_body_pitch < 3 * (std_body_pitch - c.size_px())
            mt_lead_k = (0.10 if h_idx == 0 else (0.28 if h_idx == 1 else (0.25 if h_idx == 2 else ((0.05 if is_tall_lead else 0.25) if h_idx == 4 else (0.25 if (h_idx == 5 and is_tall_lead) else 0.0)))))
            mb_lead_k = (0.10 if h_idx in (0, 3) else (0.05 if h_idx == 1 else (0.40 if h_idx == 2 else ((0.12 if is_tall_lead else 0.35) if h_idx == 4 else 0.28))))
            mt = int(round(mt_base_em * b.scale * vem_px + mt_lead_k * extra_lead))
            mb_est = int(round(mb_base_em * b.scale * vem_px + mb_lead_k * extra_lead))
        else:
            eff_vem = (max(float(std_body_pitch), (68.0 / 45.0) * c.size_px()) if extra_lead > 0.0 else float(std_body_pitch)) / 1.2
            mt = (int(b.mt_em * eff_vem * b.scale + 0.25) if (getattr(b, 'list_level', 0) > 0 and extra_lead > 0.0) else (int(round(b.mt_em * vem_px * b.scale)) if (getattr(b, 'list_level', 0) > 0 and getattr(b, 'border_collapse', False) and (getattr(b, 'bullet', None) == '\u2022' or (getattr(b, 'ol_number', None) and b.ol_number[0].isupper()))) else int(b.mt_em * vem_px * b.scale + 1e-6))) if b.mt_em else 0
            mb_est = (int(b.mb_em * vem_px * b.scale + 0.4) if b.mb_em == 1.0 else int(math.ceil(b.mb_em * vem_px * b.scale - 0.5))) if b.mb_em else 0
        gap = max(self.prev_mb, mt)
        prev_h = getattr(self, "prev_heading", 0)
        if b.heading == 1 and prev_h == 0 and not self.page_empty:
            gap += 1
        if extra_lead == 0.0:
            if b.heading == 2 and prev_h == 1:
                gap -= 1
            elif b.heading == 3 and prev_h == 1:
                gap -= 2
            elif b.heading == 2 and prev_h == 2:
                gap = 58
            elif b.heading == 0 and prev_h == 1 and (b.scale > 1.0 or b.mt_em > 1.0):
                gap -= 1
            elif b.heading == 0 and prev_h == 3:
                gap += (2 if getattr(b, "bullet", None) is not None else 1)
            elif b.heading == 0 and prev_h == 6 and not getattr(b, 'border_collapse', False):
                gap += 1
            elif prev_h == 5 and getattr(self, "prev_heading_lines", 0) >= 2:
                gap -= 1

        if b.heading and not self.page_empty and (not getattr(b, "next_is_heading", False) or len(lines) == 1):
            if (self.y + gap + len(lines) * pitch_fl <= c.page_bottom
                    and self.y + gap + len(lines) * pitch_fl + mb_est + std_body_pitch > c.page_bottom):
                self.new_page()
                self.prev_mb = 0
                gap = mt

        if not self.page_empty:
            self.y_float += gap
            self.y = int(round(self.y_float))
        elif c.margin_at_page_top and b.heading:
            top_mt = mt
            extra_top = (c.heading_top_extra_px if b.heading == 1 else (4 if (b.heading == 3 and extra_lead == 0.0 and len(lines) >= 3) else 0))
            self.y_float += top_mt + extra_top
            self.y = int(round(self.y_float))

        n = len(lines)
        i = 0
        while i < n:
            pl_cur, _ = placed[i]
            cur_scale_i = max((pl_tup[0].size26 / float(size26) for pl_tup in pl_cur if pl_tup[0] is not None), default=1.0)
            cur_scale_i = max(1.0, cur_scale_i)
            inl_i = [pl_tup[2][1] for pl_tup in pl_cur if pl_tup[1] == "__inline_img__"]
            if inl_i and max(im.height for im in inl_i) > pitch:
                line_i_pitch = float(pitch + max(0, max(im.height for im in inl_i) - (self.baseline_in(0, pitch, size26) - 6)))
            else:
                line_i_pitch = pitch_fl * cur_scale_i if (cur_scale_i > 1.0 and not b.heading) else pitch_fl
            if not self.page_empty and self.y + line_i_pitch > c.page_bottom:
                self.new_page()
                if i == 0 and c.margin_at_page_top and (b.heading or (getattr(b, 'list_level', 0) > 0 and b.mt_em)):
                    top_mt = mt if b.heading else int(round(b.mt_em * vem_px * b.scale))
                    extra_top = (c.heading_top_extra_px if b.heading == 1 else (4 if (b.heading == 3 and extra_lead == 0.0 and len(lines) >= 3) else 0))
                    self.y_float += top_mt + extra_top
                    self.y = int(round(self.y_float))
                continue
            room = int((c.page_bottom - self.y) // pitch_fl)
            remaining = n - i
            take = min(room, remaining)
            if take < remaining:
                if not b.heading and remaining - take < c.widow_orphan:
                    take = remaining - c.widow_orphan
                if ((not b.heading and take < c.widow_orphan and i == 0 and n >= c.widow_orphan)) or take <= 0:
                    if not self.page_empty:
                        self.new_page()
                        if i == 0 and c.margin_at_page_top and (b.heading or (getattr(b, 'list_level', 0) > 0 and b.mt_em)):
                            top_mt = mt if b.heading else int(round(b.mt_em * vem_px * b.scale))
                            extra_top = (c.heading_top_extra_px if b.heading == 1 else (4 if (b.heading == 3 and extra_lead == 0.0 and len(lines) >= 3) else 0))
                            self.y_float += top_mt + extra_top
                            self.y = int(round(self.y_float))
                        continue
                    take = max(1, min(room, remaining))

            self._ensure_block_meta_on_page(block_idx, b)
            first_line_idx_on_page = self._line_counter

            if drop_letter and i == 0 and take >= 1:
                first_base = self.baseline_in(self.y, pitch, size26)
                drop_baseline = first_base + int(round((min(drop_lines, take) - 1) * pitch_fl))
                self.draw_line(
                    drop_placements,
                    c.x0 * 64 + int(round(left_px * 64)),
                    drop_baseline,
                    block_idx=block_idx,
                    line_idx=first_line_idx_on_page,
                    is_drop_cap=True,
                )

            for k in range(take):
                cur_line_idx = self._line_counter
                self._line_counter += 1
                pl, off26 = placed[i + k]
                cur_scale = max((pl_tup[0].size26 / float(size26) for pl_tup in pl if pl_tup[0] is not None), default=1.0)
                cur_scale = max(1.0, cur_scale)
                std_p = int(round(std_body_pitch * b.scale))
                inline_imgs = [pl_tup[2][1] for pl_tup in pl if pl_tup[1] == '__inline_img__']

                if cur_scale > 1.0 and not b.heading:
                    extra_asc = int((cur_scale - 1.0) * vem_px)
                    cur_pitch = int(cur_scale * std_p + 0.45) if (extra_lead > 0.0 or cur_scale >= 2.0) else (std_p + extra_asc + int((cur_scale - 1.0) * (std_p - vem_px) + 0.49))
                    cur_pitch_fl = float(cur_pitch)
                    base = self.baseline_in(self.y, std_p, size26) + extra_asc + (lh_top_delta if has_custom_lh else 0)
                elif inline_imgs and max(im.height for im in inline_imgs) > pitch:
                    max_im_h = max(im.height for im in inline_imgs)
                    asc_std = self.baseline_in(0, std_p, size26) + 2
                    extra_im = max(0, max_im_h - asc_std)
                    cur_pitch = std_p + extra_im
                    cur_pitch_fl = float(cur_pitch)
                    base = self.baseline_in(self.y, std_p, size26) + extra_im
                else:
                    cur_pitch_fl = pitch_fl
                    cur_pitch = pitch
                    if has_custom_lh:
                        base = self.baseline_in(self.y, std_p, size26) + lh_top_delta
                    else:
                        base = self.baseline_in(self.y, cur_pitch, size26)

                if i + k == 0 and (getattr(b, "ol_number", None) or getattr(b, "bullet", None)):
                    self._draw_list_marker(b, left_px, base, size26, block_idx=block_idx, line_idx=cur_line_idx)

                self.draw_line(
                    pl,
                    c.x0 * 64 + int(round(left_px * 64)) + off26,
                    base,
                    block_idx=block_idx,
                    line_idx=cur_line_idx,
                )

                if c.fractional_pitch_snapping:
                    self.y_float += cur_pitch_fl
                    self.y = int(round(self.y_float))
                else:
                    self.y += cur_pitch
                self._mark_page_non_empty()

            i += take
            if i < n:
                self.new_page()
                if b.heading:
                    self.y_float += 1.0
                    self.y = int(round(self.y_float))

        if has_custom_lh:
            std_p = int(round(std_body_pitch * b.scale))
            self.y_float += (std_p - pitch) + lh_top_delta + lh_bot_delta
            self.y = int(round(self.y_float))

        self.prev_mb = mb_est if b.mb_em else int(round(c.para_gap_em * vem_px))
        self.prev_kind = "text"
        self.prev_heading = b.heading
        self.prev_heading_lines = len(lines) if b.heading else 0

    def add_pre(self, b):
        c = self.cfg
        block_idx = self._block_counter
        self._block_counter += 1
        face = self.fam.special_face('mono', c.size26)
        pitch = self.pitch_for(c.size26)
        mono_adv26 = face.space26()
        max_cols = max(1, int((c.right - c.x0) * 64 // mono_adv26))
        is_col_pre = getattr(b, 'border_collapse', False)
        mt_pre = int(round(1.0 * c.vem_px())) if is_col_pre else int(round(0.5 * c.size_px()))
        if not self.page_empty:
            self.y += max(self.prev_mb, mt_pre)
            self.y_float = float(self.y)
        wrapped_lines = []
        for raw_line in b.pre_lines:
            if not raw_line:
                wrapped_lines.append(("", False))
                continue
            if "\t" in raw_line:
                exp = []
                col_c = 0
                for ch_t in raw_line:
                    if ch_t == "\t":
                        n_sp = 3 - (col_c % 3)
                        exp.append(" " * n_sp)
                        col_c += n_sp
                    else:
                        exp.append(ch_t)
                        col_c += 1
                line = "".join(exp)
            else:
                line = raw_line
            if len(line) > max_cols and " " not in line and "_" in line:
                parts = re.findall(r"[^_]+_?", line)
                tail_lines = []
                idx_end = len(parts)
                while sum(len(p) for p in parts[:idx_end]) > 2 * max_cols:
                    cur_s = ""
                    k = idx_end - 1
                    while k >= 0 and len(parts[k]) + len(cur_s) <= max_cols:
                        cur_s = parts[k] + cur_s
                        k -= 1
                    if k == idx_end - 1:
                        cur_s = parts[k][:max_cols]
                        parts[k] = parts[k][max_cols:]
                    else:
                        idx_end = k + 1
                    tail_lines.insert(0, (cur_s, False))
                rem_parts = parts[:idx_end]
                rem_tot = sum(len(p) for p in rem_parts)
                if rem_tot <= max_cols:
                    wrapped_lines.append(("".join(rem_parts), False))
                else:
                    best_i = 1
                    best_diff = 10**9
                    for i_sp in range(1, len(rem_parts)):
                        l1 = sum(len(p) for p in rem_parts[:i_sp])
                        l2 = rem_tot - l1
                        if l1 <= max_cols and l2 <= max_cols and abs(l1 - l2) < best_diff:
                            best_diff = abs(l1 - l2)
                            best_i = i_sp
                    wrapped_lines.append(("".join(rem_parts[:best_i]), False))
                    wrapped_lines.append(("".join(rem_parts[best_i:]), False))
                wrapped_lines.extend(tail_lines)
                continue
            rem = line
            while len(rem) > max_cols:
                cut = -1
                for idx in range(max_cols, 0, -1):
                    if rem[idx - 1] in (" ", "-") and idx <= max_cols:
                        cut = idx if rem[idx - 1] == "-" else idx - 1
                        break
                if cut <= 0:
                    cut = max_cols
                wrapped_lines.append((rem[:cut].rstrip(), True))
                rem = rem[cut:].lstrip(" ")
                if not rem:
                    break
            if rem:
                wrapped_lines.append((rem, False))
        target_w26 = (c.right - c.x0) * 64
        for line, is_wrapped in wrapped_lines:
            if self.y + pitch > c.page_bottom and not self.page_empty:
                self.new_page()
                if is_col_pre:
                    self.y += 1
                    self.y_float = float(self.y)
            self._ensure_block_meta_on_page(block_idx, b, kind_override="pre")
            cur_line_idx = self._line_counter
            self._line_counter += 1
            pl = []
            pen = 0
            n_spaces = line.count(" ")
            nat_w26 = len(line) * mono_adv26
            delta26 = (target_w26 - nat_w26) if (is_wrapped and n_spaces > 0 and target_w26 > nat_w26) else 0
            sp_idx = 0
            w_idx = 0
            in_space = True
            for c_i, ch in enumerate(line):
                if ch != " ":
                    if in_space and pl:
                        w_idx += 1
                    in_space = False
                    gname = face.cmap.get(ord(ch), '.notdef')
                    pl.append((face, gname, pen, mono_adv26, {
                        "cluster_text": ch,
                        "word_idx": w_idx,
                        "logical_word_idx": w_idx,
                        "logical_char_idx": c_i,
                        "direction": "ltr",
                    }))
                    pen += mono_adv26
                else:
                    in_space = True
                    extra_sp = ((sp_idx + 1) * delta26) // n_spaces - (sp_idx * delta26) // n_spaces if delta26 else 0
                    pen += mono_adv26 + extra_sp
                    sp_idx += 1
            base = self.baseline_in(self.y, pitch, c.size26)
            self.draw_line(pl, c.x0 * 64, base, block_idx=block_idx, line_idx=cur_line_idx)
            self.y += pitch
            self.y_float = float(self.y)
            self._mark_page_non_empty()
        self.prev_mb = (mt_pre - 2 if is_col_pre else mt_pre)
        self.prev_kind = "pre"

    def add_table(self, b):
        c = self.cfg
        if not b.table_rows:
            return
        block_idx = self._block_counter
        self._block_counter += 1
        is_col = getattr(b, "border_collapse", False)
        reg_base = self.fam.face(False, False, c.size26)
        bld_base = self.fam.face(True, False, c.size26)
        std_pitch = self.pitch_for(c.size26)

        if is_col:
            mt_tbl = max(self.prev_mb, int(round(1.0 * c.vem_px())))
        else:
            mt_tbl = int(round(0.67 * (c.vem_px() + 1.0 if c.pitch_px() < 55 else c.size_px()))) if self.prev_kind == "hr" else max(self.prev_mb, int(round(0.4 * c.size_px())))
        if not self.page_empty:
            self.y += mt_tbl

        avail_w = c.right - c.x0 - c.collapsed_table_margin_px

        def _text_w_px(face, s):
            return sum(a for _, a in face.shape(s)) / 64.0

        norm_rows = []
        table_rows_meta = []
        for r_raw in b.table_rows:
            nr = []
            rm = []
            for item in r_raw:
                if len(item) == 2:
                    txt, is_h = item
                    nr.append((txt, is_h, "center" if is_h else "left", 1, 1))
                    rm.append({"text": txt, "is_header": bool(is_h), "align": "center" if is_h else "left", "colspan": 1, "rowspan": 1})
                else:
                    txt, is_h, align, cs, rs = item
                    nr.append(item)
                    rm.append({"text": txt, "is_header": bool(is_h), "align": align, "colspan": int(cs), "rowspan": int(rs)})
            norm_rows.append(nr)
            table_rows_meta.append(rm)

        cap_txt = getattr(b, "table_caption", None)
        if cap_txt:
            self._ensure_block_meta_on_page(block_idx, b, kind_override="table", table_rows_meta=table_rows_meta)
            cap_max_w = int(avail_w * 0.72)
            words_c = cap_txt.split()
            if _text_w_px(reg_base, cap_txt) <= cap_max_w or len(words_c) <= 1:
                cap_lines = [cap_txt]
            else:
                best_k = None
                best_d = 1e9
                for k_c in range(1, len(words_c)):
                    s1 = " ".join(words_c[:k_c])
                    s2 = " ".join(words_c[k_c:])
                    w1, w2 = _text_w_px(reg_base, s1), _text_w_px(reg_base, s2)
                    if w1 <= cap_max_w and w2 <= cap_max_w:
                        cost_c = ((cap_max_w - w1) ** 2) + 0.25 * ((cap_max_w - w2) ** 2)
                        if cost_c < best_d:
                            best_d = cost_c
                            best_k = k_c
                if best_k is not None:
                    cap_lines = [" ".join(words_c[:best_k]), " ".join(words_c[best_k:])]
                else:
                    cap_lines = []
                    cur_c = ""
                    for wc in words_c:
                        cand_c = (cur_c + " " + wc) if cur_c else wc
                        if _text_w_px(reg_base, cand_c) <= avail_w or not cur_c:
                            cur_c = cand_c
                        else:
                            cap_lines.append(cur_c)
                            cur_c = wc
                    if cur_c:
                        cap_lines.append(cur_c)
            for cl_s in cap_lines:
                cur_line_idx = self._line_counter
                self._line_counter += 1
                base_c = self.baseline_in(self.y, std_pitch, c.size26)
                pl_c, pen_c = [], 0
                w_idx = 0
                in_sp = True
                for c_i, (n_g, a_g, ctxt) in enumerate(reg_base.shape_with_clusters(cl_s)):
                    if ctxt == " ":
                        in_sp = True
                    else:
                        if in_sp and any(p[4].get("cluster_text", " ") != " " for p in pl_c):
                            w_idx += 1
                        in_sp = False
                    pl_c.append((reg_base, n_g, pen_c, a_g, {
                        "cluster_text": ctxt,
                        "word_idx": w_idx,
                        "logical_word_idx": w_idx,
                        "logical_char_idx": c_i,
                        "direction": "ltr",
                    }))
                    pen_c += a_g
                x_cap26 = int((c.x0 + (avail_w + 1) / 2.0) * 64 - pen_c / 2.0)
                self.draw_line(pl_c, x_cap26, base_c, block_idx=block_idx, line_idx=cur_line_idx)
                self.y += std_pitch
                self._mark_page_non_empty()
            self.y += 1

        nrows = len(norm_rows)
        occupied = {}
        ncols = 0
        grid_cells = []
        for ri, nr in enumerate(norm_rows):
            ci = 0
            for txt, is_h, align, cs, rs in nr:
                while (ri, ci) in occupied:
                    ci += 1
                for dr in range(rs):
                    for dc in range(cs):
                        occupied[(ri + dr, ci + dc)] = True
                grid_cells.append((ri, ci, txt, is_h, align, cs, rs))
                ci += cs
                if ci > ncols:
                    ncols = ci

        has_spans = any(cs > 1 or rs > 1 for _, _, _, _, _, cs, rs in grid_cells)
        pad_1x = 2.0 * c.collapsed_table_pad_1x
        tot_1x = sum(
            max([_text_w_px(bld_base if is_h else reg_base, txt) + pad_1x
                 for ri, ci, txt, is_h, align, cs, rs in grid_cells if ci == col_j and cs == 1] or [pad_1x])
            for col_j in range(ncols)
        )

        if tot_1x <= avail_w and not has_spans:
            sc_tbl = 1.0
        elif ncols >= 4 and tot_1x > avail_w:
            sc_tbl = c.collapsed_table_scale
        else:
            pref_cols_1x = []
            pad_col_pref = 78.53 if has_spans else 72.10
            for col_j in range(ncols):
                col_w_pref = 0.0
                for ri, ci, txt, is_h, align, cs, rs in grid_cells:
                    if ci == col_j and cs == 1:
                        f1 = bld_base if is_h else reg_base
                        w_full = _text_w_px(f1, txt)
                        w_words = txt.split()
                        if is_h or len(w_words) <= 2 or w_full <= avail_w / float(max(1, ncols)):
                            w_eff = w_full
                        else:
                            w_eff = max(w_full / (2.112 if has_spans else 2.863), max(_text_w_px(f1, w) for w in w_words))
                        if w_eff > col_w_pref:
                            col_w_pref = w_eff
                pref_cols_1x.append(col_w_pref + pad_col_pref)
            w_pref_tot = sum(pref_cols_1x)
            sc_tbl = max(c.collapsed_table_scale, min(1.0, avail_w / max(1.0, w_pref_tot)))

        tbl_size26 = int(round(c.size26 * sc_tbl))
        sc_eff = tbl_size26 / float(c.size26)
        reg = self.fam.face(False, False, tbl_size26)
        bld = self.fam.face(True, False, tbl_size26)

        line_p = int(round(std_pitch * sc_eff)) if sc_tbl < 1.0 else std_pitch
        if sc_tbl <= 0.75:
            row_pad = 7
            top_pad = 0
        elif sc_tbl < 1.0:
            row_pad = 10 if is_col else 15
            top_pad = 0
        else:
            row_pad = 11 if is_col else min(16, int(0.25 * c.size_px() + 5.8))
            top_pad = 3 if is_col else -1

        cell_pad = c.collapsed_table_pad_scaled if sc_tbl <= 0.75 else c.collapsed_table_pad_1x

        col_align = ["left"] * ncols
        for ri, ci, txt, is_h, align, cs, rs in grid_cells:
            if cs == 1 and align == "right":
                col_align[ci] = "right"

        def _col_pad2(ci):
            if sc_tbl <= 0.75:
                if col_align[ci] == "right":
                    return 42.8 if ci == ncols - 1 else 33.3
                return 2.0 * cell_pad
            if not is_col and sc_tbl == 1.0:
                return 70.0
            if not is_col and sc_tbl < 1.0:
                return 55.0
            if has_spans:
                return 75.5
            if col_align[ci] == "right":
                return 36.5 if ci == ncols - 1 else 49.0
            return 64.0 if ci == 0 else 49.0

        max_w = [0.0] * ncols
        min_w = [0.0] * ncols
        for ri, ci, txt, is_h, align, cs, rs in grid_cells:
            if cs == 1:
                face = bld if is_h else reg
                pad2 = _col_pad2(ci)
                t_w = _text_w_px(face, txt)
                w_full = t_w + pad2
                if w_full > max_w[ci]:
                    max_w[ci] = w_full
                raw_toks = txt.split()
                tok_candidates = []
                for rt in raw_toks:
                    if "/" in rt and len(rt) > 4:
                        ps = rt.split("/")
                        for pi, p_s in enumerate(ps):
                            tok_candidates.append(p_s + ("/" if pi < len(ps) - 1 else ""))
                    else:
                        tok_candidates.append(rt)
                if is_h and any("/" in rt and len(rt) > 4 for rt in raw_toks) and len(tok_candidates) >= 2:
                    w_sl = _text_w_px(face, " ".join(tok_candidates[:-1])) + pad2
                    if w_sl > min_w[ci]:
                        min_w[ci] = w_sl
                for tok in tok_candidates:
                    wt = _text_w_px(face, tok) + pad2
                    if wt > min_w[ci]:
                        min_w[ci] = wt

        tot_max = sum(max_w)
        if tot_max <= avail_w and not has_spans:
            if sc_tbl < 1.0:
                extra_each = (avail_w - tot_max) / max(1, ncols)
                col_ws = [int(round(w + extra_each)) for w in max_w]
                col_ws[-1] += avail_w - sum(col_ws)
                table_w = avail_w
            else:
                col_ws = [int(round(w)) for w in max_w]
                table_w = min(avail_w, sum(col_ws))
        else:
            thresh = avail_w / float(max(1, ncols))
            col_ws = [None] * ncols
            for i in range(ncols):
                if max_w[i] <= thresh:
                    col_ws[i] = int(round(max_w[i]))
            rem_idx = [i for i in range(ncols) if col_ws[i] is None]
            rem_w = avail_w - sum(w for w in col_ws if w is not None)
            if len(rem_idx) >= 2:
                sub_thresh = rem_w / float(len(rem_idx))
                narrow_rem = [i for i in rem_idx if max_w[i] <= sub_thresh]
                wide_rem = [i for i in rem_idx if max_w[i] > sub_thresh]
                if narrow_rem and wide_rem:
                    for i in narrow_rem:
                        col_ws[i] = int(round(min_w[i]))
                    rem_idx = wide_rem
                    rem_w = avail_w - sum(w for w in col_ws if w is not None)
                unlocked = list(rem_idx)
                while unlocked:
                    rem_w = avail_w - sum(w for w in col_ws if w is not None)
                    w_tot = max(1.0, sum(max_w[i] for i in unlocked))
                    clamped_any = False
                    for i in list(unlocked):
                        share = rem_w * max_w[i] / w_tot
                        if share < min_w[i]:
                            col_ws[i] = int(round(min_w[i]))
                            unlocked.remove(i)
                            clamped_any = True
                    if not clamped_any:
                        for i in unlocked:
                            col_ws[i] = int(round(rem_w * max_w[i] / w_tot))
                        break
            elif len(rem_idx) == 1:
                col_ws[rem_idx[0]] = rem_w
            else:
                col_ws = [int(round(w)) for w in max_w]
            col_ws[-1] += avail_w - sum(col_ws)
            table_w = avail_w

        col_xs = [c.x0]
        for w in col_ws:
            col_xs.append(col_xs[-1] + w)

        from .hyphen import LiangHyphenator
        dic_p = c.resolve_hyphen_dic("en")
        hyph = LiangHyphenator.get_cached(dic_p, c.left_hyphen_min, c.right_hyphen_min, c.min_word_length) if (c.hyphenate and dic_p) else None

        def _wrap_cell(face, txt, inner_w, is_hdr=False):
            raw_words = txt.split()
            words = []
            for rw in raw_words:
                if "/" in rw and len(rw) > 4:
                    parts_sl = rw.split("/")
                    for pi, ps in enumerate(parts_sl):
                        words.append(ps + ("/" if pi < len(parts_sl) - 1 else ""))
                else:
                    words.append(rw)
            if not words:
                return [("", False)]
            lines_out = []
            cur = ""
            for w in words:
                sep = "" if cur.endswith("/") else (" " if cur else "")
                cand = cur + sep + w
                if _text_w_px(face, cand) <= inner_w:
                    cur = cand
                    continue
                if (not is_hdr) and hyph and c.hyphenate:
                    m_core = w.rstrip(".,;:!?)")
                    tail = w[len(m_core):]
                    parts = hyph.hyphenate_word(m_core) if len(m_core) >= c.min_word_length else [m_core]
                    if len(parts) > 1:
                        best_k = 0
                        for k in range(1, len(parts)):
                            prefix = "".join(parts[:k]) + "-"
                            test = cur + sep + prefix
                            if _text_w_px(face, test) <= inner_w:
                                best_k = k
                        if best_k > 0:
                            prefix = "".join(parts[:best_k]) + "-"
                            lines_out.append((cur + sep + prefix, True))
                            cur = "".join(parts[best_k:]) + tail
                            continue
                if cur:
                    lines_out.append((cur, False))
                if _text_w_px(face, w) > inner_w and len(w) > 1:
                    rem_w = w
                    while len(rem_w) > 1 and _text_w_px(face, rem_w) > inner_w:
                        cut_k = 1
                        for k_c in range(1, len(rem_w)):
                            if _text_w_px(face, rem_w[:k_c] + "-") <= inner_w:
                                cut_k = k_c
                            else:
                                break
                        lines_out.append((rem_w[:cut_k] + "-", True))
                        rem_w = rem_w[cut_k:]
                    cur = rem_w
                else:
                    cur = w
            if cur:
                lines_out.append((cur, False))
            return lines_out

        wrapped_cells = []
        row_max_lines = [1] * nrows
        for ri, ci, txt, is_h, align, cs, rs in grid_cells:
            face = bld if is_h else reg
            span_w = col_xs[ci + cs] - col_xs[ci]
            pad2 = _col_pad2(ci) if cs == 1 else (2.0 * cell_pad)
            inner_w = max(20.0, span_w - pad2 + 1.0)
            lines_c = _wrap_cell(face, txt, inner_w, is_hdr=is_h)
            wrapped_cells.append((ri, ci, lines_c, is_h, align, cs, rs, face))
            if rs == 1 and len(lines_c) > row_max_lines[ri]:
                row_max_lines[ri] = len(lines_c)

        row_hs = [n_l * line_p + row_pad for n_l in row_max_lines]
        tot_tbl_h = sum(row_hs)
        if self.y + tot_tbl_h > c.page_bottom and not self.page_empty:
            self.new_page()
            if not is_col and c.pitch_px() > (19.0 / 14.0) * c.size_px() + 0.5:
                self.y += 8

        self._ensure_block_meta_on_page(block_idx, b, kind_override="table", table_rows_meta=table_rows_meta)

        row_ys = [self.y]
        for rh in row_hs:
            row_ys.append(row_ys[-1] + rh)

        col_l_pad = []
        col_r_pad = []
        for ci in range(ncols):
            if sc_tbl <= 0.75:
                lp = 30.5 if ci == 0 else 16.65
                rp = 31.0 if ci == ncols - 1 else 16.65
            elif not is_col and sc_tbl == 1.0:
                lp = 41.5 if ci == 0 else 33.5
                rp = 44.0 if ci == ncols - 1 else 28.5
            elif not is_col and sc_tbl < 1.0:
                lp = 39.25 if ci == 0 else 28.25
                rp = 48.0 if ci == ncols - 1 else 21.0
            elif has_spans:
                lp = 36.0 if ci == 0 else 39.5
                rp = 39.3 if ci == ncols - 1 else 36.0
            else:
                lp = 36.5 if ci == 0 else 24.5
                rp = 36.5 if ci == ncols - 1 else 24.5
            col_l_pad.append(lp)
            col_r_pad.append(rp)

        last_base = self.y
        for ri, ci, lines_c, is_h, align, cs, rs, face in wrapped_cells:
            y_top = row_ys[ri] + top_pad
            y_bot = row_ys[ri + rs]
            span_h = y_bot - row_ys[ri]
            n_l = len(lines_c)
            block_h = n_l * line_p
            if rs > 1:
                first_base = self.baseline_in(row_ys[ri] + top_pad, line_p, tbl_size26)
                last_sp_base = self.baseline_in(row_ys[ri + rs - 1] + top_pad + (row_max_lines[ri + rs - 1] - 1) * line_p, line_p, tbl_size26)
                if has_spans:
                    last_sp_base += 1
                mid_base = (first_base + last_sp_base) // 2
                y_start = None
            else:
                mid_base = None
                y_start = y_top + max(0, (span_h - row_pad - block_h) // 2)
            x_left = col_xs[ci]
            x_right = col_xs[ci + cs]
            for li, (ltxt, ends_with_synth_hy) in enumerate(lines_c):
                cur_line_idx = self._line_counter
                self._line_counter += 1
                if mid_base is not None:
                    base = mid_base + li * line_p
                else:
                    in_cell_step = (line_p - 1) if (sc_tbl <= 0.75 and n_l > 1) else line_p
                    base = self.baseline_in(y_start + li * in_cell_step, line_p, tbl_size26)
                    if sc_tbl <= 0.75 and n_l == 1 and row_max_lines[ri] > 1 and ri == 0:
                        base -= 1
                    elif sc_tbl <= 0.75 and ri == nrows - 1:
                        base += 1
                    elif has_spans and ri == nrows - 1 and n_l > 1:
                        base += 1
                if base > last_base:
                    last_base = base
                pl, pen = [], 0
                sh_c = face.shape_with_clusters(ltxt)
                w_idx = 0
                in_sp = True
                for g_i, (n, a, ctxt) in enumerate(sh_c):
                    if ctxt == " ":
                        in_sp = True
                    else:
                        if in_sp and any(p[4].get("cluster_text", " ") != " " for p in pl):
                            w_idx += 1
                        in_sp = False
                    is_synth = (ends_with_synth_hy and g_i == len(sh_c) - 1 and ctxt == "-")
                    pl.append((face, n, pen, a, {
                        "cluster_text": ctxt,
                        "word_idx": w_idx,
                        "logical_word_idx": w_idx,
                        "logical_char_idx": g_i,
                        "is_synthetic_hyphen": is_synth,
                        "is_ligature": (len(ctxt) > 1),
                        "direction": "ltr",
                    }))
                    pen += a
                if align == "center":
                    if cs > 1:
                        center_x = (col_xs[ci] + col_l_pad[ci] + col_xs[ci + cs]) / 2.0
                        x_px = center_x - (pen / 64.0) / 2.0
                    else:
                        c_left = x_left + col_l_pad[ci]
                        c_right = x_right - col_r_pad[ci]
                        hdr_off = 5.0 if (ci == 0 or not is_col) and not (not is_col and sc_tbl == 1.0 and ci > 0) else 0.0
                        if not is_col and sc_tbl == 1.0 and ci > 0:
                            hdr_off = 0.85
                        elif has_spans and ci == ncols - 1:
                            hdr_off = 2.0
                        center_x = (c_left + c_right) / 2.0 + hdr_off
                        x_px = center_x - (pen / 64.0) / 2.0
                elif align == "right":
                    x_px = x_right - col_r_pad[ci + cs - 1] - (pen / 64.0)
                else:
                    x_px = x_left + col_l_pad[ci]
                self.draw_line(pl, int(round(x_px * 64)), base, block_idx=block_idx, line_idx=cur_line_idx)

        if sc_tbl <= 0.75:
            rule_y_float = last_base + 17.745
        elif has_spans:
            rule_y_float = last_base + 22.753
        elif not is_col and sc_tbl < 1.0:
            rule_y_float = last_base + 29.102
        elif not is_col:
            rule_y_float = last_base + 28.706 + 0.455 * (std_pitch - 57)
        else:
            rule_y_float = last_base + 23.957

        self.y = int(math.floor(rule_y_float))
        if self.y + 70 < c.page_bottom:
            frac = rule_y_float - self.y
            g_top = int(round(255.0 * frac))
            g_bot = 255 - g_top
            rx0 = c.x0
            rx1 = min(c.right, c.x0 + table_w + 1)
            if 0 < g_top < 255:
                self.cur_ir_page.commands.append(RuleCommand(
                    x0=rx0, y0=self.y, x1=rx1, y1=self.y + 1, color=(g_top, g_top, g_top), role="table_rule"
                ))
                self.cur_ir_page.commands.append(RuleCommand(
                    x0=rx0, y0=self.y + 1, x1=rx1, y1=self.y + 3, color=(0, 0, 0), role="table_rule"
                ))
                self.cur_ir_page.commands.append(RuleCommand(
                    x0=rx0, y0=self.y + 3, x1=rx1, y1=self.y + 4, color=(g_bot, g_bot, g_bot), role="table_rule"
                ))
            else:
                self.cur_ir_page.commands.append(RuleCommand(
                    x0=rx0, y0=self.y, x1=rx1, y1=self.y + 4, color=(0, 0, 0), role="table_rule"
                ))
            icon_rgb = _render_table_icon_rgb(frac)
            ih, iw = icon_rgb.shape[:2]
            by0 = self.y + (14 if int(round(frac * 4.0)) == 4 else 13)
            bx0 = c.x0 + 17
            self.cur_ir_page.commands.append(ImageCommand(
                x=bx0, y=by0, width=iw, height=ih, pixels=icon_rgb, role="table_icon"
            ))
            self.y = (by0 + ih + (7 if sc_tbl <= 0.75 else 1)) if is_col else (by0 + ih + (6 if sc_tbl < 1.0 else 4))
        self.y_float = float(self.y)
        self.prev_mb = int(round(1.0 * c.vem_px())) if is_col else int(round(0.2 * c.size_px()))
        self.prev_kind = "table"
        self._mark_page_non_empty()

    def add_image(self, b):
        c = self.cfg
        block_idx = self._block_counter
        self._block_counter += 1
        im = b.image
        if getattr(b, 'is_cover', False):
            if not self.page_empty:
                self.new_page()
            self._ensure_block_meta_on_page(block_idx, b, kind_override="image")
            self.cur_ir_page.commands.append(RectCommand(
                x0=0, y0=0, x1=c.screen_w, y1=c.screen_h, color=(0, 0, 0), role="cover_bg"
            ))
            s = min(c.screen_w / im.width, c.screen_h / im.height)
            w = max(1, int(round(im.width * s)))
            h = max(1, int(round(im.height * s)))
            im_arr = _skia_bilerp_rgb(im, w, h)
            x = (c.screen_w - w) // 2
            y = (c.screen_h - h) // 2
            self.cur_ir_page.commands.append(ImageCommand(
                x=x, y=y, width=w, height=h, pixels=im_arr, role="cover"
            ))
            self._mark_page_non_empty()
            self.new_page()
            self.prev_mb = 0
            return

        sc = getattr(c, "img_px_scale", 1.80)
        nat_w = im.width * sc
        nat_h = im.height * sc
        vem_px = c.vem_px()
        lx = c.x0 + int(round(getattr(b, "left_em", 0.0) * c.size_px()))
        rx = c.right - int(round(getattr(b, "right_em", 0.0) * c.size_px()))
        maxw = max(1, rx - lx)
        maxh = 2036
        w_pct = getattr(b, "img_width_pct", None)
        if w_pct is not None and w_pct > 0:
            target_w = max(1, int(round(maxw * w_pct)))
            target_h = max(1, int(round(im.height * (target_w / float(im.width)))))
            if target_h > maxh:
                target_w = max(1, int(round(target_w * (maxh / float(target_h)))))
                target_h = maxh
        else:
            s = min(1.0, maxw / nat_w, maxh / nat_h)
            target_w = max(1, int(round(nat_w * s)))
            target_h = max(1, int(round(nat_h * s)))
        im = im.resize((target_w, target_h), Image.BILINEAR)

        mt_px = int(round(max(self.prev_mb, getattr(b, "mt_em", 0.0) * vem_px))) if not self.page_empty else 0
        if (self.y + mt_px + im.height > c.page_bottom or b.page_break_before) and not self.page_empty:
            self.new_page()
            self.prev_mb = 0
            mt_px = 0
        self._ensure_block_meta_on_page(block_idx, b, kind_override="image")
        self.y += mt_px
        x = lx + (maxw - im.width) // 2
        y = 167 if (self.page_empty and im.height >= 2000) else (
            c.top + (maxh - im.height) // 2 if (b.page_break_before and self.page_empty) else self.y
        )
        y_draw = (y - 1) if ((getattr(b, 'border_collapse', False) or not self.page_empty) and not b.page_break_before and im.height < 2000 and c.pitch_px() <= (19.0 / 14.0) * c.size_px() + 0.5) else y
        arr_u8 = np.array(im, dtype=np.uint8)
        self.cur_ir_page.commands.append(ImageCommand(
            x=x, y=y_draw, width=im.width, height=im.height, pixels=arr_u8, role="block"
        ))
        self.y = y + im.height
        self.y_float = float(self.y)
        self._mark_page_non_empty()
        self.prev_mb = 0
        self.prev_kind = "image"
        if b.page_break_before:
            self.new_page()
            self.prev_mb = 0

    def add_hr(self, b=None):
        c = self.cfg
        is_col = getattr(b, "border_collapse", False) if b is not None else False
        has_extra_lead = c.pitch_px() > (19.0 / 14.0) * c.size_px() + 0.5
        gap = int(round(0.52 * c.vem_px())) if (is_col and self.prev_mb == 0) else (int(c.vem_px() - 1.5) if has_extra_lead else int(round(c.vem_px())))
        top_gap = (c.pre_hr_top_gap_px if (self.prev_kind == 'pre' and is_col) else (gap if has_extra_lead else max(self.prev_mb, gap)))
        if not self.page_empty and self.y + top_gap + 3 > c.page_bottom:
            self.new_page()
            self.y += int(c.vem_px() - 1.5)
        else:
            self.y += top_gap
        if self.y + 3 <= c.page_bottom:
            self.cur_ir_page.commands.append(RuleCommand(
                x0=c.x0, y0=self.y, x1=c.right, y1=self.y + 3, color=(136, 136, 136), role="hr"
            ))
        self.y += 3
        self.y_float = float(self.y)
        self._mark_page_non_empty()
        self.prev_mb = int(round(0.50 * c.vem_px())) if is_col else int(c.vem_px() + 0.5)
        self.prev_kind = "hr"

    def add_error_placeholder_page(self, chapter_id: str, exc: Exception, tb_str: str):
        c = self.cfg
        if not self.page_empty:
            self.new_page()
        self.current_chapter = chapter_id or "unknown"
        self._mark_page_non_empty()
        bx0, by0, bx1, by1 = c.x0, c.top, c.right, min(c.page_bottom, c.top + 400)
        self.cur_ir_page.commands.append(RectCommand(x0=bx0, y0=by0, x1=bx1, y1=by0 + 4, color=(0, 0, 0), role="error_box"))
        self.cur_ir_page.commands.append(RectCommand(x0=bx0, y0=by1 - 4, x1=bx1, y1=by1, color=(0, 0, 0), role="error_box"))
        self.cur_ir_page.commands.append(RectCommand(x0=bx0, y0=by0, x1=bx0 + 4, y1=by1, color=(0, 0, 0), role="error_box"))
        self.cur_ir_page.commands.append(RectCommand(x0=bx1 - 4, y0=by0, x1=bx1, y1=by1, color=(0, 0, 0), role="error_box"))
        face = self.fam.special_face("mono", c.size26)
        pitch = self.pitch_for(c.size26)
        adv = face.space26()
        msg_lines = [
            f"ERROR IN CHAPTER: {self.current_chapter}",
            f"{type(exc).__name__}: {str(exc)[:48]}",
        ]
        y_cur = by0 + pitch
        for mline in msg_lines:
            pl, pen = [], 0
            for c_i, ch in enumerate(mline):
                if ch != " ":
                    gname = face.cmap.get(ord(ch), ".notdef")
                    pl.append((face, gname, pen, adv, {"cluster_text": ch, "word_idx": 0, "logical_word_idx": 0, "logical_char_idx": c_i}))
                pen += adv
            base = self.baseline_in(y_cur, pitch, c.size26)
            self.draw_line(pl, (bx0 + 24) * 64, base)
            y_cur += pitch
        self.y = by1 + pitch
        self.y_float = float(self.y)
        self.chapter_errors.append({
            "chapter": self.current_chapter,
            "exception": repr(exc),
            "traceback": tb_str,
        })
        self.new_page()

    def finish_ir(self) -> PositionedDocument:
        if not (self.page_empty and self.ir_pages):
            self._finalize_current_page()
        from . import __version__
        return PositionedDocument(
            pages=list(self.ir_pages),
            chapter_errors=list(self.chapter_errors),
            screen_w=self.cfg.screen_w,
            screen_h=self.cfg.screen_h,
            bg=tuple(self.cfg.bg),
            fg=tuple(self.cfg.fg),
            engine_version=__version__,
        )


def layout_blocks_to_ir(blocks, cfg, family, max_pages: Optional[int] = None) -> PositionedDocument:
    import traceback as _tb
    pg = Pager(cfg, family)
    ch_groups = []
    for b in blocks:
        ch_id = getattr(b, "chapter", "") or ""
        if not ch_groups or ch_groups[-1][0] != ch_id:
            ch_groups.append((ch_id, [b]))
        else:
            ch_groups[-1][1].append(b)

    for ch_id, ch_blocks in ch_groups:
        if max_pages and len(pg.ir_pages) >= max_pages:
            break
        if ch_id:
            pg.current_chapter = ch_id
        try:
            for b in ch_blocks:
                if max_pages and len(pg.ir_pages) >= max_pages:
                    break
                if b.kind == "text":
                    pg.add_text_block(b)
                elif b.kind == "pre":
                    pg.add_pre(b)
                elif b.kind == "table":
                    pg.add_table(b)
                elif b.kind == "image":
                    pg.add_image(b)
                elif b.kind == "hr":
                    pg.add_hr(b)
        except Exception as exc:
            pg.add_error_placeholder_page(ch_id or pg.current_chapter, exc, _tb.format_exc())

    ir_doc = pg.finish_ir()
    if max_pages:
        ir_doc.pages = ir_doc.pages[:max_pages]
    return ir_doc


def layout_lines_to_ir(lines, cfg, family, bold=False, italic=False) -> PositionedPage:
    pg = Pager(cfg, family)
    face = family.face(bold, italic, cfg.size26)
    pitch = pg.pitch_for(cfg.size26)
    for l_i, s in enumerate(lines):
        if pg.y + pitch > cfg.page_bottom:
            break
        pl, nat = [], 0
        for c_i, (n, a, ctxt) in enumerate(face.shape_with_clusters(s)):
            pl.append((face, n, nat, a, {"cluster_text": ctxt, "word_idx": 0, "logical_word_idx": 0, "logical_char_idx": c_i}))
            nat += a
        base = pg.baseline_in(pg.y, pitch, cfg.size26)
        pg.draw_line(pl, cfg.x0 * 64, base, block_idx=0, line_idx=l_i)
        if cfg.fractional_pitch_snapping:
            pg.y_float += float(cfg.pitch_px())
            pg.y = int(round(pg.y_float))
        else:
            pg.y += pitch
        pg._mark_page_non_empty()
    return pg.finish_ir().pages[0]


def render_blocks(blocks, cfg, family, max_pages=None, return_meta=False):
    from .raster import Rasterizer
    ir_doc = layout_blocks_to_ir(blocks, cfg, family, max_pages=max_pages)
    rast = Rasterizer(cfg)
    try:
        out_imgs = rast.rasterize_document(ir_doc)
    finally:
        rast.close()
    if return_meta:
        meta = {
            "page_chapters": [p.chapter for p in ir_doc.pages],
            "chapter_errors": ir_doc.chapter_errors,
            "layout_hashes": [p.layout_sha256() for p in ir_doc.pages],
            "ir_pages": ir_doc.pages,
            "ir_doc": ir_doc,
        }
        return out_imgs, meta
    return out_imgs


def render_lines(lines, cfg, family, bold=False, italic=False):
    from .raster import Rasterizer
    ir_page = layout_lines_to_ir(lines, cfg, family, bold=bold, italic=italic)
    rast = Rasterizer(cfg)
    try:
        return rast.rasterize_page(ir_page)
    finally:
        rast.close()
