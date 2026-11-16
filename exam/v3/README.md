# Kindle Render Exam v3 (`kindle_exam_v3.epub`) — Ground Truth Corpus

## 1. Overview
- **Fixture**: `kindle_exam_v3.epub`
- **Device**: Samsung Galaxy M32 (`SM-M325FV`, Android 13 TrebleDroid GApps, 1080x2340 @ ~450 dpi)
- **Reader App**: Amazon Kindle for Android `v8.159.0.100 (2.0.115180.0)`
- **Total Batches**: 14 (12 Bookerly font sizes under standard baseline + Compact theme preset + Large theme preset)
- **Total Pages Captured**: 2,307 hardware PNG screenshots
- **Capture Tool**: `scripts/capture_exam_r20.py` with multi-chunk resume, body-hash change verification, and 3-tap termination confirmation.

---

## 2. Verified Reading Configurations

### Standard Baseline Series (`size_00_Bookerly` to `size_11_Bookerly`)
- **Theme Preset**: Standard baseline preset
- **Font Family**: Bookerly (default serif)
- **Font Size**: Slider notch 1 to 12 of 12 (0 to 11 index)
- **Line Spacing**: Notch 2 of 5 (Position 1, $X \approx 386$, one step above minimum)
- **Paragraph Spacing**: Notch 1 of 5 (Position 0, $X \approx 233$, minimum)
- **Word Spacing**: Notch 1 of 5 (Position 0, $X \approx 233$, minimum)
- **Character Spacing**: Notch 1 of 5 (Position 0, $X \approx 233$, minimum)
- **Margins**: Medium / Normal (middle option, ~79.0–82.0 px median first ink column)
- **Alignment**: Justified (left option)
- **Reading Mode**: Immersive (status bar rows 0–139 white, bottom progress overlay hidden)
- **Bitwise Hash Verification**:
  - Size 0 `page_003.png`: SHA-256 `cb119890d14779da2ba8e0ec729eae4c7ce1eeb12e8035de5e7056b67f34c37f` (0 px differ against hardware baseline)
  - Size 4 `page_003.png`: SHA-256 `2c03013ba15db04292230cf3993b6578b9ff9cc08c3fe64d5aa3193f99f96290` (0 px differ against Standard preset default)

### Compact Theme Preset (`theme_Compact`)
- **Theme Preset**: Compact
- **Font Family**: Bookerly
- **Font Size**: Step 4 of 12 (index 3, ~3/12 in user notation)
- **Spacing Options**: All spacing options at 1/4 (minimum notch)
- **Margins**: Narrow (left option, ~40.0 px median first ink column)
- **Alignment**: Justified
- **Page Count**: 56 pages
- **Measured Line Pitch**: 53 px

### Large Theme Preset (`theme_Large`)
- **Theme Preset**: Large
- **Font Family**: Bookerly
- **Font Size**: Step 8 of 12 (index 7, ~7/12 in user notation)
- **Line Spacing**: Step 2 of 5
- **Paragraph / Word / Character Spacing**: Step 1 of 5 (minimum)
- **Margins**: Wide (right option, ~133.0 px median first ink column)
- **Alignment**: Justified
- **Page Count**: 124 pages
- **Measured Line Pitch**: 82 px

---

## 3. Summary Table of Batches

| Batch Folder | Theme | Font Size Step | Measured Pitch (px) | First Ink Column (px) | Total Pages | Stop Reason |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| `size_00_Bookerly` | Standard | 1/12 (index 0) | 51 | 79.0 | 54 | page did not change after 3 taps: end of book |
| `size_01_Bookerly` | Standard | 2/12 (index 1) | 56 | 80.0 | 59 | page did not change after 3 taps: end of book |
| `size_02_Bookerly` | Standard | 3/12 (index 2) | 59 | 80.0 | 69 | page did not change after 3 taps: end of book |
| `size_03_Bookerly` | Standard | 4/12 (index 3) | 63 | 80.0 | 73 | page did not change after 3 taps: end of book |
| `size_04_Bookerly` | Standard | 5/12 (index 4) | 68 | 80.0 | 82 | page did not change after 3 taps: end of book |
| `size_05_Bookerly` | Standard | 6/12 (index 5) | 71 | 80.0 | 89 | page did not change after 3 taps: end of book |
| `size_06_Bookerly` | Standard | 7/12 (index 6) | 76 | 80.0 | 100 | page did not change after 3 taps: end of book |
| `size_07_Bookerly` | Standard | 8/12 (index 7) | 83 | 81.0 | 121 | page did not change after 3 taps: end of book |
| `size_08_Bookerly` | Standard | 9/12 (index 8) | 91 | 81.0 | 145 | page did not change after 3 taps: end of book |
| `size_09_Bookerly` | Standard | 10/12 (index 9) | 127 | 82.0 | 196 | page did not change after 3 taps: end of book |
| `size_10_Bookerly` | Standard | 11/12 (index 10) | 171 | 93.0 | 520 | page did not change after 3 taps: end of book |
| `size_11_Bookerly` | Standard | 12/12 (index 11) | 230 | 85.0 | 719 | page did not change after 3 taps: end of book |
| `theme_Compact` | Compact | 4/12 (index 3) | 53 | 40.0 | 56 | page did not change after 3 taps: end of book |
| `theme_Large` | Large | 8/12 (index 7) | 82 | 133.0 | 124 | page did not change after 3 taps: end of book |
| **Total** | | | | | **2,307** | |

---

## 4. Kindle UI Aa Menu Reference & Settings Panels

### Aa Menu Sheet Behavior
- **Drag Handle Pill**: Located at $Y \approx 460\text{--}475$, centered at $X = 540$. When the reader opens the Aa menu, it defaults to a half-height sheet. Sliding up the pill handle expands the sheet to full screen, exposing the complete **Font Spacing** sub-menu including **Word Spacing** and **Character Spacing** sliders beneath **Line Spacing** and **Paragraph Spacing**.
- **Tab Coordinates (Half-Height Mode)**:
  - Font tab: $X \approx 200, Y \approx 1353$
  - Themes tab: $X \approx 423, Y \approx 1353$
  - Layout tab: $X \approx 640, Y \approx 1353$
  - More tab: $X \approx 870, Y \approx 1353$
- **Theme Preset Coordinates (Half-Height Mode)**:
  - Compact: $(540, 1680)$
  - Standard: $(540, 1860)$
  - Large: $(540, 2040)$

### Panel Screenshots (`settings_panels/`)
- `settings_00_panel.png` through `settings_11_panel.png`: Font size slider positions for all 12 Bookerly sizes.
- `settings_spacing_full.png`: Full expanded Font Spacing menu revealing all 4 sliders (Line, Paragraph, Word, Character).
- `settings_themes.png`: Themes preset selection menu.
- `settings_Compact_panel.png`: Compact preset active panel state.
- `settings_Large_panel.png`: Large preset active panel state.
