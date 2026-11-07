"""QA helpers (inspect, contact sheet, verdict log) and export of approved assets."""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageStat

from . import imagegen, paths
from .overlay import load_font
from .paths import Product, die

GATES = ("factual", "visual", "creative")


def inspect(path: Path) -> dict:
    img = Image.open(path)
    rgb = img.convert("RGB")
    small = rgb.copy()
    small.thumbnail((512, 512))
    edges = ImageStat.Stat(small.convert("L").filter(ImageFilter.FIND_EDGES))
    w, h = img.size
    return {
        "file": paths.rel(path),
        "width": w,
        "height": h,
        "aspect": f"{w / h:.3f}",
        "mode": img.mode,
        "has_alpha": "A" in img.getbands(),
        "kb": round(path.stat().st_size / 1024),
        "mean_rgb": [round(x) for x in ImageStat.Stat(rgb).mean],
        "sharpness": round(edges.var[0], 1),  # low (< ~50) suggests blur
    }


def contact_sheet(prod: Product, images: list[Path], out: Path, thumb: int = 512) -> Path:
    if not images:
        die("no images for the contact sheet")
    font = load_font(None, 18)
    cells = []
    for p in images:
        im = Image.open(p).convert("RGB")
        im.thumbnail((thumb, thumb))
        cell = Image.new("RGB", (thumb, thumb + 34), "white")
        cell.paste(im, ((thumb - im.width) // 2, (thumb - im.height) // 2))
        label = paths.rel(p).replace(paths.rel(prod.work) + "/", "")
        ImageDraw.Draw(cell).text((8, thumb + 8), label[-60:], fill="black", font=font)
        cells.append(cell)
    cols = min(4, len(cells))
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (thumb + 12) + 12, rows * (thumb + 46) + 12), "#DDDDDD")
    for i, c in enumerate(cells):
        sheet.paste(c, (12 + (i % cols) * (thumb + 12), 12 + (i // cols) * (thumb + 46)))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


def qa_mark(prod: Product, image: Path, verdicts: dict, notes: str = "") -> dict:
    if not image.exists():
        die(f"image not found: {image}")
    path = prod.work / "qa" / "qa.json"
    qa = paths.read_json(path, {"product_id": prod.id, "renders": {}})
    entry = {g: verdicts[g] for g in GATES if verdicts.get(g)}
    entry.update(notes=notes, at=paths.now())
    entry["approved"] = all(entry.get(g) in ("pass", "na") for g in GATES)
    qa["renders"][paths.rel(image)] = entry
    paths.write_json(path, qa)
    paths.record(prod, "qa", reviewed=len(qa["renders"]), approved=sum(r["approved"] for r in qa["renders"].values()))
    return entry


def export(prod: Product, images: list[Path], description: str | None = None, force: bool = False) -> dict:
    qa = paths.read_json(prod.work / "qa" / "qa.json", {"renders": {}})["renders"]
    if not images:
        images = [paths.p(k) for k, v in qa.items() if v.get("approved")]
    if not images:
        die("nothing to export — no image passed all three QA gates (use `qa-mark`).")
    for img in images:
        if not qa.get(paths.rel(img), {}).get("approved") and not force:
            die(f"{paths.rel(img)} has not passed all QA gates. Mark it with `qa-mark` (or pass --force with a reason).")

    verified = paths.read_json(prod.work / "factcheck" / "facts.verified.json") or {"facts": []}
    final = prod.work / "final"
    final.mkdir(parents=True, exist_ok=True)
    out_images = []
    for i, img in enumerate(images, 1):
        shot = img.parent.name
        dst = final / f"{prod.id}-{shot}-{i:02d}{img.suffix.lower()}"
        shutil.copy2(img, dst)
        base = img
        overlay_meta = paths.read_json(img.with_suffix(".overlay.json"))
        if overlay_meta:
            base = paths.p(overlay_meta["base"])
        meta = imagegen.meta_for(base) or {}
        out_images.append({
            "file": paths.rel(dst),
            "source_render": paths.rel(img),
            "shot": shot,
            "engine": meta.get("engine"),
            "model": meta.get("model"),
            "mode": meta.get("mode"),
            "prompt": meta.get("prompt"),
            "references": meta.get("references"),
            "overlay": overlay_meta,
            "qa": qa.get(paths.rel(img)),
        })

    facts = [f for f in verified["facts"] if f["status"] == "verified"]
    listing = {
        "product_id": prod.id,
        "status": "draft — awaiting client approval (never auto-published)",
        "exported_at": paths.now(),
        "identity": {k: next((f["value"] for f in facts if f["key"] == k), None)
                     for k in ("product_name", "brand", "model_number", "sku", "gtin", "category")},
        "description": description,
        "facts": [{k: f.get(k) for k in ("key", "label", "variant", "value", "unit", "basis")} for f in facts],
        "excluded_unverified": sorted({f["key"] for f in verified["facts"] if f["status"] != "verified"}),
        "images": out_images,
        "inputs": prod.to_dict(),
    }
    paths.write_json(final / "listing.json", listing)
    paths.record(prod, "export", images=len(out_images))
    return listing
