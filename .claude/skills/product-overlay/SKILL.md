---
name: product-overlay
description: Stage 6 (optional) for ONE product — add text, spec callouts, badges, logos or layout panels onto a render deterministically, using only verified facts and user-approved copy. Use when a mockup needs dimensions, feature callouts, headlines, logos or any typography.
argument-hint: <product-image-path> [render path]
---

# Deterministic overlays (text, callouts, logos)

**Product:** `$ARGUMENTS`. The first token is the product image path, and an optional second token is the render to decorate. If you see the literal text `$ARGUMENTS`, take them from the user's message.

Image models garble lettering and invent numbers, so all added text is drawn here by Pillow, never by the image tool. You decide the layout freely: an infographic, a minimal corner caption, a dimension diagram, a story frame with a headline. Three guards apply:
- `fact` elements must reference a fact whose status is **verified** (`uv run scripts/studio.py facts <product-path>`)
- `copy` text must appear word-for-word in the brief (ideally under "Approved copy"). For new wording, ask the user to add it to the brief.
- `image` elements (logos, badges, certification marks) must be real files the client supplied, usually in `assets/<product>/refs/` or `brands/`

## 1. Write a spec: `output/<id>/creative/overlays/<shot>.json`

```json
{
  "base": "output/<id>/renders/catalog-white/v2-1.png",
  "output": "output/<id>/renders/catalog-white/v2-1-callouts.png",
  "canvas": {"width": 2048, "height": 2048, "fill": "#FFFFFF", "base_fit": "contain"},
  "elements": [
    {"type": "line", "x1": 0.80, "y1": 0.18, "x2": 0.80, "y2": 0.86, "width": 3, "color": "#111111"},
    {"type": "text", "fact": "height", "template": "{value}", "x": 0.82, "y": 0.52, "anchor": "lm",
     "size": 0.03, "color": "#111111", "font": "Helvetica"},
    {"type": "rect", "x": 0.0, "y": 0.90, "w": 1.0, "h": 0.10, "fill": "#111111E6"},
    {"type": "text", "copy": "Handcrafted in Portugal", "x": 0.5, "y": 0.95, "anchor": "mm",
     "size": 0.032, "color": "#FFFFFF", "uppercase": true, "letter_spacing": 4},
    {"type": "image", "path": "assets/<product>/refs/logo.png", "x": 0.04, "y": 0.04, "w": 0.14}
  ]
}
```
- Coordinates and sizes are fractions of the canvas (0–1). `size` is the text height as a fraction of canvas height.
- `canvas` is optional. It resizes or pads the base, for example to 2048² for marketplaces or 1080×1920 for stories.
- Text options: `font` (name or file; put brand fonts in `fonts/`), `anchor` (Pillow anchors: `la`, `mm`, `rs` …), `max_width` (wraps), `align`, `stroke_width`, `stroke_color`, `opacity`, `uppercase`, `letter_spacing`.
- Fact templates: `{label}`, `{value}` (already includes the unit), `{unit}`, `{variant}`. Add `"variant": "Black"` for variant-specific facts.
- Colours are hex, with `#RRGGBBAA` for transparency.

## 2. Render it

```bash
uv run scripts/studio.py overlay <product-path> --spec output/<id>/creative/overlays/catalog-white.json
```
This writes the image and a `.overlay.json` sidecar that lists exactly which facts and copy were drawn. QA and export use the sidecar.

## 3. Check it

Open the result. Look for legibility, contrast, nothing covering the product's key details, and safe margins for the channel (e.g. Instagram UI zones). Adjust the spec and re-run as often as needed; it's free and deterministic.

Leaving negative space for overlays is part of the creative plan. If a render has no calm area, use a `rect` panel or extend the canvas instead of covering the product.
