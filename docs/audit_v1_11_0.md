# Audit of `v1.10.2` / `v1.11.0` Hard-Coded Constants and Golden Changes (`Task B`)

## 1. Executive Summary
Per Section 3 of the Task Pack (`Task B`), this document audits:
- **B1**: Every geometry-keyed condition (`size26 != 2688`, `size_px() == 42.0`, `size_px() < 40`, `size_px() > 46`, `maxw != 922`) and empirical constant (`886.0`, `0.28 * size_px`, `7/1/2 px` post-table-icon offsets, `Config.pitch_ratio = 1.5`, `floor(x + 0.5)`) introduced in `v1.10.2` / `v1.11.0`. All unproven constants have been registered as `UNPROVEN` hypotheses with concrete falsification tests in `docs/hypotheses/unproven_v1_11_0.md`.
- **B2**: Every golden hash change in `v1.10.2` / `v1.11.0` (`probe` p88, p89; `exam1` p47; `synthetic` p1–3; plus verification that `probe` p1, `exam3_normal` p1, and `exam3_small` p1 pixel hashes did NOT change), supported by side-by-side crops in `docs/crops/audit_v1_11_0/`.
- **B3**: Removal of `tools/score_dir.py` (which duplicated `tools/score_all.py` with an incompatible CLI).

---

## 2. Part B1 — Table of New Constants & Geometry Guards in `v1.10.2` / `v1.11.0`

Full hypothesis entries and falsification tests are recorded in [`docs/hypotheses/unproven_v1_11_0.md`](hypotheses/unproven_v1_11_0.md).

| ID | `file:line` | Value / Condition | Fitted On | First-Principles Derivation? | Exercised by Std / Compact / Large? |
|---|---|---|---|---|---|
| `H-B1-01` | `kindle_render/layout.py:294` | `sc = (size26 / 1024.0) if size26 != 2688 else cfg.dpi_scale` | `tables_images` `i4_inline` (`ti_std` p36, `ti_compact` p29, `ti_large` p45) vs `exam2` p40 | Partial (`size_px / 16.0` = CSS `1em` to `16px` ratio; `size26 != 2688` is an unproven guard for `exam2` p40) | **Yes** (all 3 themes in `tables_images`) |
| `H-B1-02` | `kindle_render/page.py:987` | `(is_col and ncols <= 3 and has_spans and c.size_px() != 42.0)` -> `sc_tbl = 1.0` | `tables_images` `t3_spans` vs `exam2` p36 (`42 px`) | **No** (`size_px() != 42.0` is a geometry guard) | **Yes** (all 3 themes in `tables_images`) |
| `H-B1-03` | `kindle_render/page.py:990` | `sc_tbl = 0.81 if c.size_px() > 46.0 else 0.96` (3-col wide collapsed table) | `ti_std` p6 (`0.96`), `ti_compact` p5 (`0.96`), `ti_large` p7 (`0.81`) | **No** (fitted scale factors + `size_px() > 46.0` threshold) | **Yes** (all 3 themes in `tables_images`) |
| `H-B1-04` | `kindle_render/page.py:992` | `min(1.0, avail_w / 886.0) if c.size_px() > 46.0 else 1.0` (4+ col collapsed table) | `ti_large` p2–6 (`avail_w = 818`) | **No** (`886.0` and `> 46.0` fitted on `ti_large`) | **Yes** (`Large` in `tables_images`) |
| `H-B1-05` | `kindle_render/page.py:1018` | `int(round((tbl_size26 / 64.0) * 1.36))` when `is_col and sc_tbl <= 0.75 and c.size_px() != 42.0` | `tables_images` `t1_columns` vs `exam2` p36 | Partial (`1.36 ≈ 19/14` tight line-height ratio inside scaled tables; `!= 42.0` is a guard) | **Yes** (all 3 themes in `tables_images`) |
| `H-B1-06` | `kindle_render/page.py:1026` | `row_pad = int(0.28 * c.size_px()) if is_col` | `ti_compact` (`10`), `exam2` (`11`), `ti_std` (`12`), `ti_large` (`14`) | Partial (`0.28em` vertical cell padding across 4 font sizes) | **Yes** (all 3 themes) |
| `H-B1-07` | `kindle_render/page.py:1212` | `int(round(n_l * (std_pitch * sc_eff) + row_pad))` when `0.90 <= sc_tbl < 1.0 and c.size_px() != 42.0` | `ti_std` p6, `ti_compact` p5 vs `exam2` p35 | **No** (`size_px() != 42.0` guard) | **Yes** (`Standard`, `Compact` in `t2_text`) |
| `H-B1-08` | `kindle_render/page.py:1385` | `if is_col and c.size_px() != 42.0: rule_y_float = float(row_ys[-1])` | `tables_images` vs `exam2` p35–36 | **No** (`size_px() != 42.0` guard) | **Yes** (all 3 themes in `tables_images`) |
| `H-B1-09` | `kindle_render/page.py:1399` | `-4 if c.size_px() < 40 else 0` (borderless table bottom offset) | `ti_compact` p2 (`t1_columns` 2-col table) | **No** (fitted on `ti_compact` p2) | **Yes** (`Compact` in `tables_images`) |
| `H-B1-10` | `kindle_render/page.py:1429` | `7 if sc_tbl <= 0.75 else (7 if c.extra_lead_px() > 0.0 else (1 if c.size_px() == 42.0 else 2))` | `ti_std`/`ti_large` (`7`), `exam2` (`1`), `ti_compact` (`2`) | **No** (`7 / 1 / 2 px` post-icon offsets + `size_px() == 42.0` branch) | **Yes** (all 3 themes) |
| `H-B1-11` | `kindle_render/page.py:1431` | `prev_mb = (int(round(1.0 * c.vem_px())) if c.size_px() == 42.0 else 0) if is_col` | `exam2` (`42 px`) vs `tables_images` | **No** (`size_px() == 42.0` guard) | **Yes** (all 3 themes) |
| `H-B1-12` | `kindle_render/page.py:1466` | `sc = (maxw / 512.0) if (maxw != 922 or getattr(b, "img_css_w", None) is not None) else 1.80` | `tables_images` `i2_dims`/`i3_shapes` vs `exam1`/`exam2` (`maxw == 922`) | Partial (512px reference width in `tables_images`; `maxw != 922` is a guard) | **Yes** (`Compact`, `Large`, and `Standard` with `img_css_w`) |
| `H-B1-13` | `kindle_render/page.py:1494` | `target_h > rem_h and rem_h >= 1000 and target_h < 1500` (shrink image to `rem_h`) | `tables_images` `i5_flow` (`ti_std` p39, `ti_compact` p31, `ti_large` p49) | Partial (KRF shrinks tall flow images to fit remaining page height; bounds `1000` and `1500` are empirical) | **Yes** (all 3 themes in `i5_flow`) |
| `H-B1-14` | `kindle_render/config.py:45,149` | `pitch_ratio = 1.5`, `floor(x + 0.5)` | `e3_small` (`34 * 1.5 = 51`), Standard steps | **Yes** (Standard step-2 line spacing is `1.5x` and `floor(x+0.5)` matches C/Kotlin round-half-up) | Only when `pitch == 0` (`synthetic`) |

---

## 3. Part B2 — Audit & Justification of Golden Changes in `v1.10.2` / `v1.11.0`

Comparing `git diff 3938782..374787e -- tools/golden/` (`v1.10.1` vs `v1.11.0`):

| Corpus & Page | Golden Hash Changed in `v1.10.2`/`v1.11.0`? | Changed Pixels (`v1.10.1` vs `v1.11.0`) | Bounding Box of Change | Device Capture `diff_pixels` (`before -> after`, `y=83..2240`) | Root Cause & Justification | Crop (`old \| new \| device`) |
|---|---:|---:|---|---:|---|---|
| `probe` p1 (`cover`) | **No** (`a4672ab714f1...` unchanged since `1.8.0`) | `0 px` | None | `7,178 -> 7,178` (`0`) | `_skia_bilerp_rgb` generalized `(W_in == 1000 and W_out == 1080)` to `(W_out * 25 == W_in * 27)` and `60680/65536` to `((W_in*65536)//W_out - 1)/65536`, which evaluates to the **exact same float** (`60680/65536`) for `1000x1500 -> 1080x1620`. Only the JSON `engine_version` header field in `probe.json` changed (`"1.9.1" -> "1.10.2"`). | `docs/crops/audit_v1_11_0/crop_probe_p1.png` |
| `probe` p88 (`e3_blocks`) | **Yes** (`feeb161c... -> a689e800...`) | `61,527 px` | `x=[39..1040], y=[1056..1661]` | **`105,804 -> 82,079` (`-23,725 px`)** | `probe` uses `x0=39, right=1041` (`maxw = 1002 != 922`) and `size26 = 2688` (`42 px`). In `e3_blocks` p88, `<dd>` (`is_dd = True`) and `mt_tbl` before the collapsed table (`page.py:865`) shifted the table and following inline/block elements closer to the device capture by `-23,725` diff pixels. | `docs/crops/audit_v1_11_0/crop_probe_p88.png` |
| `probe` p89 (`e3_blocks`) | **Yes** (`a2cac5ee... -> 124ffd99...`) | `8,096 px` | `x=[307..777], y=[167..2202]` | **`99,927 -> 98,083` (`-1,844 px`)** | On `probe` p89 (`maxw = 1002 != 922`), `add_image` scaled the block image using `sc = maxw / 512.0` (`1.9570` vs `1.80`), improving alignment against the device capture by `-1,844` diff pixels. | `docs/crops/audit_v1_11_0/crop_probe_p89.png` |
| `exam1` p47 (`e11_blocks`) | **Yes** (`dbffa8bd... -> e7a1412c...`) | `25,162 px` | `x=[78..1001], y=[1402..1572]` | **`126,930 -> 126,877` (`-53 px`)** | In `epub.py:594` and `page.py:865`, `is_dd` restricted the `1.0 * vem_px` collapsed-table top margin fallback to tables immediately following `<dd>` (as in `exam2` p35), shifting the collapsed table on `exam1` p47 (`y=[1402..1572]`) for a net `-53 px` reduction in diff vs capture. | `docs/crops/audit_v1_11_0/crop_exam1_p47.png` |
| `exam3_normal` p1 (`cover`) | **No** (`41453d0d3da0...` unchanged since `1.8.0-rc1`) | `0 px` | None | `8,739 -> 8,739` (`0`) | Neither `exam3_normal.json` nor `exam3_small.json` changed in `v1.10.2` / `v1.11.0` (`0` lines diff in git). Their p1 cover image (`1000x1500 -> 956x1434` inside `x0=79..1001` or `1080x1620`) is byte-identical between `v1.10.1` and `v1.11.0`. | `docs/crops/audit_v1_11_0/crop_exam3_normal_p1.png` |
| `exam3_small` p1 (`cover`) | **No** (`41453d0d3da0...` unchanged since `1.8.0-rc1`) | `0 px` | None | `8,739 -> 8,739` (`0`) | Same as `exam3_normal` p1: `0` pixels changed between `v1.10.1` and `v1.11.0`. | `docs/crops/audit_v1_11_0/crop_exam3_small_p1.png` |
| `synthetic` p1–3 | **Yes** (`6ccefdfd... -> c0956b20...`) | `p1: 278,631 px`<br>`p2: 264,112 px`<br>`p3: 189,404 px` | Full text area (`y=[168..2180]`) | N/A (no device capture) | `tools/golden/synthetic.json` had not been updated since `07f4b78` (`v1.8.0`), because intermediate golden updates (`08889f2`, `8bc97c9`, `91b5736`, `3938782`) invoked `corpus.py --only <corpus> --update-golden` (which skips `synthetic`). When `corpus.py --update-golden` was run across all suites in `0782f4a` (`v1.10.2`), `synthetic.json` caught up with all Stage C–H changes (including `float32` justified pen accumulation, cross-box dash kerning, and the schema header format `"corpus": "synthetic", "engine_version": "1.10.2"` replacing `"environment_fingerprint"`). | `docs/crops/audit_v1_11_0/crop_synthetic_p1.png`, `crop_synthetic_p2.png`, `crop_synthetic_p3.png` |

---

## 4. Part B3 — Duplicate Scoring Script Cleanup
- Removed `tools/score_dir.py` (`git rm tools/score_dir.py`), which duplicated `tools/score_all.py` with an ad-hoc positional CLI (`<epub> <cap_dir> <size_px> <pitch> <x0> <right>`). All multi-dataset and single-dataset scoring now goes through `tools/score_all.py`.
