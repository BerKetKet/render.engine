# Vertical Rhythm & Margin Calibration Inventory (`layout.py`, `page.py`, `config.py`)

## 1. Geometry-Keyed & Empirical Spacing Branches

| Location | Mechanism / Constant | Current Expression | Derived From (Corpus & Pages) | Status |
|---|---|---|---|---|
| `config.py:134` | `vem_px()` | `round(size_px() * pitch_ratio) / 1.2` (`47.5 px` at 42/57; `56.67 px` at 45/68; `42.5 px` at 34/51) | `probe` p.24–30 (`b7_headings`), `exam1` p.29–30 (`e06_headings`) | Fitted on 42px & 45px |
| `page.py:211-235` | `heading_sizes` & `heading_margins` | `h1..h6` multipliers `(1.5, 1.3, 1.15, 1.0, 0.9, 0.8)` and `(mt_em, mb_em)` table | `probe` p.24–25, `exam1` p.29–30, `exam2` X01–X17 | Needs cross-geometry formula validation at 34px (`exam3_small` p.23, 43) |
| `page.py:242-265` | Heading top-of-page & consecutive heading adjustments | Fixed `-1 px` / `-2 px` / `+1 px` adjustments on `mt` and `mb` | `probe` p.24, `exam1` p.29, `exam2` p.7–8 | Empirical per-level offsets |
| `page.py:305-320` | Heading line-breaking (`balance_heading`) | Balanced 2-line split when `len(words) >= 3` | `exam1` p.19 (`E04`), `exam2` p.3 (`X01`) | Needs general rule for `exam3_small` p.3 (`E01 The Ferryman's Almanac`) |
| `epub.py:420-438` | `em` basis for `margin-left` / `margin-right` | Uses `base_root_em_px` (`28.8125 px`) when `abs(val) >= 2.0`, else `size_px()` | `exam2` p.14–15 (`2em`, `3em`), `probe` p.81 (`2em`, `4em`) | Fails at `1em` (`exam3_normal` p.48, `exam3_small` p.31 where `1em` also uses `28.8125 px`) |
| `layout.py:820-845` | Ragged terminal-word hyphen guard | Blocks hyphenation on the last word of a ragged line unless word exceeds measure | `exam2` X11 p.32–34 (`L00`–`L07`) | Blocks valid ragged hyphens on `exam3_normal` p.48 (`shep-/herd`, `anchor-/age`) |
| `page.py:510-545` | Widow/orphan and heading keep-with-next | `min_lines_after_heading = 1` or `2` depending on block kind | `exam1` E13, `exam2` X16 | Needs general keep-with-next rule for `exam3_normal` p.36 (`Heading 2` + 2 body lines) |
