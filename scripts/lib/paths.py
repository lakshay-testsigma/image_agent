"""Subject resolution, workspace layout, manifest + JSON helpers.

A "product" here means ANY subject an image job is about: a retail product, a dish, a person, a pet, a
property, a vehicle, an app screen, an artwork, a brand campaign ... It is resolved from ONE path:
  assets/001-oak-chair/01-front.jpg   -> folder assets/001-oak-chair/ (primary image = that file)
  assets/001-oak-chair/               -> same subject, primary image = first image in the folder
  assets/003-mug.jpg                  -> loose single-image subject (brief = assets/003-mug.md)
  001-oak-chair                       -> shorthand for assets/001-oak-chair/
  assets/004-launch-poster/           -> concept job: brief.md (+ optional refs/) but no subject photo

All generated work for that product lives in output/<product-id>/. Originals are never modified.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
OUTPUT = ROOT / "output"
PROMPTS = ROOT / "prompts"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
STYLE_REF_DIR = "refs"


def die(msg: str) -> None:
    raise SystemExit(f"error: {msg}")


def warn(msg: str) -> None:
    print(f"warning: {msg}", file=sys.stderr)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def p(arg: str | Path) -> Path:
    """Resolve a user-supplied path against cwd first, then the repo root."""
    path = Path(arg).expanduser()
    if path.is_absolute():
        return path.resolve()
    if (Path.cwd() / path).exists():
        return (Path.cwd() / path).resolve()
    return (ROOT / path).resolve()


def rel(path: Path | str) -> str:
    path = Path(path)
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def slugify(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", s.strip()).strip("-").lower()
    return s or "product"


def list_images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTS and not f.name.startswith(".")
    )


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


@dataclass
class Product:
    id: str
    asset_dir: Path
    primary_image: Path | None
    images: list[Path]
    style_refs: list[Path] = field(default_factory=list)
    brief: Path | None = None
    work: Path = OUTPUT

    @property
    def manifest_path(self) -> Path:
        return self.work / "manifest.json"

    def to_dict(self) -> dict:
        return {
            "product_id": self.id,
            "asset_dir": rel(self.asset_dir),
            "primary_image": rel(self.primary_image) if self.primary_image else None,
            "product_images": [rel(i) for i in self.images],
            "style_refs": [rel(i) for i in self.style_refs],
            "brief": rel(self.brief) if self.brief else None,
            "workspace": rel(self.work),
        }


def resolve(arg: str) -> Product:
    if not arg:
        die("a product image path is required, e.g. assets/001-oak-chair/01-front.jpg")
    path = p(arg)
    if not path.exists() and (ASSETS / arg).exists():
        path = (ASSETS / arg).resolve()
    if not path.exists():
        die(f"product path not found: {arg}")

    assets = ASSETS.resolve()
    key: str | None = None
    brief: Path
    style_refs: list[Path] = []

    if path.is_file():
        if path.suffix.lower() not in IMAGE_EXTS:
            die(f"not an image ({', '.join(sorted(IMAGE_EXTS))}): {arg}")
        if path.parent.name == STYLE_REF_DIR:
            die(f"{arg} is inside a '{STYLE_REF_DIR}/' folder (style/mood references). Pass the product image instead.")
        primary = path
        if path.parent == assets:
            asset_dir, images, key = assets, [path], path.stem
            brief = path.with_suffix(".md")
        else:
            asset_dir, images = path.parent, list_images(path.parent)
    else:
        if path == assets:
            die("pass ONE product (an image or its folder), not the whole assets/ folder.")
        if path.name.startswith("_"):
            die(f"{arg} is a template folder. Copy it to assets/NNN-product-name/ first.")
        asset_dir, images = path, list_images(path)
        if not images and not (path / "brief.md").exists():
            die(f"no subject images ({', '.join(sorted(IMAGE_EXTS))}) and no brief.md in {arg}")
        primary = images[0] if images else None  # None = concept job (brief + refs only)

    if key is None:
        try:
            key = "__".join(asset_dir.relative_to(assets).parts)
        except ValueError:
            key = asset_dir.name
        brief = asset_dir / "brief.md"
        style_refs = list_images(asset_dir / STYLE_REF_DIR)

    images = ([primary] if primary else []) + [i for i in images if i != primary]
    pid = slugify(key)
    return Product(
        id=pid,
        asset_dir=asset_dir,
        primary_image=primary,
        images=images,
        style_refs=style_refs,
        brief=brief if brief.exists() else None,
        work=OUTPUT / pid,
    )


# ── manifest: per-product state + audit trail ────────────────────────────────

def load_manifest(prod: Product) -> dict:
    m = read_json(prod.manifest_path)
    if m is None:
        m = {"product_id": prod.id, "created_at": now(), "inputs": prod.to_dict(), "stages": {}, "events": []}
    return m


def record(prod: Product, stage: str, status: str = "done", **data) -> None:
    m = load_manifest(prod)
    st = m["stages"].setdefault(stage, {})
    st.update(data)
    st["status"] = status
    st["updated_at"] = now()
    event = {"at": now(), "stage": stage, "status": status}
    event.update({k: v for k, v in data.items() if isinstance(v, (str, int, float, bool))})
    m["events"].append(event)
    write_json(prod.manifest_path, m)


# ── brief helpers ────────────────────────────────────────────────────────────

def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def brief_text(prod: Product) -> str:
    return prod.brief.read_text(encoding="utf-8") if prod.brief else ""


def brief_section(text: str, heading: str) -> str:
    """Body of the markdown section titled `heading` (exact match preferred, else prefix match), comments removed."""
    sections: list[tuple[str, list[str]]] = []
    for line in strip_comments(text).splitlines():
        m = re.match(r"^#{1,6}\s+(.*)$", line)
        if m:
            sections.append((m.group(1).strip().lower(), []))
        elif sections:
            sections[-1][1].append(line)
    h = heading.lower()
    for title, body in sections:
        if title == h:
            return "\n".join(body).strip()
    for title, body in sections:
        if title.startswith(h):
            return "\n".join(body).strip()
    return ""
