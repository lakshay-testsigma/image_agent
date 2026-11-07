"""OpenAI gpt-image rendering. The agent writes the prompt; this module only executes it and logs it.

mode=edit      (default) product photos are sent as reference images so the model keeps the real product
mode=generate  pure text-to-image (concept / background plates) — product identity NOT guaranteed
"""
from __future__ import annotations

import base64
import os
import re
import shutil
import sys
from contextlib import ExitStack
from pathlib import Path

from . import paths
from .paths import Product, die


def _next_version(shot_dir: Path) -> int:
    vs = [int(m.group(1)) for f in shot_dir.glob("v*-*.*") if (m := re.match(r"v(\d+)-", f.name))]
    return max(vs, default=0) + 1


def shot_slug(shot: str) -> str:
    return paths.slugify(shot)


def render(
    prod: Product,
    shot: str,
    prompt: str,
    refs: list[Path],
    *,
    mode: str = "edit",
    size: str | None = None,
    quality: str | None = None,
    n: int = 1,
    background: str | None = None,
    output_format: str = "png",
    fidelity: str | None = None,
    mask: Path | None = None,
    model: str | None = None,
    dry_run: bool = False,
) -> dict:
    model = model or os.getenv("IMAGE_MODEL", "gpt-image-1")
    size = size or os.getenv("IMAGE_SIZE", "1024x1024")
    quality = quality or os.getenv("IMAGE_QUALITY", "high")
    fidelity = fidelity if fidelity is not None else os.getenv("IMAGE_INPUT_FIDELITY", "high")
    if mode == "edit" and not refs:
        die("edit mode needs at least one reference image (product photo).")
    for r in refs:
        if not r.exists():
            die(f"reference image not found: {r}")

    shot_dir = prod.work / "renders" / shot_slug(shot)
    version = _next_version(shot_dir) if shot_dir.exists() else 1
    params: dict = {"model": model, "prompt": prompt, "n": n, "size": size, "quality": quality}
    if background:
        params["background"] = background
    if output_format:
        params["output_format"] = output_format

    meta = {
        "product_id": prod.id,
        "shot": shot,
        "version": version,
        "engine": "openai-images",
        "mode": mode,
        "model": model,
        "params": {k: v for k, v in params.items() if k != "prompt"} | ({"input_fidelity": fidelity} if mode == "edit" and fidelity else {}),
        "references": [paths.rel(r) for r in refs],
        "mask": paths.rel(mask) if mask else None,
        "prompt": prompt,
        "created_at": paths.now(),
    }
    if dry_run:
        meta["dry_run"] = True
        return meta

    from openai import BadRequestError, OpenAI

    if not os.getenv("OPENAI_API_KEY"):
        die("OPENAI_API_KEY is not set in .env (needed for image generation).")
    client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL") or None, timeout=float(os.getenv("IMAGE_TIMEOUT", "600")))
    print(f"[render] {shot} v{version}: {mode} · {model} · {size} · {quality} · n={n} · refs={len(refs)}", file=sys.stderr)

    with ExitStack() as stack:
        if mode == "edit":
            params["image"] = [stack.enter_context(open(r, "rb")) for r in refs]
            if mask:
                params["mask"] = stack.enter_context(open(mask, "rb"))
            if fidelity:
                params["input_fidelity"] = fidelity
            try:
                resp = client.images.edit(**params)
            except BadRequestError as e:
                if "input_fidelity" not in str(e):
                    raise
                print("[render] model rejected input_fidelity — retrying without it", file=sys.stderr)
                params.pop("input_fidelity")
                meta["params"].pop("input_fidelity", None)
                for f in params["image"]:
                    f.seek(0)
                resp = client.images.edit(**params)
        else:
            resp = client.images.generate(**params)

    shot_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for i, d in enumerate(resp.data, 1):
        out = shot_dir / f"v{version}-{i}.{output_format}"
        out.write_bytes(base64.b64decode(d.b64_json))
        files.append(paths.rel(out))
        if getattr(d, "revised_prompt", None):
            meta.setdefault("revised_prompts", []).append(d.revised_prompt)
    meta["files"] = files
    usage = getattr(resp, "usage", None)
    if usage is not None:
        meta["usage"] = usage.model_dump() if hasattr(usage, "model_dump") else str(usage)
    paths.write_json(shot_dir / f"v{version}.json", meta)
    paths.record(prod, f"render:{shot_slug(shot)}", version=version, files=len(files), model=model)
    return meta


def register(prod: Product, shot: str, image: Path, prompt: str, engine: str, refs: list[Path], model: str | None) -> dict:
    """Log an image produced by another engine (e.g. Codex built-in image_gen) into the same audit trail."""
    if not image.exists():
        die(f"image not found: {image}")
    shot_dir = prod.work / "renders" / shot_slug(shot)
    shot_dir.mkdir(parents=True, exist_ok=True)
    version = _next_version(shot_dir)
    out = shot_dir / f"v{version}-1{image.suffix.lower()}"
    shutil.copy2(image, out)
    meta = {
        "product_id": prod.id, "shot": shot, "version": version, "engine": engine, "mode": "external",
        "model": model, "references": [paths.rel(r) for r in refs], "prompt": prompt,
        "files": [paths.rel(out)], "created_at": paths.now(),
    }
    paths.write_json(shot_dir / f"v{version}.json", meta)
    paths.record(prod, f"render:{shot_slug(shot)}", version=version, files=1, engine=engine)
    return meta


def meta_for(render_path: Path) -> dict | None:
    m = re.match(r"(v\d+)-\d+", render_path.stem)
    if not m:
        return None
    return paths.read_json(render_path.parent / f"{m.group(1)}.json")
