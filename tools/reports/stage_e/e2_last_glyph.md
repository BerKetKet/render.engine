# Stage E2 — Last-Glyph `1 px` Right-Edge Rounding Investigation

## 1. Complete 5-Corpus Census
Across all 5 corpora, we identified every justified line where shifting only the final glyph's horizontal coordinate (`gs[-1].x -= 1`) makes the rendered line band `100%` bitwise identical to the device capture:
- **Shared Geometric Property**: On every such line (`exam1` p.3, p.18; `exam3_normal` p.3, p.4, p.18; `exam3_small` 24 lines), the line ends flush against `cfg.right = 1001` (`start26 + off + adv26 == 1001 * 64 = 64064`) and the terminal glyph has a half-pixel 26.6 advance (`adv26 & 63 == 32`):
  - `'k'` at `45 px`: `adv26 = 1696` (`26.50 px`), `start26 + off = 62368` (`974.50 px`), `int(974.50 + 0.5) = 975` vs device `974`.
  - `'m'` at `45 px`: `adv26 = 2848` (`44.50 px`), `start26 + off = 61216` (`956.50 px`), `int(956.50 + 0.5) = 957` vs device `956`.
  - `'e'` at `34 px`: `adv26 = 1120` (`17.50 px`), `start26 + off = 62944` (`983.50 px`), `int(983.50 + 0.5) = 984` vs device `983`.

## 2. Candidate Evaluation Against the Zero-Regression Rule
We tested all three candidate mechanisms `(a)`, `(b)`, and `(c)` across all 5 corpora:
- On the exact same corpora (`exam1`, `exam3_normal`, `exam3_small`), there are **61 lines** ending with the exact same terminal glyphs (`'k'` at `45 px`, `'m'` at `45 px`, `'e'` at `34 px`) at the exact same `start26 + off` (`974.50 px -> 975`, `956.50 px -> 957`, `983.50 px -> 984`) that are **already `100%` bitwise identical** to the device captures (`4` on `exam1`, `8` on `exam3_normal`, `49` on `exam3_small`) versus `29` non-exact lines on those corpora (`34` including `probe`).
- Specifically, on `exam1` and `exam3_normal`, shifting `(start26 + off) & 63 == 32` left by `1 px` on the last glyph regresses `4` exact lines on `exam1` and `8` exact lines on `exam3_normal` (including breaking exact pages `p.19`, `p.23`, `p.24`, `p.27`, `p.29`, `p.54`, `p.57` on `exam3_normal`).
- **Conclusion**: Because the `0.5 px` tie depends on sub-`1/64 px` float justification space distribution across the preceding words on the line, any deterministic rule based on 26.6 coordinates or float advance sums regresses existing bitwise-identical pages. Per the Stage E2 rule (*"Accept only if zero regressions"*), `place_phase = 0.5` is preserved unchanged.
