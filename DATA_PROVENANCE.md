# DATA_PROVENANCE.md — Bundled Font & Hyphenation Data Files

This document lists every bundled font (`kindle_render/fonts/*`) and hyphenation data file (`kindle_render/hyph_*.bin`, `kindle_render/hyph_*.dic`) in `kindle_render` v1.6.1, with its verified SHA-256 digest, byte size, and strictly established origin and licence metadata read from embedded file headers/tables. Where origin or licence metadata is not embedded in the file itself, it is recorded as `unknown`.

---

## 1. Font Files (`kindle_render/fonts/*`)

| File Path | Size (bytes) | SHA-256 | Established Origin (from OpenType `name` table) | Established Licence (from OpenType `name` table) |
|---|---:|---|---|---|
| `kindle_render/fonts/Bookerly-Bold.ttf` | 278,376 | `c151ccad313fbefe0e733510fbc1b8d937748a4f4d20b0eed5236192acb7547c` | Bookerly Bold Version 1.000; Manufacturer/Designer: Dalton Maag Ltd (`http://www.daltonmaag.com/`) | Proprietary ("Copyright 2014 Dalton Maag Ltd. Modification of this file requires prior written permission from Dalton Maag Ltd."; `http://www.daltonmaag.com/eula`) |
| `kindle_render/fonts/Bookerly-BoldItalic.ttf` | 290,500 | `d9379d485cd9bf3f8c6ef453fe4c114a744e27c7c08190f172c1846734a741b5` | Bookerly Bold Italic Version 1.000; Manufacturer/Designer: Dalton Maag Ltd (`http://www.daltonmaag.com/`) | Proprietary ("Copyright 2014 Dalton Maag Ltd. Modification of this file requires prior written permission from Dalton Maag Ltd."; `http://www.daltonmaag.com/eula`) |
| `kindle_render/fonts/Bookerly-Display.ttf` | 105,428 | `9a6d2941bd2c722106b5fab1ee63430bdf1631a37aaae97d4665904358b3fbca` | Bookerly Display Regular Version 1.001; Manufacturer: Amazon.com, Inc (`http://www.daltonmaag.com/`) | Proprietary ("Copyright 2013-2017, Amazon.com, Inc. or its affiliates. Modification or redistribution of this file requires prior written permission from Amazon.com, Inc."; `http://www.daltonmaag.com/eula`) |
| `kindle_render/fonts/Bookerly-Regular.ttf` | 275,188 | `262d5bc642d2fc710bfffe1aa2664983ed9c478108a0cfb7d57672090feffde7` | Bookerly Regular Version 1.000; Manufacturer/Designer: Dalton Maag Ltd (`http://www.daltonmaag.com/`) | Proprietary ("Copyright 2014 Dalton Maag Ltd. Modification of this file requires prior written permission from Dalton Maag Ltd."; `http://www.daltonmaag.com/eula`) |
| `kindle_render/fonts/Bookerly-RegularItalic.ttf` | 278,208 | `bdff5401a92c061f731dda69fb214a7be3a756f7f0ffd8cfbc1a7bcdabf7a417` | Bookerly Italic Version 1.000; Manufacturer/Designer: Dalton Maag Ltd (`http://www.daltonmaag.com/`) | Proprietary ("Copyright 2014 Dalton Maag Ltd. Modification of this file requires prior written permission from Dalton Maag Ltd."; `http://www.daltonmaag.com/eula`) |
| `kindle_render/fonts/DroidSansMono.ttf` | 108,128 | `db19a1fdaba41cc4a2fec0330e5c15e71c6dd68a3ef074f4f28268828b45c862` | Droid Sans Mono Regular Version 1.00 build 113; Manufacturer: Ascender Corporation (`http://www.ascendercorp.com/`); Copyright 2007 Google Corporation | Apache License, Version 2.0 (`http://www.apache.org/licenses/LICENSE-2.0`) |
| `kindle_render/fonts/NotoColorEmoji.ttf` | 2,767,876 | `83914c48dc1bb7ff27cd06a3728d2f997dbcdc15cdc81b7deb21079c6d36e108` | Noto Color Emoji Regular Version 2.038 (`GOOG;noto-emoji:20220906:4b1c5bfb0d5b1f5c69aa321d5b6e70656ead1d30`); Google, Inc. (`https://github.com/googlefonts/noto-emoji`) | SIL Open Font License, Version 1.1 (`http://scripts.sil.org/OFL`) |
| `kindle_render/fonts/NotoNaskhArabic-Regular.ttf` | 116,716 | `4a23dc5dea7f846fb274f7ebb256d25063bc432e2cb810fc9eeb964a3d7ae217` | Noto Naskh Arabic Regular Version 1.08 uh; Monotype Imaging Inc. / Google Inc. (`http://www.google.com/get/noto/`) | SIL Open Font License, Version 1.1 (`http://scripts.sil.org/OFL`) |
| `kindle_render/fonts/NotoSansCJK-Regular.otf` | 16,465,744 | `a57e8161e38bd46c4b77a151fc8c9508f94838b6288ee8460a1bf04fbcdacb61` | Noto Sans CJK JP Regular Version 2.004; Adobe / Google Inc. (`http://www.google.com/get/noto/`) | SIL Open Font License, Version 1.1 (`http://scripts.sil.org/OFL`) |
| `kindle_render/fonts/NotoSansDevanagari-Regular.ttf` | 200,804 | `3b52bdbb58647090b1493dc2412f7654e4a2f3c56dc219615fa6c8b536d9e77c` | Noto Sans Devanagari Regular Version 1.06; Monotype Imaging Inc. / Google Inc. (`http://www.google.com/get/noto/`) | SIL Open Font License, Version 1.1 (`http://scripts.sil.org/OFL`) |
| `kindle_render/fonts/NotoSansHebrew-Regular.ttf` | 17,352 | `ef877e0e136f7942900b7ec8c866c180562d45def425b8bfe2dc0a992e3c2fd7` | Noto Sans Hebrew Regular Version 1.04 uh; Monotype Imaging Inc. / Google Inc. (`http://www.google.com/get/noto/`) | SIL Open Font License, Version 1.1 (`http://scripts.sil.org/OFL`) |
| `kindle_render/fonts/NotoSansSymbols2-Regular.ttf` | 656,852 | `876598db5f1e3bef2bc77c4d94c5b0d5d2c1620be4878a06f18fb5434e331688` | Noto Sans Symbols2 Regular Version 2.003; Monotype Imaging Inc. / Google Inc. (`http://www.google.com/get/noto/`) | SIL Open Font License, Version 1.1 (`http://scripts.sil.org/OFL`) |
| `kindle_render/fonts/NotoSansThai-Regular.ttf` | 21,380 | `0dc4e81ac4fe236db1a1d8a9cdb28971b9c136de08f2e6328e365e11c76410de` | Noto Sans Thai Regular Version 1.04 uh; Monotype Imaging Inc. / Google Inc. (`http://www.google.com/get/noto/`) | SIL Open Font License, Version 1.1 (`http://scripts.sil.org/OFL`) |
| `kindle_render/fonts/NotoSerifEthiopic-Regular.ttf` | 289,600 | `30bd9e21c81cd95a3004bbf75aba9b2ab5f861408a3fbb4f82b10fe82072952b` | Noto Serif Ethiopic Regular Version 2.000; Monotype Imaging Inc. / Google Inc. (`http://www.google.com/get/noto/`) | SIL Open Font License, Version 1.1 (`http://scripts.sil.org/OFL`) |

---

## 2. Hyphenation Dictionary Files (`kindle_render/hyph_*.dic`)

| File Path | Size (bytes) | SHA-256 | Established Origin | Established Licence |
|---|---:|---|---|---|
| `kindle_render/hyph_de_DE.dic` | 1,094,183 | `8f5017f08b9b943779b86a3afcdfb7c77f3a6f566525f90f60d4073e8b7dbced` | Embedded header: German (`de_DE`) dictionary Version 2017-01-12 based on TeX hyphenation tables `dehyphn.tex` (revision level 31, `http://www.ctan.org/tex-archive/language/hyphenation/dehyphn.tex`), converted/improved by Marco Huggenberger, Daniel Naber, and Karl Zeiler | Embedded header: LaTeX Project Public License (LPPL) for `dehyphn.tex`; GNU Lesser General Public License (LGPL 2 or later) for OpenOffice.org adaptions |
| `kindle_render/hyph_en_us.dic` | 106,457 | `cb76034d0a48f4eeda6315e5991671e49ba874300864ebb2bf4b768c8bbfbb0c` | unknown (no copyright/origin comment header present in file) | unknown (no licence header present in file) |
| `kindle_render/hyph_fr.dic` | 24,033 | `fedf8813d594f0ea04a94a1d7e0ea2c6845a476f7296b6840cdf3b0ad3fe4605` | unknown (no copyright/origin comment header present in file) | unknown (no licence header present in file) |

---

## 3. Compiled Binary Hyphenation Files (`kindle_render/hyph_*.bin`)

| File Path | Size (bytes) | SHA-256 | Established Origin | Established Licence |
|---|---:|---|---|---|
| `kindle_render/hyph_de.bin` | 261,564 | `6ca1a9492da1380c4a43120b66b4553fb4b76362f4955d5de58e10f77982f678` | unknown | unknown |
| `kindle_render/hyph_deva.bin` | 2,000 | `65534f81c408f0a0529384245516a2d7e1a9e9b7cba062b20f4ac01216723f87` | unknown | unknown |
| `kindle_render/hyph_en_YJ.bin` | 384,048 | `c6b35e08fe6023de9f39be3360926db5cc56befefef22c9319424f2e1d9e727e` | unknown | unknown |
| `kindle_render/hyph_es.bin` | 72,108 | `39c7b3c2b3e7fee1a58e8aa64946189680ba9b1614a4ee9ef6e3d0d85b5b30b0` | unknown | unknown |
| `kindle_render/hyph_fr.bin` | 40,648 | `cc9c6d53102df854ed60b13a1e841ad4eb6343067ef423403cc07eec2af54101` | unknown | unknown |
| `kindle_render/hyph_gujr.bin` | 1,316 | `46490fc8601d94931ede34b10ae9c0951dd1cc6acd2f9fb1681b8f81811b79b7` | unknown | unknown |
| `kindle_render/hyph_it.bin` | 7,112 | `dd5d9ded50d36db3b579716f7fa15e81c859fb20edd65312eaed1220423e4592` | unknown | unknown |
| `kindle_render/hyph_mlym.bin` | 1,468 | `1a34386778ab3ca93bc0d54aa181709c65f1f88afa0afa2db8ab9a3b341e4b47` | unknown | unknown |
| `kindle_render/hyph_nl.bin` | 232,704 | `3e4a5a63b06b3b590cc7b83afa29faf984b57eb25a1b22edd678778755df0bb0` | unknown | unknown |
| `kindle_render/hyph_pt.bin` | 4,712 | `d70bdcda457a64af44f759dce4f3a0452aea7e2c3f0efd086043f90490a041b4` | unknown | unknown |
| `kindle_render/hyph_ru.bin` | 182,188 | `7d9fc756255abbcc3d6cd508eca76a3b9b18f31c2bb0d0a1a10b02072c4ec784` | unknown | unknown |
| `kindle_render/hyph_taml.bin` | 2,008 | `d7e876b9f1e14bbd8f8872ea67ce77645e8adcddba6f0dc691ea4b52b156daee` | unknown | unknown |
