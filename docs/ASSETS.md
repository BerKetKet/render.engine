# Third-Party & Amazon-Derived Assets Inventory (`docs/ASSETS.md`)

This inventory lists every third-party or Amazon-derived binary/media asset in the repository so the owner can decide repository visibility and what must never be redistributed publicly. (Full SHA-256 digests for all fonts and hyphenation files are in `DATA_PROVENANCE.md`.)

## 1. Proprietary / Amazon-Derived Fonts (`kindle_render/fonts/`) — **DO NOT PUBLISH PUBLICLY**
| Path | Size (bytes) | Origin & License |
| :--- | ---: | :--- |
| `kindle_render/fonts/Bookerly-Regular.ttf` | 275,188 | Dalton Maag Ltd (`2014`); proprietary EULA (no redistribution without written permission) |
| `kindle_render/fonts/Bookerly-RegularItalic.ttf` | 278,208 | Dalton Maag Ltd (`2014`); proprietary EULA |
| `kindle_render/fonts/Bookerly-Bold.ttf` | 278,376 | Dalton Maag Ltd (`2014`); proprietary EULA |
| `kindle_render/fonts/Bookerly-BoldItalic.ttf` | 290,500 | Dalton Maag Ltd (`2014`); proprietary EULA |
| `kindle_render/fonts/Bookerly-Display.ttf` | 105,428 | Amazon.com, Inc. (`2013–2017`); proprietary ("Modification or redistribution of this file requires prior written permission from Amazon.com, Inc.") |

## 2. Open-Source Third-Party Fonts (`kindle_render/fonts/`)
| Path | Size (bytes) | Origin & License |
| :--- | ---: | :--- |
| `kindle_render/fonts/DroidSansMono.ttf` | 108,128 | Ascender Corp / Google (`2007`); Apache License 2.0 |
| `kindle_render/fonts/NotoColorEmoji.ttf` | 2,767,876 | Google (`noto-emoji` v2.038); SIL OFL 1.1 |
| `kindle_render/fonts/NotoNaskhArabic-Regular.ttf` | 116,716 | Monotype / Google (`Noto` v1.08); SIL OFL 1.1 |
| `kindle_render/fonts/NotoSansCJK-Regular.otf` | 16,465,744 | Adobe / Google (`Noto` v2.004); SIL OFL 1.1 |
| `kindle_render/fonts/NotoSansDevanagari-Regular.ttf` | 200,804 | Monotype / Google (`Noto` v1.06); SIL OFL 1.1 |
| `kindle_render/fonts/NotoSansHebrew-Regular.ttf` | 17,352 | Monotype / Google (`Noto` v1.04); SIL OFL 1.1 |
| `kindle_render/fonts/NotoSansSymbols2-Regular.ttf` | 656,852 | Monotype / Google (`Noto` v2.003); SIL OFL 1.1 |
| `kindle_render/fonts/NotoSansThai-Regular.ttf` | 21,380 | Monotype / Google (`Noto` v1.04); SIL OFL 1.1 |
| `kindle_render/fonts/NotoSerifEthiopic-Regular.ttf` | 289,600 | Monotype / Google (`Noto` v2.000); SIL OFL 1.1 |

## 3. Compiled Binary Hyphenation Tables (`kindle_render/hyph_*.bin`) — **KEEP PRIVATE / REVIEW**
All 11 `.bin` files (`hyph_de.bin` 261,564 B, `hyph_deva.bin` 2,000 B, `hyph_en_YJ.bin` 384,048 B, `hyph_es.bin` 72,108 B, `hyph_fr.bin` 40,648 B, `hyph_gujr.bin` 1,316 B, `hyph_it.bin` 7,112 B, `hyph_mlym.bin` 1,468 B, `hyph_nl.bin` 232,704 B, `hyph_pt.bin` 4,712 B, `hyph_ru.bin` 182,188 B, `hyph_taml.bin` 2,008 B) have **unknown** embedded provenance/license (extracted from device runtime); do not publish publicly without verifying origin.

## 4. Text Hyphenation Dictionaries (`kindle_render/hyph_*.dic`)
- `kindle_render/hyph_de_DE.dic` (`1,094,183` B): TeX `dehyphn.tex` / OpenOffice (`LPPL` / `LGPL 2+`).
- `kindle_render/hyph_en_us.dic` (`106,457` B), `kindle_render/hyph_fr.dic` (`24,033` B): No embedded header (`unknown`).

## 5. Device Screenshots & Test Corpora (`exam/`) — **DO NOT PUBLISH PUBLICLY**
- `exam/v1/exam_v1_screenshots/` (`70` PNGs), `exam/v2/exam_v2_screenshots/` (`65` PNGs), `exam/v3/{size_00_Bookerly,size_04_Bookerly,theme_Compact,theme_Large}/` (`316` PNGs), `exam/tables_images_exam/{theme_Standard,theme_Compact,theme_Large}/` (`200+` PNGs including expanded table captures): Screenshots captured from Kindle for Android (`8.159.0.100`) containing rendered Bookerly glyphs and Kindle UI chrome. Keep private or distribute only via private release assets.
