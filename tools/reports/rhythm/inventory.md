# Inventory of Geometry-Keyed Branches, Tables, and Constants (`layout.py`, `page.py`, `config.py`, `epub.py`)

## Grep Pattern List Used
```bash
grep -nE "size26|size_px|pitch|std_body_pitch|x0|right|measure|page_bottom|2688|2880|2176|19\.0|1\.357|0\.6632|0\.814|0\.8281|28\.8125|0\.6849|2\.0" \
  kindle_render/config.py kindle_render/epub.py kindle_render/layout.py kindle_render/page.py
```

## Complete Inventory Table

| File & Line | Expression / Constant / Branch | Corpus Pages Derived From | Provenance | Stage C/D/E Action |
|---|---|---|---|---|
| `kindle_render/config.py:44` | `pitch_ratio: float = 57 / 42` (`19/14 = 1.3571428`) | `probe` p.3, `exam2` p.3 | `measured` | Default compact line-spacing ratio (`19/14`); explicit `--pitch` overrides per profile. |
| `kindle_render/config.py:114` | `heading_top_extra_px: int = 1` | `probe` p.43, 80; `exam1` p.5; `exam2` p.3, 22 | `measured` | Keep as universal `+1 px` `h1` page-top offset across all geometries (remove `std_body_pitch == 57` guard). |
| `kindle_render/config.py:121` | `base_root_em_sp: float = 10.97619` (`28.8125 px` at `2.625x`) | `exam1` p.25-26 (`2em=58px`), `exam2` p.40-41 (`2em=58px`), `exam3_normal` p.48 (`1em=29px`), `exam3_small` p.31 (`1em=29px`) | `measured` | Checked across all 3 geometries (`42px`, `45px`, `34px`); apply to all `em`/`rem` horizontal margins on `<p>` (remove `abs(v) >= 1.99` threshold in `epub.py:165`). |
| `kindle_render/config.py:122` | `blockquote_margin_ratio: float = 0.04725` | `probe` p.52, `exam1` p.44 | `measured` | Checked at 2 geometries (`x0=39..1041` -> `47.3 px`, `x0=79..1001` -> `43.6 px`). |
| `kindle_render/config.py:123-128` | `collapsed_table_*` (`margin_px=36`, `scale=0.70`, `line_pitch=55`, `rule_h=4`, `pad_1x=34`, `pad_scaled=24`) | `exam2` p.8, 13, 35; `exam3_normal` p.38-40 | `measured` | Named device constants in `config.py` with page/crop comments. |
| `kindle_render/config.py:129` | `pre_hr_top_gap_px: int = 50` | `exam2` p.36 | `measured` | Named device constant in `config.py`. |
| `kindle_render/config.py:132-134` | `ul_indent_em: float = 2.0000`, `ol_indent_em: float = 2.0952` (`88 px / 42 px`) | `probe` p.87, `exam1` p.45, `exam2` p.37 | `measured` | Checked across geometries (`88 px` fixed indent / `size_px`). |
| `kindle_render/config.py:152` | `vem_px() -> self.pitch_px() / 1.2` | `probe` p.80-81, `exam1` p.5-14, `exam2` p.22-28 | `measured` | Evaluate continuous `P / 1.2` vs `floor(P / 1.2)` in Stage B & Stage C. |
| `kindle_render/epub.py:165` | `if use_root_em and abs(v) >= 1.99: return v * cfg.base_root_em_px() / sz` | `exam1` p.25-26, `exam2` p.40-41 | `fitted` | Replace in Stage C: compare `em` vs `rem` and remove arbitrary `abs(v) >= 1.99` gate so `1em` (`exam3_normal` p.48, `exam3_small` p.31) resolves consistently. |
| `kindle_render/epub.py:365-368` | `sub`/`sup` `baseline_shift_em` (`-0.21 * pitch_px` and `13.0 px`) | `probe` p.78, `exam1` p.42, `exam2` p.40, `exam3_normal` p.42 | `measured` | Checked across all 3 geometries. |
| `kindle_render/epub.py:577-580` | `132.0 / cfg.size_px()` (`ol` nested in `ul` left indent = `132 px`) | `exam1` p.45, `exam2` p.37, `exam3_normal` p.36 | `measured` | Checked across `42px` and `45px` geometries (`88 + 44 = 132 px`). |
| `kindle_render/layout.py:902-906` | `s0 = (slack / G) * 2.0` vs `(slack / ref_size26) * 0.61` | `probe` p.43-61, `exam1` p.15-32 | `fitted` | Knuth-Plass badness scaling in terms of `ref_size26` and glue `G`. |
| `kindle_render/page.py:349-350` | `extra_sp_lead = max(0.0, std_body_pitch - (19.0 / 14.0) * c.size_px())`; `self.y_float += (std_body_pitch - 4.04124 * extra_sp_lead)` | `exam1` p.15 | `fitted` | Back-solved 5-digit constant `4.04124` from single geometry (`45px, 68`); replace in Stage C with clean formula. |
| `kindle_render/page.py:363` | `lh_top_delta = (lead_diff // 2) if (lead_diff >= 0 or std_body_pitch != 57) else -((-lead_diff) // 2)` | `probe` p.82, `exam1` p.42 | `fitted` | Remove `std_body_pitch != 57` branch in Stage C. |
| `kindle_render/page.py:367` | `pitch_fl = float(int(std_body_pitch * b.scale)) if (b.heading in (2, 3) and std_body_pitch == 57) else ...` | `probe` p.80, `exam1` p.5-14, `exam2` p.22-28 | `fitted` | Geometry-keyed `std_body_pitch == 57` branch; replace in Stage C with unified heading line-step formula across `(34,51)`, `(42,57)`, `(45,68)`. |
| `kindle_render/page.py:507-514` | `extra_lead = max(0.0, std_body_pitch - (19.0 / 14.0) * c.size_px())`, `mt_base_em = (0.6632, 0.8140, 0.9717, 1.3263, 1.6487, 2.2938)`, `mb_base_em = (0.6632, 0.8281, ...)` | `probe` p.80-81, `exam1` p.5-14, `exam2` p.22-28 | `fitted` | 4-digit back-solved constants (`0.6632`, `0.8140`, `0.8281`, etc.); replace in Stage C with CSS-standard `m_top = m_bot = (0.67, 0.83, 1.00, 1.33, 1.67, 2.33)` + verified cross-geometry formula. |
| `kindle_render/page.py:517` | `mb_est = (int(b.mb_em * vem_px * b.scale + 1e-6) if (std_body_pitch == 57 and b.mb_em == 1.0) else ...)` | `probe` p.82, `exam2` p.35 | `fitted` | Remove `std_body_pitch == 57` branch in Stage C. |
| `kindle_render/page.py:519-536` | `if std_body_pitch == 57:` pairwise `prev_h` / `b.heading` `+1/-1/-2` adjustments | `probe` p.80-81, `exam2` p.22-28 | `fitted` | Geometry-keyed `std_body_pitch == 57` block; eliminate in Stage C. |
| `kindle_render/page.py:550,569,583` | `extra_top = (c.heading_top_extra_px if (b.heading == 1 and std_body_pitch == 57) else (4 if (b.heading == 3 and std_body_pitch == 57 and len(lines) >= 3) else 0))` | `probe` p.80, `exam2` p.22, `exam3_small` p.43 | `fitted` | Remove `std_body_pitch == 57` condition in Stage C (`h1` page-top `+1 px` applies across all geometries, fixing `exam3_small` p.3/23/43/46/49/52 `245` vs `244`). |
| `kindle_render/page.py:615` | `cur_pitch = int(round(cur_scale * std_p)) if (std_body_pitch != 57 or cur_scale >= 2.0) else ...` | `exam2` p.40 (`big` span), `exam3_normal` p.42 | `fitted` | Remove `std_body_pitch != 57` branch in Stage C. |
| `kindle_render/page.py:1345` | `y_draw = (y - 1) if (... and c.pitch_px() == 57) else y` | `exam2` p.39 | `fitted` | Remove `c.pitch_px() == 57` geometry-keyed branch in Stage C. |
