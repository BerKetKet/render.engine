# Stage C Measurement & Cross-Geometry Findings (Ready to Apply on Resume)

## 1. Verified Cross-Geometry Rules (`(34, 51)`, `(42, 57)`, `(45, 68)`)
1. **Effective Unrounded Line-Spacing Pitch (`eff_body_pitch`)**:
   - Standard line-spacing preset has ratio `68 / 45 = 1.5111...` (`34 * 68/45 = 51.3778`, rounded to `51` for `1.0x` body text).
   - For scaled blocks (`b.heading` or `b.scale > 1.0`) when `extra_lead > 0`:
     `eff_body_pitch = max(float(std_body_pitch), (68.0 / 45.0) * c.size_px())`
   - Gives exact device heading pitches at `(34, 51)`: `(103, 77, 60, 51, 43, 34)` and `p.fs120`/`p.fs150` pitches `62` and `77` on `exam3_small` p.32, while keeping `(42, 57)` `(114, 86, 67, 57, 47, 38)` and `(45, 68)` `(136, 102, 80, 68, 56, 46)` identical.
2. **Heading Top & Bottom Margins (`mt`, `mb_est`) & Page-Top Offset (`C1`–`C4`)**:
   - Using 2-to-3 digit base multipliers `mt_base_em = (0.66, 0.81, 0.963, 1.32, 1.64, 2.29)` and `mb_base_em = (0.66, 0.822, 0.963, 1.32, 1.65, 2.30)` with `mt_lead_k = (0.10, 0.28, 0.25, 0.0, 0.25, 0.25)` and `mb_lead_k = (0.10, 0.05, 0.40, 0.10, 0.27, 0.28)` plus `+1 px` (`c.heading_top_extra_px`) for `h1` at page top (and after `<p>`) across ALL geometries:
     - `(34, 51)`: `mt = [57 (+1=58), 53, 49, 56, 59, 65]`, `mb = [57, 53, 50, 57, 60, 67]`
     - `(42, 57)`: `mt = [63 (+1=64), 58, 54, 63, 65, 73]`, `mb = [63, 59, 54, 63, 65, 73]`
     - `(45, 68)`: `mt = [75 (+1=76), 71, 66, 75, 79, 89]`, `mb = [75, 70, 67, 75, 79, 89]`
   - Resolves `exam3_small` p.23 (`22/22` positional exact bands) and `exam3_normal` p.36 (`17/17` positional exact bands).
3. **Heading Wrap with Inter-Word Shrink (`C4` & Stage D `exam3_normal` p.36)**:
   - In `layout.py:break_balanced_ragged`, allowing `w <= L + z` (where `z = Z[b] - Z[s]` is cumulative `Glue.shrink`) with `w_last = 0.65` (M0 Section 2) and removing `runt_min_chars`:
     - Wraps `exam3_small` p.3 `h1` (`E01 The Ferryman's Almanac`) as `['E01 The Ferryman’s', 'Almanac']` (device band heights `70` then `54`).
     - Wraps `exam3_normal` p.36 `h2` into 3 lines (`['Heading 2: the gentle', 'blacksmith of Oakenshaw', 'and its long wandering title']`), so `h2` + 2 body lines end at `y = 2201 <= 2203` and stay on page 36.
4. **Horizontal `em`/`rem` Resolution & `blockquote` UA Margin (`C1(d)`)**:
   - Removing `and abs(v) >= 1.99` in `epub.py:_em` resolves `1em` on `p.in1` (`exam3_normal` p.48, `exam3_small` p.31) against `base_root_em_px` (`28.8125 px` -> `x = 108`).
   - Ignoring CSS `margin-left`/`margin-right` on `<blockquote>`/`<figure>` in `epub.py` preserves the Kindle UA `blockquote_margin_ratio` (`43.6 px` at `922 px` measure) on `exam3_normal` p.38 and `exam3_small` p.24.
   - Scaling `<sub>` baseline shift as `int(0.30 * cfg.size_px() + 0.4)` (`10 px` at `34 px`, `13 px` at `42 px` and `45 px`) fixes `H<sub>1</sub>O` band heights on `exam3_small` p.27–30.
