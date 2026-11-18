# Repository Weight & Branch Report (`docs/repo_weight.md`)

## 1. Local `.git` Size & 20 Largest Tracked Paths
- **Local sandbox `.git` size**: `25M` (`25 MiB`, shallow/packed snapshot without `exam/` history; owner reports remote `.git` is `~955 MB` and `exam/` is `~548 MB`).
- **20 largest tracked paths in the current checkout (`git ls-files`)**:
  1. `16,465,744 B` — `kindle_render/fonts/NotoSansCJK-Regular.otf`
  2. `2,767,876 B` — `kindle_render/fonts/NotoColorEmoji.ttf`
  3. `1,094,183 B` — `kindle_render/hyph_de_DE.dic`
  4. `656,852 B` — `kindle_render/fonts/NotoSansSymbols2-Regular.ttf`
  5. `595,142 B` — `tools/reports/rhythm/gaps_probe.json`
  6. `384,048 B` — `kindle_render/hyph_en_YJ.bin`
  7. `322,630 B` — `tools/reports/rhythm/gaps_exam3_normal.json`
  8. `303,188 B` — `tools/reports/rhythm/gaps_exam3_small.json`
  9. `290,500 B` — `kindle_render/fonts/Bookerly-BoldItalic.ttf`
  10. `289,600 B` — `kindle_render/fonts/NotoSerifEthiopic-Regular.ttf`
  11. `278,376 B` — `kindle_render/fonts/Bookerly-Bold.ttf`
  12. `278,208 B` — `kindle_render/fonts/Bookerly-RegularItalic.ttf`
  13. `275,188 B` — `kindle_render/fonts/Bookerly-Regular.ttf`
  14. `266,587 B` — `tools/reports/round1/synthetic_after/page_03.png`
  15. `261,564 B` — `kindle_render/hyph_de.bin`
  16. `247,304 B` — `tools/reports/round1/synthetic_before/page_04.png`
  17. `235,255 B` — `tools/reports/round1/item_01/exam2_page_08_after.png`
  18. `233,902 B` — `tools/reports/round1/synthetic_before/page_03.png`
  19. `232,704 B` — `kindle_render/hyph_nl.bin`
  20. `217,879 B` — `tools/reports/synthetic/page_03.png`

## 2. Options for Shrinking Clone Size (No History Rewrite Performed)
| Option | Clone Bandwidth / Disk Impact | Trade-Offs |
| :--- | :--- | :--- |
| **Partial clone (`git clone --filter=blob:none`)** | Downloads only blobs needed for `HEAD`; skips historical `exam/` and report PNGs (`~500+ MB` saved) without rewriting git history. | Requires network access to fetch historical blobs on `git log -p` / `git checkout` of old commits. |
| **Git LFS (`exam/**/*.png`, `*.epub`, `*.otf`, `*.ttf`)** | Keeps `HEAD` fast and thin for code-only contributors (`git lfs pull` optional). | Requires `git-lfs` installed and GitHub LFS storage quota; migrating existing blobs requires history rewrite (`git filter-repo`). |
| **Move `exam/` captures to a GitHub Release asset** | Drops `~548 MB` of screenshots out of git completely; `tools/run_gates.py` can still run unit + golden hash gates without captures, or fetch/unpack `exam.tar.zst` on demand. | Captures are no longer versioned atomically with git commits; requires a one-time `filter-repo` if removing from history. |

**Recommendation**: Use `git clone --filter=blob:none` immediately (zero risk, zero history rewrite), and for the Rust port repository keep `exam/` out of git (attach as a private release asset) while keeping `tools/golden/*.json` in git.

## 3. Remote `engine` Branch
- **Status on sandbox VM**: No `git remote` is configured and only `main` exists locally (`git branch -a` -> `* main`), so the remote `engine` branch could not be inspected here. Run `git log -1 origin/engine` and `git diff --stat main...origin/engine` on a connected clone to verify whether `engine` is an obsolete pre-refactor branch before deleting.
