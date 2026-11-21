# Hypothesis M: how the device scales and lays out collapsed tables (pre-registered; measured by an independent reviewer)

## Statement
The device lays a table out at 1x, then scales the whole table uniformly so that its width equals the measure when it is wider.

1. Column width at 1x: `w_c = clamp(minc_c, maxc_c, CAP_EM * font_px) + PAD_EM * font_px`, where `maxc_c` is the max-content width of the widest single-line cell in the column (bold face for header cells), `minc_c` is the min-content width of the header cells only (words split after `-` and `/`), and font_px is the unscaled body font size.
2. Scale: `s = min(1, avail / sum(w_c))` (avail = right - x0 - collapsed_table_margin_px). No floor was observed (Large 9-column: 0.325).
3. Everything inside the table is the 1x layout multiplied by `s`: font size `s*size`, column widths, cell wraps (same wrap points as at 1x), row pitch `s*(n_lines*pitch + row_pad_1x)`.

## Evidence
- Device scale of each table measured by template matching of engine row bands against the device page (`tools/lab_tables/measure_scale.py`, +/- 0.01): data in `docs/data/table_scale_measurements.json` (26 tables x 3 themes).
- Fit of PAD_EM, CAP_EM on 46 non-span tables: PAD_EM 1.37, CAP_EM 6.5, mean relative scale error 0.76% (max 6.4%). The pre-1.11.12 engine formulas were off by up to 40% (for example Standard 6-column sentence table: device 0.515, old 0.399; Large 9-column: device 0.325, old 0.35; Standard Name/Description table: device 0.97, old 0.70).
- With uniform layout (columns = s * w_c, row pitch = s * 1x pitch) the 9-column table, the 6-column sentence table and the Key/Value table match the device in column positions and wraps (Compact p4, p6).
- A joint sweep of the cap (scale and widths together) on the 3-theme pixel total prefers CAP_EM about 7.5 (24.42M) over 6.5 (24.62M), 7.0 (24.52M), 8.0 (24.52M), 9.0 (24.62M), although the scale-only fit prefers 6.5 (mean error 1.3% at 7.5). Open question: the true quantity is probably a wrap rule for long cells, not a cap.

## Known residuals (device vs model)
1. Long 3-column table (Table 5.1: Row / Detail / Amount, 31 rows, Detail max-content about 36 em): device scale 0.967 / 0.967 / 0.816 (Standard / Compact / Large). Model gives 1.0. Implied 1x table width 916 / 999 / 958 px; implied Detail wrap width at 1x about 452 / 588 / 439 px (10.0 / 15.1 / 8.8 em). The engine keeps the legacy values 0.96 / 0.81 for this case. Find the rule (it is not a function of avail alone: Standard and Compact have the same scale, Large much lower).
2. A data cell with a very long unbreakable word (Key/Value table "supercalifragilistic..."): device 0.971 / 0.914 / 0.99, model 1.0. Header-only min-content was enough elsewhere; probably a small data-cell contribution.
3. 3-column tables in Large (Large k16 device 0.92, model 0.86; k19 0.948; k22 0.948; k23 0.531: small tables with a long cell).
4. Spans (colspan/rowspan) are not modelled: cells with cs > 1 are ignored in the width sum.

## Pass criteria
Three-theme total diff on tables_images / ti_compact / ti_large improves against the previous release, no lost exact pages, page counts unchanged (44 / 35 / 57), all other goldens unchanged.
