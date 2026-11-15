# Structured Text Layer Schema (`kindle_render` v1.7.0)

The structured text layer is emitted directly from the `PositionedDocument` / `PositionedPage` intermediate representation (`kindle_render/ir.py`) without recomputing layout or touching the rasterizer.

When invoked via `kindle_render text IN.epub OUT_DIR` or `kindle_render epub IN.epub OUT_DIR --text-layer`, the engine writes:
- **Per-page JSON files**: `OUT_DIR/page_001.json`, `OUT_DIR/page_002.json`, …
- **Document JSON file**: `OUT_DIR/document.json`

---

## 1. Per-Page JSON Schema (`page_NNN.json`)

```json
{
  "schema_version": "1.0",
  "ir_version": "1.0",
  "page_number": 1,
  "chapter": "x01_victorian",
  "width": 1080,
  "height": 2340,
  "glyph_command_count": 1412,
  "glyph_box_count": 1412,
  "logical_text": "X01 In which Mr. Hobday Is Disappointed by a Clock\n...",
  "links": [
    {
      "href": "x01_victorian.xhtml",
      "text": "X01 Victorian",
      "bbox": [211, 232, 463, 274]
    }
  ],
  "blocks": [
    {
      "reading_order": 0,
      "block_idx": 2,
      "chapter": "x01_victorian",
      "kind": "heading",
      "heading_level": 1,
      "list_level": 0,
      "list_marker": null,
      "table_caption": null,
      "table_rows": null,
      "bbox": [79, 175, 922, 316],
      "logical_text": "X01 In which Mr. Hobday Is Disappointed by a Clock",
      "lines": [
        {
          "line_idx": 14,
          "reading_order": 0,
          "baseline": 238,
          "bbox": [79, 175, 922, 250],
          "ends_with_synthetic_hyphen": false,
          "logical_text": "X01 In which Mr. Hobday Is",
          "words": [
            {
              "word_idx": 0,
              "logical_word_idx": 0,
              "reading_order": 0,
              "text": "X01",
              "direction": "ltr",
              "link_href": null,
              "bbox": [79, 178, 195, 238],
              "clusters": [
                {
                  "text": "X",
                  "glyph_name": "X",
                  "glyph_id": 59,
                  "font_id": "Bookerly-Display.ttf",
                  "size26": 5376,
                  "x": 79,
                  "baseline": 238,
                  "bbox": [79, 178, 123, 238],
                  "is_synthetic_hyphen": false,
                  "is_list_marker": false,
                  "is_drop_cap": false,
                  "is_ligature": false,
                  "direction": "ltr",
                  "logical_char_idx": 0,
                  "link_href": null
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### Field Guarantees & Invariants
1. **Strict 1-to-1 Glyph Box Correspondence**: Every `GlyphCommand` on a `PositionedPage` produces exactly one cluster entry in `blocks[*].lines[*].words[*].clusters[*]`, so `glyph_box_count == glyph_command_count` on every page.
2. **Page-Clamped Bounding Boxes**: Every cluster, word, line, block, and link `bbox` is a 4-element integer array `[x0, y0, x1, y1]` satisfying `0 <= x0 < x1 <= width` and `0 <= y0 < y1 <= height`.
3. **Logical Text & Copy Fidelity**:
   - Soft hyphens (`U+00AD`) removed during itemization and line-breaking hyphens (`is_synthetic_hyphen: true`) are excluded from `word.text`, `line.logical_text`, `block.logical_text`, and `page.logical_text`.
   - Words split across lines by hyphenation share or continue their `logical_word_idx` and re-join without inserting spurious spaces.
   - Standard and discretionary OpenType ligatures (`fi`, `fl`, `ff`, `ffi`, `ffl`, Arabic `lam_alef`) carry their expanded Unicode string in `cluster.text` with `is_ligature: true`.
   - Right-to-left (`direction: "rtl"`) words and clusters (`Arabic`, `Hebrew`) are ordered in **logical reading order** in `lines[*].words` and `words[*].clusters` while preserving their exact visual pixel bounding boxes.
4. **Structural Metadata**:
   - `kind`: `"paragraph" | "heading" | "list_item" | "pre" | "table" | "image"`
   - `heading_level`: `1..6` for headings (`0` otherwise)
   - `list_level` (`1..3`) and `list_marker` (e.g. `"•"`, `"◦"`, `"▪"`, `"1."`, `"a."`, `"i."`) for list items; list marker glyphs are flagged with `is_list_marker: true`.
   - `table_caption` and `table_rows` (2D grid of `{"text", "is_header", "align", "colspan", "rowspan"}`) on `"table"` blocks.
   - `link_href`: target URI on words/clusters inside `<a href="...">`, plus top-level `links` summary per page.

---

## 2. Document JSON Schema (`document.json`)

```json
{
  "schema_version": "1.0",
  "ir_version": "1.0",
  "engine_version": "1.7.0",
  "screen_w": 1080,
  "screen_h": 2340,
  "page_count": 65,
  "chapters": [
    {
      "chapter": "x01_victorian",
      "start_page": 3,
      "end_page": 4,
      "logical_text": "X01 In which Mr. Hobday Is Disappointed by a Clock\n..."
    }
  ],
  "pages": [
    /* Array of per-page JSON objects matching Section 1 */
  ]
}
```
