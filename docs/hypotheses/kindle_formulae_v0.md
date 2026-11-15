# Kindle Layout and Rendering Formulae

## 1. Heading Block Spacing

Vertical structural em unit derived from body line pitch $P$:

$$V_{\text{em}}(P) = \lfloor P / 1.2 \rfloor$$

Top and bottom block margins in pixels for heading level $k \in \{1, \dots, 6\}$ with font-size multiplier $s_k$ and user-agent margin factors $m_{\text{top}, k}, m_{\text{bot}, k}$:

$$\text{mt\_px}(h_k) = \lfloor m_{\text{top}, k} \cdot s_k \cdot V_{\text{em}}(P) + 0.5 \rfloor$$

$$\text{mb\_px}(h_k) = \lfloor m_{\text{bot}, k} \cdot s_k \cdot V_{\text{em}}(P) + 0.5 \rfloor$$

Heading multipliers and margin factors:
- $k=1$: $s_1 = 2.00, \; m_{\text{top},1} = 0.670, \; m_{\text{bot},1} = 0.670$
- $k=2$: $s_2 = 1.50, \; m_{\text{top},2} = 0.830, \; m_{\text{bot},2} = 0.835$
- $k=3$: $s_3 = 1.17, \; m_{\text{top},3} = 0.965, \; m_{\text{bot},3} = 1.000$
- $k=4$: $s_4 = 1.00, \; m_{\text{top},4} = 1.330, \; m_{\text{bot},4} = 1.330$
- $k=5$: $s_5 = 0.83, \; m_{\text{top},5} = 1.670, \; m_{\text{bot},5} = 1.670$
- $k=6$: $s_6 = 0.67, \; m_{\text{top},6} = 2.330, \; m_{\text{bot},6} = 2.350$

Vertical margin collapse between two adjacent block boxes:

$$G_{\text{box}}(\text{prev}, \text{next}) = \max(\text{mb\_px}(\text{prev}), \text{mt\_px}(\text{next}))$$

Vertical pixel distance from the bottom ink bound of the previous line to the top ink bound of the next line, where $b_{\text{base}}$ is the baseline offset within line pitch $P$, $d_{\text{ink}}$ is the glyph descender ink extent below baseline, and $a_{\text{ink}}$ is the glyph ascender ink extent above baseline:

$$G_{\text{ink}}(\text{prev}, \text{next}) = (P_{\text{prev}} - b_{\text{base,prev}} - d_{\text{ink,prev}}) + G_{\text{box}}(\text{prev}, \text{next}) + (b_{\text{base,next}} - a_{\text{ink,next}})$$

## 2. Heading Wrap Logic

Headings wrap within the full content measure $L$ without hyphenation and bind opening parenthetical tokens to the immediately following word. Given $m$ candidate lines with natural widths $W_1, \dots, W_m \le L$, the line breaker minimizes the total squared relative slack with a reduced weight $w_{\text{last}} = 0.65$ on the final line:

$$J(W_1, \dots, W_m) = \sum_{k=1}^{m-1} \left(1 + \left(\frac{L - W_k}{L}\right)^2\right) + \left(1 + 0.65 \left(\frac{L - W_m}{L}\right)^2\right)$$

## 3. Page-Top Headings

When a heading $h_k$ is placed at the top of a page after a page break or top container boundary $y_0$, its top margin is retained:

$$y_{\text{box\_top}} = y_0 + \text{mt\_px}(h_k) + \mathbb{I}(k = 1)$$

$$y_{\text{baseline}} = y_{\text{box\_top}} + b_{\text{base}}(h_k)$$

## 4. Em and Rem Unit Resolution

Horizontal inline and indentation properties resolve against the element font size $F$ (in pixels):

$$\text{indent}_{\text{text}}(c) = c \cdot F$$

$$\text{spacing}_{26}(c) = \lfloor c \cdot F_{26} + 0.5 \rfloor$$

$$\text{indent}_{\text{blockquote}} = \text{indent}_{\text{dd}} = 1.12857 \cdot F$$

$$\text{indent}_{\text{ul}}(d) = 2.0 \cdot d \cdot F \quad (d \in \{1, 2, \dots\})$$

$$\text{indent}_{\text{ol}} = 2.1052827 \cdot F$$

Root container units ($\text{rem}$) resolve against the base UI density scale $D = \text{dpi} / 160$:

$$1\text{ rem} = 11.0 \cdot D$$

Vertical paragraph block margins resolve against the continuous vertical structural unit $V_{\text{em,p}}(P) = P / 1.2$:

$$\text{mt\_px}(p) = \lfloor m_{\text{top}} \cdot V_{\text{em,p}}(P) \rfloor$$

$$\text{mb\_px}(p) = \lfloor m_{\text{bot}} \cdot (\lfloor P / 1.2 \rfloor + 0.4) + 0.5 \rfloor$$

## 5. Page Break and Keep Rules

Let $y_{\text{max}}$ be the bottom viewport boundary, $y_{\text{cursor}}$ the current vertical position, and $R = \lfloor (y_{\text{max}} - (y_{\text{cursor}} + \text{mt\_px})) / P \rfloor$ the number of whole lines that fit on the current page.

Heading keep-with-next condition for a heading of $N_h$ lines followed by a block with line pitch $P_{\text{next}}$:

$$y_{\text{cursor}} + \text{mt\_px}(h_k) + N_h \cdot P_{h_k} + \text{mb\_px}(h_k) + P_{\text{next}} \le y_{\text{max}}$$

If this inequality fails, the heading pushes to the next page.

Paragraph widow and orphan pagination for a paragraph of $N$ lines with minimum threshold $w = 2$, returning $(k_{\text{current}}, \text{push\_rest})$:

$$(k_{\text{current}}, \text{push\_rest}) = \begin{cases} (1, \text{false}) & \text{if } N = 1 \text{ and } R \ge 1 \\ (N, \text{false}) & \text{if } R \ge N \\ (0, \text{true}) & \text{if } 2 \le N \le 2w - 1 \text{ and } R < N \\ (0, \text{true}) & \text{if } N \ge 2w \text{ and } R < w \\ (\min(R, N - w), \text{true}) & \text{if } N \ge 2w \text{ and } w \le R < N \end{cases}$$

## 6. Ragged Line Breaking

For ragged alignments (left, right, center), line breaking uses dynamic programming over feasible lines satisfying the maximum inter-word shrink bound $W - L \le 0.5 \cdot m_{\text{spaces}} \cdot S_{\text{shrink}}$, where $S_{\text{shrink}} = \frac{101}{577} w_{\text{space}}$. Within this feasible window, cubic glue badness is zero and the demerit of a non-terminal line of width $W \le L$ is:

$$D_{\text{ragged}}(W) = \left(l_{\text{pen}} + 100.0 \left(\frac{L - W}{L}\right)^2 + p_{\text{hyph}} \cdot \mathbb{I}_{\text{hyph}}\right)^2$$

where $l_{\text{pen}} = 10.0$ is the base line penalty, $p_{\text{hyph}} = 100.0$ is the discretionary hyphen penalty, and $\mathbb{I}_{\text{hyph}} \in \{0, 1\}$ indicates whether the line ends at a discretionary hyphen. For the terminal line of a paragraph ($j = n$), the shortfall term is zero.

## 7. Contents Page Pitch and Link Underlines

Table of Contents list items use the standard body line pitch:

$$P_{\text{toc}} = P_{\text{body}}$$

Link underlines are rendered as an edge-antialiased rectangle spanning horizontal coordinates $[x_0, x_1]$ and vertical coordinates $[y_{\text{base}} + y_{u,0}, y_{\text{base}} + y_{u,1}]$ with $y_{u,0} = 3.651\text{ px}$ and $y_{u,1} = 6.651\text{ px}$. For each integer pixel $(x, y)$, horizontal and vertical coverage are:

$$\alpha_x(x) = \text{clip}(\min(x + 1 - x_0, x_1 - x), 0, 1)$$

$$\alpha_y(y) = \text{clip}(\min(y + 1 - (y_{\text{base}} + y_{u,0}), (y_{\text{base}} + y_{u,1}) - y), 0, 1)$$

Combined pixel coverage is the intersection of the two signed distance bounds:

$$\alpha(x, y) = \min(\alpha_x(x), \alpha_y(y))$$

## 8. Image Resampling and Scaling

Inline images with intrinsic dimensions $(W_0, H_0)$ scale by the display density factor $D = \text{dpi} / 160$ and sit on the text baseline:

$$W = \lfloor W_0 \cdot D + 0.5 \rfloor, \qquad H = \lfloor H_0 \cdot D + 0.5 \rfloor, \qquad y_{\text{top}} = y_{\text{baseline}} - H$$

Standalone block images scale by the block image factor $s_0 = 1.96$, clamped to maximum content dimensions $(W_{\max}, H_{\max})$:

$$s = \min\left(s_0, \frac{W_{\max}}{W_0}, \frac{H_{\max}}{H_0}\right), \qquad W = \lfloor W_0 \cdot s + 0.5 \rfloor, \qquad H = \lfloor H_0 \cdot s \rfloor$$

Pixel values are interpolated via separable bilinear resampling:

$$I(x, y) = (1 - f_x)(1 - f_y) I_{00} + f_x(1 - f_y) I_{10} + (1 - f_x) f_y I_{01} + f_x f_y I_{11}$$

where $u = (x + 0.5)\frac{W_0}{W} - 0.5$, $v = (y + 0.5)\frac{H_0}{H} - 0.5$, $f_x = u - \lfloor u \rfloor$, and $f_y = v - \lfloor v \rfloor$.

## 9. Stable Anchor Position Mapping

A reading position is represented as a layout-invariant tuple over section index $s$, element hash $e$, and character offset $c$:

$$\mathbf{p} = (s, e, c)$$

Given a typography configuration $\theta$, pagination partitions the document into ordered page intervals $\{[\mathbf{p}_k(\theta), \mathbf{p}_{k+1}(\theta))\}_{k=1}^{M}$. After a configuration change $\theta \to \theta'$, the active page index $k^*$ is selected by binary search such that:

$$\mathbf{p}_{k^*}(\theta') \le \mathbf{p} < \mathbf{p}_{k^*+1}(\theta')$$

## 10. Fixed-Point Rounding Pipeline

1. Font scaling factor from pixel size $F$ to 26.6 fixed-point units per font design unit ($\text{upem} = 1000$):

$$F_{26} = \lfloor 64 \cdot F + 0.5 \rfloor, \qquad S = \frac{F_{26}}{\text{upem}}$$

2. Glyph advance and pairwise kerning in 26.6 fixed-point units:

$$\text{adv}_{26}(g) = \lfloor \text{adv}_{\text{fu}}(g) \cdot S \rfloor + \Delta_{\text{bold}, 26}$$

$$\text{kern}_{26}(g_1, g_2) = \lfloor \text{kern}_{\text{fu}}(g_1, g_2) \cdot S + 0.5 \rfloor$$

3. Inter-word justification glue distribution for $m$ spaces with total deficit $\Delta_{26} = L_{26} - W_{26}$, integer pixel deficit $\Delta_{\text{px}} = \lfloor \Delta_{26} / 64 + 0.5 \rfloor$, base quotient $q = \lfloor \Delta_{\text{px}} / m \rfloor$, and remainder $r = \Delta_{\text{px}} \bmod m$:

$$g_{i, 26} = 64 \cdot \left(q + \mathbb{I}\left(((i + 1) \cdot r) \bmod m < r\right)\right), \quad i \in \{0, \dots, m - 1\}$$

4. Horizontal screen pixel placement from 26.6 pen position $\text{pen}_{26}$, line start $\text{start}_{26}$, optical margin overhang $\text{overhang}_{26}$, and glyph bitmap left bearing $l_{\text{bmp}}$:

$$x_{\text{screen}} = \left\lfloor \frac{\text{start}_{26} + \text{overhang}_{26} + \text{pen}_{26}}{64.0} + 0.5 \right\rfloor + l_{\text{bmp}}$$

5. Vertical baseline offset within a line box of pitch $P$ using typographic ascender ratio $\alpha_{\text{typo}} = \frac{\text{sTypoAscender}}{\text{upem}} = 0.802$:

$$b_{\text{base}}(P, F) = \left\lfloor \frac{P - F}{2.0} + \alpha_{\text{typo}} \cdot F + 0.5 \right\rfloor$$

$$y_{\text{baseline}} = \lfloor y_{\text{cursor}} + 0.5 \rfloor + b_{\text{base}}(P, F)$$
