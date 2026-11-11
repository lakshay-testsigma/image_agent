"""QA helpers (inspect, contact sheet, verdict log) and export of approved assets.

An image is approved when the agent's three judgement gates pass AND the deterministic checks pass:
  planned_mockup    its shot is a mockup in the resolved design
  delivery_size     its pixels match the mockup's output (exact width x height, else the aspect)
  attempt_budget    it was not generated past the attempt budget
  subject_reference exact / likeness renders were generated with a subject photo attached
  overlay_facts     every fact drawn on it still equals the verified value
The approval is tied to the file's sha256: change the file and it must be reviewed again.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageStat

from . import factcheck, metadata, paths, renders
from .overlay import load_font
from .paths import Product, die

GATES = ("factual", "visual", "creative")
ASPECT_TOLERANCE = 0.01


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


def provenance(image: Path) -> tuple[dict | None, dict | None]:
    """(overlay sidecar or None, render log of the generation it came from or None)."""
    overlay_meta = paths.read_json(image.with_suffix(".overlay.json"))
    base = paths.p(overlay_meta["base"]) if overlay_meta else image
    return overlay_meta, renders.meta_for(base)


def _size_check(image: Path, output: dict) -> dict:
    with Image.open(image) as im:
        w, h = im.size
    if output.get("width") and output.get("height"):
        ok = (w, h) == (output["width"], output["height"])
        expected = f"{output['width']}x{output['height']}"
        fix = f"resize with an overlay `canvas` of {expected}"
    else:
        aw, ah = (float(x) for x in output["aspect"].split(":"))
        ok = abs(w / h - aw / ah) <= ASPECT_TOLERANCE * (aw / ah)
        expected = f"aspect {output['aspect']}"
        fix = f"crop/pad to {output['aspect']} with an overlay `canvas`"
    return {"ok": ok, "expected": expected, "actual": f"{w}x{h}", **({} if ok else {"fix": fix})}


def deterministic_checks(prod: Product, image: Path, meta: dict) -> dict:
    overlay_meta, render = provenance(image)
    mock = metadata.mockup(meta, image.parent.name)
    checks = {"planned_mockup": {"ok": bool(mock)}}
    if not mock:
        checks["planned_mockup"]["fix"] = f"'{image.parent.name}' is not in the resolved design's mockups"
        return checks
    checks["delivery_size"] = _size_check(image, mock["style"]["output"])
    if render is None:
        checks["attempt_budget"] = {"ok": False, "fix": "no render log — images must be logged with `register`"}
    else:
        checks["attempt_budget"] = {"ok": not render.get("over_budget"), "attempt": render.get("attempt"),
                                    "allowed": render.get("attempts_allowed")}
        if render.get("over_budget"):
            checks["attempt_budget"]["fix"] = "generated past the attempt budget without the user's go-ahead"
        problem = render.get("reference_problem")
        checks["subject_reference"] = {"ok": not problem, **({"fix": problem} if problem else {})}
    if overlay_meta and overlay_meta.get("facts_rendered"):
        current = {(f["key"], factcheck.norm(f.get("variant") or "")): factcheck.fmt_value(f)
                   for f in meta["attributes"]["verified"]}
        stale = [r["key"] for r in overlay_meta["facts_rendered"]
                 if current.get((r["key"], factcheck.norm(r.get("variant") or ""))) != r.get("value")]
        checks["overlay_facts"] = {"ok": not stale}
        if stale:
            checks["overlay_facts"]["fix"] = f"drawn facts no longer match verified values: {stale} — re-run `overlay`"
    return checks


def _load_qa(prod: Product) -> dict:
    return paths.read_json(prod.work / "qa" / "qa.json", {"product_id": prod.id, "renders": {}})


def is_approved(entry: dict | None, image: Path) -> bool:
    """Approved, and the file is still the one that was reviewed."""
    return bool(entry and entry.get("approved") and entry.get("sha256") == paths.sha256_file(image))


def qa_mark(prod: Product, image: Path, verdicts: dict, notes: str = "") -> dict:
    if not image.exists():
        die(f"image not found: {image}")
    meta = metadata.require_current(prod)
    overlay_meta, _ = provenance(image)
    if verdicts.get("factual") == "na" and overlay_meta and (overlay_meta.get("facts_rendered") or overlay_meta.get("copy_rendered")):
        die("--factual na is not allowed: this image has facts or copy drawn on it. Check them and give pass or fail.")
    checks = deterministic_checks(prod, image, meta)
    failed = [name for name, c in checks.items() if not c["ok"]]
    gates_ok = all(verdicts.get(g) in ("pass", "na") for g in GATES)
    entry = {g: verdicts[g] for g in GATES}
    entry.update(notes=notes, at=paths.now(), sha256=paths.sha256_file(image), checks=checks,
                 blocked_by=failed, approved=gates_ok and not failed)
    qa = _load_qa(prod)
    qa["renders"][paths.rel(image)] = entry
    paths.write_json(prod.work / "qa" / "qa.json", qa)
    paths.record(prod, "qa", reviewed=len(qa["renders"]), approved=sum(r["approved"] for r in qa["renders"].values()))

    b = renders.budget(prod, meta, image.parent.name) if checks["planned_mockup"]["ok"] else None
    if entry["approved"]:
        nxt = "approved"
    elif gates_ok:
        nxt = "gates passed but deterministic checks failed — fix: " + "; ".join(checks[n].get("fix", n) for n in failed)
    elif b and b["left"] > 0:
        nxt = f"retry: change one thing in the prompt and render again (attempt {b['used'] + 1} of {b['allowed']})"
    else:
        nxt = "escalate: attempt budget used up — report to the user instead of rendering again"
    return {**entry, "next": nxt}


def qa_set(prod: Product, consistency: str, notes: str = "") -> dict:
    """Set-level verdict: do the approved images work together (one design system, useful variation)?"""
    qa = _load_qa(prod)
    images = {k: v["sha256"] for k, v in qa["renders"].items() if is_approved(v, paths.p(k))}
    if not images:
        die("no approved images yet — mark single images with `qa-mark` first.")
    qa["set"] = {"consistency": consistency, "notes": notes, "at": paths.now(), "images": images}
    paths.write_json(prod.work / "qa" / "qa.json", qa)
    paths.record(prod, "qa-set", consistency=consistency, images=len(images))
    return qa["set"]


def _set_problem(qa: dict, images: list[Path]) -> str | None:
    if len(images) < 2:
        return None
    verdict = qa.get("set")
    if not verdict:
        return "no set-level verdict — review the approved images together and record it with `qa-set`"
    if verdict["consistency"] != "pass":
        return f"the set failed the consistency review ({verdict.get('notes') or 'no notes'})"
    missing = [paths.rel(i) for i in images if verdict["images"].get(paths.rel(i)) != paths.sha256_file(i)]
    if missing:
        return f"the set verdict does not cover {missing} (new or changed since `qa-set`) — run `qa-set` again"
    return None


def export(prod: Product, images: list[Path], description: str | None = None, force: bool = False,
           partial: bool = False) -> dict:
    meta = metadata.require_current(prod)
    qa = _load_qa(prod)
    entries = qa["renders"]
    if not images:
        images = [paths.p(k) for k, v in entries.items() if is_approved(v, paths.p(k))]
    if not images:
        die("nothing to export — no image is approved (three gates + deterministic checks; use `qa-mark`).")
    problems = []
    for img in images:
        entry = entries.get(paths.rel(img))
        if not is_approved(entry, img):
            why = "changed since it was reviewed" if entry and entry.get("approved") else "has not passed QA"
            problems.append(f"{paths.rel(img)} {why}")
    set_problem = _set_problem(qa, images)
    if set_problem:
        problems.append(set_problem)
    if problems and not force:
        die("export blocked:\n  - " + "\n  - ".join(problems) + "\n(--force exports anyway; only when the user asks.)")

    covered = {img.parent.name for img in images}
    missing_mockups = [m["name"] for m in meta["design"]["mockups"] if m["name"] not in covered]
    if missing_mockups and not (partial or force):
        die(f"planned mockups without an approved image: {', '.join(missing_mockups)}. Finish them, or export what "
            "exists with --partial (say so to the user).")

    final = prod.work / "final"
    final.mkdir(parents=True, exist_ok=True)
    out_images = []
    for i, img in enumerate(images, 1):
        shot = img.parent.name
        dst = final / f"{prod.id}-{shot}-{i:02d}{img.suffix.lower()}"
        shutil.copy2(img, dst)
        overlay_meta, render = provenance(img)
        render = render or {}
        out_images.append({
            "file": paths.rel(dst),
            "source_render": paths.rel(img),
            "sha256": paths.sha256_file(dst),
            "shot": shot,
            "mockup": metadata.mockup(meta, shot),
            "engine": render.get("engine"),
            "model": render.get("model"),
            "attempt": render.get("attempt"),
            "prompt": render.get("prompt"),
            "references": render.get("references"),
            "overlay": overlay_meta,
            "qa": entries.get(paths.rel(img)),
        })
    shutil.copy2(metadata.path(prod), final / "product.json")

    attrs = meta["attributes"]
    ident = meta["identification"]
    listing = {
        "product_id": prod.id,
        "status": "draft — awaiting client approval (never auto-published)",
        "exported_at": paths.now(),
        "forced": bool(problems), "qa_problems_overridden": problems,
        "missing_mockups": missing_mockups,
        "identity": {k: ident[k] for k in ("subject_type", "category", "name", "brand", "model", "identifiers")},
        "description": description,
        "facts": attrs["verified"],
        "excluded_unverified": sorted({f["key"] for k in ("unverified", "conflicting", "rejected") for f in attrs[k]}
                                      | set(attrs["unavailable"])),
        "sources": meta["research"]["sources"],
        "design_system": {"name": meta["design"]["name"], "version": meta["design"]["version"], "layers": meta["design"]["layers"]},
        "set_qa": qa.get("set"),
        "images": out_images,
        "metadata": paths.rel(final / "product.json"),
        "inputs": prod.to_dict(),
    }
    paths.write_json(final / "listing.json", listing)
    paths.record(prod, "export", images=len(out_images), forced=bool(problems), partial=bool(missing_mockups))
    return listing
