# Round 1 Fidelity Report (`v1.7.0` -> `v1.8.0`)

## Summary of Measured Improvements (Item 1 Complete; Items 2-8 Queued)

| Page | Baseline v1.7.0 Diff Px | v1.8.0 (Item 1) Diff Px | Net Diff Px Reduction | Baseline Pos / PI Lines | v1.8.0 Pos / PI Lines |
|---|---:|---:|---:|---:|---:|
| `exam2` p.8 (`x03_manual`) | 57,561 | 48,360 | -9,201 | 7/31 / 7/31 | 10/31 / 10/31 |
| `exam2` p.13 (`x05_recipe`) | 43,184 | 28,473 | -14,711 | 1/16 / 1/16 | 1/16 / 1/16 |
| `exam2` p.36 (`x12_structure`) | 274,572 | 253,551 | -21,021 | 2/24 / 9/24 | 2/24 / 10/24 |
| `exam1` p.47 (`e11_blocks`) | 156,847 | 143,039 | -13,808 | 1/19 / 4/19 | 1/19 / 5/19 |
| `probe` p.88 (`e3_blocks`) | 115,753 | 105,804 | -9,949 | 1/15 / 3/15 | 1/15 / 3/15 |
| **Total (5 Table Pages)** | **647,917** | **579,227** | **-68,690** | **12/105 / 24/105** | **15/105 / 29/105** |

## Item 1 Rules & Provenance (`MEASURED`)
1. **Unbreakable Word Floor (`min_w`)**: Every column `ci` enforces `min_w[ci] >= max_token_width(ci) + col_pad2(ci)` across all header and data cells (`cs == 1`), where headers split only at spaces or after `/` in compound unit tokens (`len > 4`), never mid-word.
2. **Iterative Min-Content Clamping Solver**: Columns with `max_w[i] <= avail_w / ncols` lock at `max_w[i]`; remaining unlocked columns allocate remaining width proportionally to `max_w[i]` with iterative clamping at `min_w[i]`, preventing wide data columns from squeezing multi-word header columns below their longest word (`Recovery (min)` wraps at space as `Recovery / (min)`).
3. **Preferred 1.0x Table Width Scaling (`sc_tbl`)**: Narrow tables (`tot_1x <= avail_w`) use `sc_tbl = 1.0`; 4+ column wide tables clamp at `sc_tbl = 0.70` (`size26 = 1882`); 3-column wide tables scale by `avail_w / W_pref_1x` (`size26 = 2585` on `exam2` p.36; `size26 = 2494` on `exam1` p.47).
4. **Caption Centering & Multi-Line Wrapping**: Captions center over `[x0, x0 + avail_w + 1]` (`0` diff px on both caption lines of `exam2` p.8) and fall back to greedy multi-line wrapping within `avail_w` when exceeding two `0.72 * avail_w` lines.
5. **Subpixel Bottom Rule & 4x4 Supersampled Vector Expand Icon**: Bottom rule spans `[x0, x0 + table_w]` with 3.0-px fractional coverage (`[g_top, 0, 0, 255 - g_top]`) and 4x4 subpixel vector expand icon (`95 x 52/53`).
