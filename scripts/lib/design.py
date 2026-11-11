"""Two-level design system: a required global file, optional per-product and session layers, one resolved result.

Layers (lowest → highest priority):
  global   design/global.json                  REQUIRED. The look every subject in the collection shares.
                                               A brief line "Design system: design/<other>.json" picks another file.
  product  assets/<job>/design.json            optional, user-owned (loose photo: assets/<stem>.design.json)
  session  output/<id>/design/session.json     optional, written by the agent from what the user asked for in
                                               the session or the brief's deliverables — never its own ideas

`resolve()` merges them with the fixed rules in RULES and writes output/<id>/design/design.resolved.json, with a
log of every override, every blocked override and every warning. Nothing here is a judgement call.
"""
from __future__ import annotations

import copy
import math
import re
from pathlib import Path

from . import paths, schema
from .paths import Product, die

DEFAULT_GENERATION = {"max_attempts": 3, "variations": 1}
DEFAULT_MOCKUP = {"name": "main", "type": "hero"}
ADDITIVE = ("must_avoid", "identity_constraints")
ASPECT_TOLERANCE = 0.01

RULES = [
    "R1 base: start from the global design system.",
    "R2 order: apply the product layer, then the session layer. A later layer wins field by field; objects "
    "(palette, typography, output) merge key by key, lists inside style are replaced whole.",
    "R3 locked: a path listed in global `locked` (or anything under it) keeps the global value; the attempted "
    "override is dropped and logged as blocked. Locks bind the product and session layers only.",
    "R4 additive: `must_avoid` and `identity_constraints` only grow. No layer can remove an entry.",
    "R5 mockups: the last layer that defines `mockups` replaces the list (unless `mockups` is locked). No layer "
    "defines any → one default mockup `main`. Each mockup's own `style` is applied last, under R3.",
    "R6 output: aspect and width/height must agree. A layer that changes only the aspect drops the inherited "
    "size; one that changes only the size re-derives the aspect, unless the aspect is locked (then the size "
    "change is blocked).",
    "R7 avoid wins: a style text that mentions a must_avoid term is reported as a warning; the planner must "
    "follow must_avoid.",
]


# ── files ────────────────────────────────────────────────────────────────────

def global_path(prod: Product) -> Path:
    m = re.search(r"^[ \t]*[-*]?[ \t]*Design system:[ \t]*(\S+)", paths.strip_comments(paths.brief_text(prod)), flags=re.M | re.I)
    return paths.p(m.group(1)) if m else paths.ROOT / "design" / "global.json"


def product_path(prod: Product) -> Path:
    if prod.asset_dir == paths.ASSETS.resolve() and prod.primary_image:  # loose single photo
        return prod.primary_image.with_suffix(".design.json")
    return prod.asset_dir / "design.json"


def session_path(prod: Product) -> Path:
    return prod.work / "design" / "session.json"


def resolved_path(prod: Product) -> Path:
    return prod.work / "design" / "design.resolved.json"


def layer_files(prod: Product) -> list[dict]:
    files = (("global", global_path(prod)), ("product", product_path(prod)), ("session", session_path(prod)))
    return [{"layer": name, "file": paths.rel(f), "present": f.exists(), "sha256": paths.sha256_file(f)} for name, f in files]


def _read_layer(path: Path, kind: str) -> dict | None:
    data = paths.read_json(path)
    if data is None:
        return None
    if kind == "layer" and isinstance(data, dict):
        forbidden = sorted({"locked", "name", "version"} & set(data))
        if forbidden:
            die(f"{paths.rel(path)}: only the global design system may set {forbidden}. Remove them here.")
    schema.check(data, f"design#{kind}", paths.rel(path))
    return data


# ── merge rules ──────────────────────────────────────────────────────────────

def is_locked(path: str, locked: list[str]) -> bool:
    return any(path == l or path.startswith(l + ".") for l in locked)


def _merge(base: dict, over: dict, prefix: str, layer: str, locked: list[str], log: list) -> dict:
    """R2 + R3: apply `over` onto `base`, key by key, skipping locked paths."""
    out = copy.deepcopy(base)
    for key, value in over.items():
        path = f"{prefix}.{key}"
        if is_locked(path, locked):
            if out.get(key) != value:
                log.append({"path": path, "layer": layer, "rule": "R3 locked", "applied": False,
                            "kept": out.get(key), "rejected": value})
        elif isinstance(value, dict):
            out[key] = _merge(out.get(key) if isinstance(out.get(key), dict) else {}, value, path, layer, locked, log)
        elif out.get(key) != value:
            log.append({"path": path, "layer": layer, "rule": "R2 override", "applied": True,
                        "from": out.get(key), "to": value})
            out[key] = copy.deepcopy(value)
    return out


def _union(base: list[str], extra: list[str], path: str, layer: str, log: list) -> list[str]:
    """R4: additive lists, de-duplicated case-insensitively, order kept."""
    out, seen = list(base), {b.strip().lower() for b in base}
    for item in extra or []:
        if item.strip().lower() not in seen:
            seen.add(item.strip().lower())
            out.append(item)
            log.append({"path": path, "layer": layer, "rule": "R4 additive", "applied": True, "added": item})
    return out


def _ratio(aspect: str) -> float:
    w, h = aspect.split(":")
    return float(w) / float(h)


def _aspect_of(width: int, height: int) -> str:
    g = math.gcd(width, height)
    return f"{width // g}:{height // g}"


def _consistent(output: dict) -> bool:
    if not (output.get("aspect") and output.get("width") and output.get("height")):
        return True
    return abs(output["width"] / output["height"] - _ratio(output["aspect"])) <= ASPECT_TOLERANCE * _ratio(output["aspect"])


def _reconcile_output(prev: dict, new: dict, layer: str, locked: list[str], log: list) -> dict:
    """R6: keep aspect and width/height in agreement after a layer changed one of them."""
    new = dict(new)
    changed = {k for k in ("aspect", "width", "height") if new.get(k) != prev.get(k)}
    if not changed or _consistent(new):
        return new
    if "aspect" in changed and not changed & {"width", "height"}:
        dropped = {k: new.pop(k) for k in ("width", "height") if k in new}
        log.append({"path": "style.output", "layer": layer, "rule": "R6 output", "applied": True,
                    "note": f"aspect changed to {new['aspect']}; inherited size {dropped} dropped"})
    elif "aspect" not in changed:
        if is_locked("style.output.aspect", locked):
            rejected = {k: new.get(k) for k in ("width", "height")}
            for k in ("width", "height"):
                new.pop(k, None)
                if k in prev:
                    new[k] = prev[k]
            log.append({"path": "style.output", "layer": layer, "rule": "R3 locked", "applied": False,
                        "kept": {k: prev.get(k) for k in ("aspect", "width", "height")}, "rejected": rejected,
                        "note": "size contradicts the locked aspect"})
        else:
            new["aspect"] = _aspect_of(new["width"], new["height"])
            log.append({"path": "style.output.aspect", "layer": layer, "rule": "R6 output", "applied": True,
                        "from": prev.get("aspect"), "to": new["aspect"], "note": "derived from the new size"})
    return new


def _apply_style(style: dict, over: dict | None, layer: str, locked: list[str], log: list) -> dict:
    if not over:
        return style
    merged = _merge(style, over, "style", layer, locked, log)
    merged["output"] = _reconcile_output(style.get("output", {}), merged.get("output", {}), layer, locked, log)
    return merged


def _check_output(output: dict, where: str) -> None:
    if not output.get("aspect") and not (output.get("width") and output.get("height")):
        die(f"{where}: style.output needs an `aspect` or both `width` and `height`.")
    if not _consistent(output):
        die(f"{where}: style.output {output['width']}x{output['height']} does not match aspect {output['aspect']}.")
    if not output.get("aspect"):
        output["aspect"] = _aspect_of(output["width"], output["height"])


_NEGATION = r"(?:no|not|non|never|without|avoid|free of|zero)\s+(?:[\w-]+\s+){0,2}"


def _avoid_warnings(mockup: dict) -> list[dict]:
    """R7: style texts that mention something the avoid list forbids."""
    def leaves(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                yield from leaves(v, f"{path}.{k}")
        elif isinstance(node, str):
            yield path, node.lower()

    out = []
    for entry in mockup["must_avoid"]:
        term = re.sub(r"^(?:no|avoid|never|without)\s+", "", entry.strip().lower())
        if len(term) < 3:
            continue
        for path, text in leaves(mockup["style"], "style"):
            hit = re.search(rf"\b{re.escape(term)}\b", text)
            if hit and not re.search(rf"\b{_NEGATION}{re.escape(term)}\b", text):
                out.append({"mockup": mockup["name"], "path": path, "term": entry, "rule": "R7 avoid wins",
                            "note": f"style text mentions '{term}', which must_avoid forbids — follow must_avoid"})
    return out


# ── resolve ──────────────────────────────────────────────────────────────────

def resolve(prod: Product) -> dict:
    gpath = global_path(prod)
    if not gpath.exists():
        die(f"no global design system: {paths.rel(gpath)} is required for every job. Copy "
            "design/global.example.json to design/global.json and edit it (or ask the user for one).")
    glob = _read_layer(gpath, "global")
    _check_output(glob["style"]["output"], paths.rel(gpath))
    layers = [("product", _read_layer(product_path(prod), "layer")), ("session", _read_layer(session_path(prod), "layer"))]

    locked = list(glob.get("locked", []))
    log: list[dict] = []
    style = copy.deepcopy(glob["style"])
    generation = {**DEFAULT_GENERATION, **glob.get("generation", {})}
    lists = {k: list(glob.get(k, [])) for k in ADDITIVE}
    mockups, mockup_layer = glob.get("mockups"), "global"

    for name, layer in layers:
        if not layer:
            continue
        style = _apply_style(style, layer.get("style"), name, locked, log)
        generation = _merge(generation, layer.get("generation", {}), "generation", name, locked, log)
        for k in ADDITIVE:
            lists[k] = _union(lists[k], layer.get(k), k, name, log)
        if layer.get("mockups"):
            if is_locked("mockups", locked):
                log.append({"path": "mockups", "layer": name, "rule": "R3 locked", "applied": False,
                            "kept": [m["name"] for m in mockups or [DEFAULT_MOCKUP]],
                            "rejected": [m["name"] for m in layer["mockups"]]})
            else:
                mockups, mockup_layer = layer["mockups"], name
                log.append({"path": "mockups", "layer": name, "rule": "R5 mockups", "applied": True,
                            "to": [m["name"] for m in mockups]})
    if not mockups:
        mockups, mockup_layer = [DEFAULT_MOCKUP], "default"
        log.append({"path": "mockups", "layer": "default", "rule": "R5 mockups", "applied": True, "to": ["main"]})

    names = [m["name"] for m in mockups]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        die(f"design ({mockup_layer} layer): duplicate mockup name(s) {dupes}.")

    resolved_mockups, warnings = [], []
    for m in mockups:
        who = f"{mockup_layer}:mockup:{m['name']}"
        m_style = _apply_style(style, m.get("style"), who, [] if mockup_layer == "global" else locked, log)
        _check_output(m_style["output"], f"mockup '{m['name']}'")
        rm = {
            "name": m["name"], "type": m.get("type", "hero"),
            "variations": m.get("variations", generation["variations"]),
            **{k: m[k] for k in ("purpose", "notes") if m.get(k)},
            "style": m_style,
            "must_avoid": _union(lists["must_avoid"], m.get("must_avoid"), f"mockups.{m['name']}.must_avoid", who, log),
        }
        warnings += _avoid_warnings(rm)
        resolved_mockups.append(rm)

    out = {
        "product_id": prod.id,
        "resolved_at": paths.now(),
        "name": glob["name"],
        "version": glob.get("version"),
        "layers": layer_files(prod),
        "rules": RULES,
        "style": style,
        "generation": generation,
        "must_avoid": lists["must_avoid"],
        "identity_constraints": lists["identity_constraints"],
        "locked": locked,
        "mockups": resolved_mockups,
        "resolution_log": log,
        "warnings": warnings,
    }
    schema.check(out, "design#resolved", "resolved design")
    previous = paths.read_json(resolved_path(prod))
    if previous and {**previous, "resolved_at": None} == {**out, "resolved_at": None}:
        return previous  # nothing changed: keep the file (and its hash) as is
    paths.write_json(resolved_path(prod), out)
    paths.record(prod, "design", mockups=len(resolved_mockups), overrides=sum(e["applied"] for e in log),
                 blocked=sum(not e["applied"] for e in log), warnings=len(warnings))
    return out


def stale_reason(prod: Product) -> str | None:
    """None when design.resolved.json matches the layer files on disk, else why it doesn't."""
    resolved = paths.read_json(resolved_path(prod))
    if not resolved:
        return "no design.resolved.json — run `studio.py design`"
    was = {l["layer"]: (l["file"], l["sha256"]) for l in resolved["layers"]}
    for l in layer_files(prod):
        if was.get(l["layer"]) != (l["file"], l["sha256"]):
            return f"the {l['layer']} design layer ({l['file']}) changed — run `studio.py design` again"
    return None


def load_resolved(prod: Product) -> dict:
    reason = stale_reason(prod)
    if reason:
        die(reason)
    return paths.read_json(resolved_path(prod))


def mockup(resolved: dict, shot: str) -> dict | None:
    return next((m for m in resolved["mockups"] if m["name"] == paths.slugify(shot)), None)
