"""Deterministic text / graphics overlay — the ONLY way text gets onto final images.

Image models garble typography and invent specs, so spec callouts, badges and copy are drawn here.
The layout is entirely up to the agent (spec JSON below); the only hard rules are:
  * "fact" elements must reference a fact whose status is "verified" in facts.verified.json
  * "copy" text must appear verbatim in the product brief (user-approved wording)
  * "image" elements (logos, badges) must be real files the client supplied

Spec format (coordinates are fractions of the canvas, 0..1):
{
  "base": "output/<id>/renders/hero/v1-1.png",
  "output": "output/<id>/renders/hero/v1-1-callouts.png",     # optional
  "canvas": {"width": 2048, "height": 2048, "fill": "#F4F1EC", "base_fit": "contain"},  # optional: resize/pad base
  "elements": [
    {"type": "rect",  "x": 0.0, "y": 0.86, "w": 1.0, "h": 0.14, "fill": "#000000AA", "radius": 0},
    {"type": "line",  "x1": 0.1, "y1": 0.5, "x2": 0.3, "y2": 0.5, "width": 3, "color": "#FFFFFF"},
    {"type": "text",  "fact": "height", "template": "{label}: {value}", "x": 0.05, "y": 0.9,
                      "size": 0.035, "color": "#FFFFFF", "font": "Helvetica", "anchor": "lm"},
    {"type": "text",  "copy": "Handcrafted in Portugal", "x": 0.95, "y": 0.9, "anchor": "rm", "size": 0.03},
    {"type": "image", "path": "assets/001-oak-chair/refs/logo.png", "x": 0.05, "y": 0.05, "w": 0.15}
  ]
}
Text options: size (fraction of canvas height), color, font (file path or font name), anchor (Pillow anchor,
default "la"), max_width (fraction → wraps), align, line_spacing, stroke_width, stroke_color, opacity, uppercase,
letter_spacing (px). Template fields: {label} {value} {unit} {variant} ({value} already includes the unit).
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont

from . import paths
from .factcheck import fmt_value, norm
from .paths import Product, die

FONT_DIRS = [
    paths.ROOT / "fonts",
    Path("/System/Library/Fonts"),
    Path("/System/Library/Fonts/Supplemental"),
    Path("/Library/Fonts"),
    Path.home() / "Library/Fonts",
    Path("/usr/share/fonts"),
    Path("C:/Windows/Fonts"),
]


def load_font(name: str | None, px: int):
    px = max(6, int(px))
    candidates = []
    if name:
        path = paths.p(name)
        if path.exists():
            candidates.append(path)
        stem = name.lower().replace(" ", "")
        for d in FONT_DIRS:
            if d.exists():
                for f in d.rglob("*"):
                    if f.suffix.lower() in (".ttf", ".otf", ".ttc") and f.stem.lower().replace(" ", "").replace("-", "") == stem.replace("-", ""):
                        candidates.append(f)
    candidates += [Path("/System/Library/Fonts/Helvetica.ttc"), Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
                   Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
    for c in candidates:
        try:
            return ImageFont.truetype(str(c), px)
        except OSError:
            continue
    return ImageFont.load_default(size=px)


def color(c: str | None, default="#000000", opacity: float | None = None) -> tuple:
    rgba = ImageColor.getrgb(c or default)
    if len(rgba) == 3:
        rgba = (*rgba, 255)
    if opacity is not None:
        rgba = (*rgba[:3], int(rgba[3] * opacity))
    return rgba


def _wrap(draw, text, font, max_px):
    out = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            trial = f"{line} {word}".strip()
            if line and draw.textlength(trial, font=font) > max_px:
                out.append(line)
                line = word
            else:
                line = trial
        out.append(line)
    return "\n".join(out)


def _fit_base(base: Image.Image, canvas: dict) -> Image.Image:
    W, H = int(canvas["width"]), int(canvas["height"])
    bg = Image.new("RGBA", (W, H), color(canvas.get("fill"), "#FFFFFF"))
    fit = canvas.get("base_fit", "contain")
    scale = (min if fit == "contain" else max)(W / base.width, H / base.height)
    img = base.resize((round(base.width * scale), round(base.height * scale)), Image.LANCZOS)
    if fit == "contain":
        bg.alpha_composite(img, ((W - img.width) // 2, (H - img.height) // 2))
    else:  # cover: fill the canvas, crop the overflow
        left, top = (img.width - W) // 2, (img.height - H) // 2
        bg.alpha_composite(img.crop((left, top, left + W, top + H)))
    return bg


def render_overlay(prod: Product, spec_path: Path) -> dict:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    verified = paths.read_json(prod.work / "factcheck" / "facts.verified.json")
    facts = {}
    if verified:
        for f in verified["facts"]:
            if f["status"] == "verified":
                facts.setdefault(f["key"], []).append(f)
    brief = norm(paths.strip_comments(paths.brief_text(prod)))

    base_path = paths.p(spec["base"])
    if not base_path.exists():
        die(f"base image not found: {spec['base']}")
    img = Image.open(base_path).convert("RGBA")
    if spec.get("canvas"):
        img = _fit_base(img, spec["canvas"])
    W, H = img.size
    used_facts, used_copy = [], []

    for n, el in enumerate(spec.get("elements", []), 1):
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        t = el.get("type", "text")
        if t == "rect":
            box = [el["x"] * W, el["y"] * H, (el["x"] + el["w"]) * W, (el["y"] + el["h"]) * H]
            d.rounded_rectangle(box, radius=int(el.get("radius", 0) * min(W, H)) if el.get("radius", 0) < 1 else int(el["radius"]),
                                fill=color(el.get("fill"), "#00000080", el.get("opacity")),
                                outline=color(el["outline"]) if el.get("outline") else None, width=int(el.get("outline_width", 0)))
        elif t == "line":
            d.line([el["x1"] * W, el["y1"] * H, el["x2"] * W, el["y2"] * H], fill=color(el.get("color"), "#000000", el.get("opacity")),
                   width=int(el.get("width", 2)))
        elif t == "image":
            src = paths.p(el["path"])
            if not src.exists():
                die(f"element {n}: image not found: {el['path']}")
            logo = Image.open(src).convert("RGBA")
            w = int(el["w"] * W)
            logo = logo.resize((w, round(logo.height * w / logo.width)), Image.LANCZOS)
            if el.get("opacity") is not None:
                logo.putalpha(logo.getchannel("A").point(lambda a: int(a * el["opacity"])))
            layer.alpha_composite(logo, (int(el["x"] * W), int(el["y"] * H)))
        elif t == "text":
            if "fact" in el:
                key = el["fact"]
                options = facts.get(key)
                if not options:
                    die(f"element {n}: fact '{key}' is not verified — only verified facts may be rendered. "
                        "Run fact-check / override first, or drop this element.")
                variant = el.get("variant")
                f = next((x for x in options if norm(x.get("variant") or "") == norm(variant or "")), None)
                if f is None:
                    die(f"element {n}: no verified '{key}' for variant {variant!r}")
                text = el.get("template", "{label}: {value}").format(
                    label=f.get("label") or key, value=fmt_value(f), unit=f.get("unit") or "", variant=f.get("variant") or "")
                used_facts.append({"key": key, "variant": f.get("variant"), "text": text})
            elif "copy" in el:
                text = el["copy"]
                if norm(text) not in brief:
                    die(f"element {n}: copy {text!r} is not in the product brief. Add it to the brief's "
                        "'Approved copy' section (user-approved wording) first.")
                used_copy.append(text)
            else:
                die(f"element {n}: text needs either 'fact' or 'copy'")
            if el.get("uppercase"):
                text = text.upper()
            font = load_font(el.get("font"), el.get("size", 0.035) * H)
            if el.get("max_width"):
                text = _wrap(d, text, font, el["max_width"] * W)
            xy = (el["x"] * W, el["y"] * H)
            kw = dict(font=font, fill=color(el.get("color"), "#111111", el.get("opacity")), anchor=el.get("anchor", "la"),
                      stroke_width=int(el.get("stroke_width", 0)), stroke_fill=color(el.get("stroke_color"), "#000000"))
            if "\n" in text:
                d.multiline_text(xy, text, align=el.get("align", "left"), spacing=int(el.get("line_spacing", 0.3) * font.size), **kw)
            elif el.get("letter_spacing"):
                ls = el["letter_spacing"]
                total = sum(d.textlength(ch, font=font) for ch in text) + ls * (len(text) - 1)
                h_anchor, v_anchor = kw["anchor"][0], kw["anchor"][1]
                x = xy[0] - {"l": 0, "m": total / 2, "r": total}.get(h_anchor, 0)
                kw["anchor"] = "l" + v_anchor
                for ch in text:
                    d.text((x, xy[1]), ch, **kw)
                    x += d.textlength(ch, font=font) + ls
            else:
                d.text(xy, text, **kw)
        else:
            die(f"element {n}: unknown type '{t}'")
        img.alpha_composite(layer)

    out = paths.p(spec["output"]) if spec.get("output") else base_path.with_name(base_path.stem + "-overlay.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out) if out.suffix.lower() in (".jpg", ".jpeg") else img.save(out)
    meta = {"base": paths.rel(base_path), "output": paths.rel(out), "spec": paths.rel(spec_path),
            "facts_rendered": used_facts, "copy_rendered": used_copy, "created_at": paths.now()}
    paths.write_json(out.with_suffix(".overlay.json"), meta)
    paths.record(prod, "overlay", output=paths.rel(out))
    return meta
