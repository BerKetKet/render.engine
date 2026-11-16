# Stage E1 — Ragged Line-Breaking & Terminal-Word Hyphen Guard (`B7`)

## 1. Root Cause of Ragged Verse Line-Break Divergences
- **MEASURED**:
  - On `exam3_normal` p.48 (`E08 Verse, Epigraphs, Centred and Right-Aligned Text`), verse lines containing internal `<br/>` forced breaks (`has_internal_forced == True`) previously fell back to `_orig_break_kp` in `kindle_render/layout.py:822`.
  - `_orig_break_kp` used `ragged_bad = ((L - w) / L)^2 * 10000` instead of `break_kp`'s `r^2 * 1500` (`w / L` deficit) and lacked the `B7` terminal-word hyphenation guard (`is_last_word_break`), causing greedy hyphenation of `"shep-/herd"`, `"anchor-/age"` on `exam3_normal` p.48, `"wex-/combe"`, `"merid-/ian"`, `"cart-/wright"` on `exam3_normal` p.49, and `"sig-/nal"` on `exam3_small` p.31.
- **FIX**:
  - In `break_kp`, when `has_internal_forced` is `True` and `not varies_dropcap`, split `items` at each `<br/>` (`Penalty <= -INF`) and run `break_kp` independently on each forced-break segment.
- **MEASURED IMPACT**:
  - `exam3_normal` p.48: `21/24 -> 24/24` positional-exact lines (`diff_pixels: 81,020 -> 0` on all 24 verse/ragged bands!).
  - `exam3_normal` p.49: `22/28 -> 28/28` positional-exact lines (`diff_pixels: 162,155 -> 0` on all 28 bands!).
  - `exam3_small` p.31: `31/33 -> 33/33` positional-exact lines (`diff_pixels: 51,694 -> 0` on all 33 bands!).
  - `probe`, `exam1`, `exam2`: `0` changed pages (`100%` unchanged).
