---
name: product-overlay
description: Stage 6 (optional) for ONE subject — deterministically add text (headlines, CTAs, spec callouts, prices, disclaimers), logos and badges, composite real assets (app screenshots, artwork, labels) in perspective onto screens/signs/walls/packaging, and resize to channel sizes, using only verified facts and approved copy. Use when an image needs typography, a poster/ad/thumbnail layout, a screen or label replacement, or an exact delivery size.
argument-hint: <subject-image-path> [render path]
---

# Deterministic overlays & composites

**Subject:** `$ARGUMENTS`. The first token is the subject image path, and an optional second token is the render to decorate. If you see the literal text `$ARGUMENTS`, take them from the user's message.

Image models garble lettering and invent numbers, so all added text is drawn here by Pillow, never by the image tool. Exact assets (logos, real app/website screenshots, artwork, label art, QR codes) are composited here too, never redrawn by the image tool. You decide the layout freely: an infographic, a minimal corner caption, a dimension diagram, a story frame with a headline, a poster, an ad with CTA and disclaimer, a YouTube thumbnail, a menu tile, a device mockup with the real UI. Three guards apply:
- `fact` elements must reference a fact whose status is **verified** (`uv run scripts/studio.py facts <path>`)
- `copy` text must appear word-for-word in the brief (ideally under "Approved copy"). For new wording, ask the user to add it to the brief.
- `image` elements (logos, badges, certification marks, screenshots, artwork) must be real files the client supplied, usually in `assets/<job>/`, `assets/<job>/refs/` or `brands/`

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
- Image placement: `x, y, w` (height follows aspect), or `x, y, w, h` + `"fit": "contain" | "cover" | "stretch"`, or `"corners": [[x,y] TL, TR, BR, BL]` to warp it in perspective onto a screen, billboard, wall frame, book cover or label (ask the image tool for a plain blank area there). Also `radius` (rounded screen corners) and `opacity`.
- Coordinates and sizes are fractions of the canvas (0–1). `size` is the text height as a fraction of canvas height.
- `canvas` is optional. It resizes the base to the delivery size: `base_fit: contain` pads with `fill`, `cover` crops to fill (see `../product-creative/formats.md`). One spec per channel gives you every crop of a master image.
- Text options: `font` (name or file; put brand fonts in `fonts/`), `anchor` (Pillow anchors: `la`, `mm`, `rs` …), `max_width` (wraps), `align`, `stroke_width`, `stroke_color`, `opacity`, `uppercase`, `letter_spacing`.
- Fact templates: `{label}`, `{value}` (already includes the unit), `{unit}`, `{variant}`. Add `"variant": "Black"` for variant-specific facts.
- Colours are hex, with `#RRGGBBAA` for transparency.

## 2. Render it

```bash
uv run scripts/studio.py overlay <path> --spec output/<id>/creative/overlays/catalog-white.json
```
This writes the image and a `.overlay.json` sidecar that lists exactly which facts and copy were drawn. QA and export use the sidecar.

## 3. Check it

Open the result. Look for legibility, contrast, nothing covering the subject's key details, composites sitting flush in perspective, and safe margins for the channel (e.g. Instagram / TikTok UI zones). Adjust the spec and re-run as often as needed; it's free and deterministic.

Leaving negative space for overlays is part of the creative plan. If a render has no calm area, use a `rect` panel or extend the canvas instead of covering the subject.
