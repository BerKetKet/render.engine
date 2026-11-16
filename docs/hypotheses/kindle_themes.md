# Kindle Reading Theme Configurations

## 1. Theme Preset Values (from a sample size of 5490 captures over all possible combinations of settings) (`1080 × 2340 px` at `420 dpi`, `D = 2.625`)

| Parameter | Compact | Standard | Large | Low Vision |
| :--- | :--- | :--- | :--- | :--- |
| **Typeface** | Preserves active font (`Bookerly` default) | Preserves active font (`Bookerly` default) | Preserves active font (`Bookerly` default) | Forces `Amazon Ember Bold` |
| **Font Size (`px` / `sp`)** | `34.0 px` (`12.95 sp`) | `42.0 px` (`16.00 sp`) | `45.0 px` (`17.14 sp`) | `63.53 px` (`24.20 sp`) |
| **Font Size (`26.6` units)** | `2176` (`S = 2.176`) | `2688` (`S = 2.688`) | `2880` (`S = 2.880`) | `4066` (`S = 4.066`) |
| **Line Pitch (`P`)** | `51 px` (`1.500 × F`) | `57 px` (`1.357 × F`) | `68 px` (`1.511 × F`) | `87 px` (`1.369 × F`) |
| **Baseline Offset (`b_base`)** | `36 px` | `41 px` | `48 px` | `64 px` |
| **Heading Vertical `em` (`V_em`)** | `42 px` (`floor(51 / 1.2)`) | `47 px` (`floor(57 / 1.2)`) | `56 px` (`floor(68 / 1.2)`) | `72 px` (`floor(87 / 1.2)`) |
| **Body Vertical `em` (`V_em,p`)** | `42.50 px` (`51 / 1.2`) | `47.50 px` (`57 / 1.2`) | `56.67 px` (`68 / 1.2`) | `72.50 px` (`87 / 1.2`) |
| **Horizontal Margins (`x0 .. x1`)** | `39 .. 1041 px` (`39 px` per side) | `39 .. 1041 px` (`NONE`) or `79 .. 1001 px` (`NARROW`) | `79 .. 1001 px` (`79 px` per side) | `79 .. 1001 px` (`79 px` per side) |
| **Line Measure (`L`)** | `1002 px` (`64128` in `26.6`) | `1002 px` (`64128`) or `922 px` (`59008`) | `922 px` (`59008` in `26.6`) | `922 px` (`59008` in `26.6`) |
| **Vertical Content Window (`y`)** | `168 .. 2203 px` (`2035 px` height) | `168 .. 2203 px` (`2035 px` height) | `168 .. 2203 px` (`2035 px` height) | `168 .. 2203 px` (`2035 px` height) |
| **Full-Page Line Capacity** | `39 lines` | `35 lines` | `29 lines` | `23 lines` |
| **Alignment & Boldness** | Justified, Boldness `0` | Justified, Boldness `0` | Justified, Boldness `0` | Justified, Boldness `4` (`+52 FUnits`) |

## 2. Likely Internal Parameterization & Scaling Rules

### Horizontal Margin Modes (`margin_mode` $\in \{0, 1, 2\}$)
- `0` (`NONE` / Smallest): $x_0 = 39\text{ px}, \; x_1 = 1041\text{ px}, \; L = 1002\text{ px}$
- `1` (`NARROW` / Medium): $x_0 = 79\text{ px}, \; x_1 = 1001\text{ px}, \; L = 922\text{ px}$
- `2` (`WIDE` / Largest): $x_0 = 119\text{ px}, \; x_1 = 961\text{ px}, \; L = 842\text{ px}$

### Line Spacing Modes (`line_spacing_mode` $\in \{0, 1, 2\}$)
Each font-size step $i$ has a base line-height entry $\text{base\_pitch}[i] = \lfloor \text{dp}_i \cdot D + 0.5 \rfloor$ (where $D = \text{dpi} / 160 = 2.625$), and the active line pitch adds the spacing mode offset $\Delta P(\text{mode})$:

$$P(i, \text{mode}) = \text{base\_pitch}[i] + \Delta P(\text{mode})$$

where $\text{mode} = 0$ (`NARROW`), $\text{mode} = 1$ (`NORMAL`), and $\text{mode} = 2$ (`WIDE`).

### Text Alignment Modes (`alignment` $\in \{0, 1\}$)
- `0` (`JUSTIFY`): Full Knuth-Plass justification with dynamic space shrink $S_{\text{shrink}} = \frac{101}{577} w_{\text{space}}$ and Bresenham integer pixel remainder distribution.
- `1` (`LEFT`): Ragged-right Knuth-Plass optimization with zero cubic glue badness over $r \in [-0.5, +\infty)$, quadratic line-shortfall penalty $100 \cdot ((L - W)/L)^2$, and discretionary hyphen penalty $100$.

### Preset Independence of Document Position
Switching between `Compact`, `Standard`, `Large`, or `Low Vision` updates the layout settings hash (invalidating cached page bounds) while keeping the reading anchor tuple $(s, e, c)$ (section ID, element hash, character offset) invariant, re-paginating the active section and landing on the newly computed page interval $[\mathbf{p}_k, \mathbf{p}_{k+1})$ containing $(s, e, c)$.
