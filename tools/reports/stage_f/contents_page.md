# Stage F — Contents Page (`nav` / p.2) & Subpixel Link Underlines

## 1. Measured Device Rules Across All 3 Geometries (`(34, 51)`, `(42, 57)`, `(45, 68)`)
1. **Ordered List Horizontal Indent (`ol_indent_em = 2.1054`)**:
   - **MEASURED**: Across all 5 corpora, `<ol><li>` text starts at `x0 + 2.1054 * size_px` in 26.6 fixed-point coordinates (`150.58 px` at `34 px`, `127.42 px` / `167.42 px` at `42 px`, `173.74 px` at `45 px`), replacing the integer-rounded `88/42 = 2.0952` approximation.
   - **IMPACT**: Achieves `0` glyph diff pixels across all `80/80` TOC lines on `p.2` AND gains `+101` positional-exact lines on body `<ol>` pages (`probe` p.87–88, `exam1` p.45–46, `exam2` p.7/8/12/35, `exam3_normal` p.39–40, `exam3_small` p.24–25), making `exam2` p.7 and `exam2` p.12 `100%` bitwise identical!
2. **Skia Antialiased Subpixel Link Underline (`role="link_underline"`)**:
   - **MEASURED**: On `<a href>` links, Kindle draws a continuous subpixel rectangle `[x0_fl, yt, x1_fl, yb]` per line using separable Skia coverage `alpha(x, y) = min(cov_x(x), cov_y(y))` blended over the glyph canvas, where `base_thk = round(0.065 * size_px)` (`2 px` at `34 px`, `3 px` at `42 px` & `45 px`) and `yt = baseline + base_thk + 0.02612 * size_px + 0.00245 * pitch - 0.5855`.

## 2. Before vs After on Contents Page (`p.2`) & Corpus Totals

| Corpus | `p.2` Before Diff Px | `p.2` After Diff Px | `p.2` Pos Lines (Before -> After) | Corpus Exact Pages (Before -> After) | Corpus Pos Lines (Before -> After) |
|---|---:|---:|---:|---:|---:|
| `probe` | `46,056` | **`0`** (`EXACT`) | `1/27 -> 27/27` | `37/86 -> 38/86` (`+1`) | `2,703 -> 2,741 / 2,863` (`+38`) |
| `exam1` | `28,375` | **`0`** (`EXACT`) | `1/21 -> 21/21` | `42/70 -> 43/70` (`+1`) | `1,405 -> 1,439 / 1,568` (`+34`) |
| `exam2` | `30,378` | **`0`** (`EXACT`) | `1/27 -> 27/27` | `35/65 -> 38/65` (`+3`) | `1,322 -> 1,390 / 1,529` (`+68`) |
| `exam3_normal` | `46,627` | **`0`** (`EXACT`) | `1/18 -> 18/18` | `42/82 -> 43/82` (`+1`) | `1,835 -> 1,869 / 2,027` (`+34`) |
| `exam3_small` | `70,891` | **`0`** (`EXACT`) | `1/18 -> 18/18` | `16/54 -> 17/54` (`+1`) | `1,430 -> 1,474 / 1,651` (`+44`) |
| **TOTAL (All 5)** | **`222,327`** | **`0` (`5/5 EXACT`)** | **`5/111 -> 111/111`** | **`172/357 -> 179/357` (`+7`)** | **`8,695 -> 8,913 / 9,638` (`+218`)** |
