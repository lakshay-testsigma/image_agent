"""Product metadata: one validated JSON per subject, built from the earlier stages, read by every later one.

  output/<id>/metadata/product.json  =  intake.json  +  facts.verified.json (or a recorded skip)
                                        +  sources index  +  design.resolved.json

Every attribute carries a status, so nothing unverified can pass as fact:
  verified     passed fact-check; has its sources (or a recorded human decision)
  unverified   found, but only weak support (fact-check `needs_review`)
  conflicting  sources disagree
  rejected     did not survive fact-check
  inferred     seen in the photos at intake — a hint for generation, never a claim
  unavailable  required, but nothing usable was found

The file is validated against schemas/product.schema.json before it is written, and it records the hash of
each input. `require_current()` is the gate image generation, QA and export go through.
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

from . import design, intake, paths, schema, sources
from .paths import Product, die

SCHEMA_VERSION = "1.0"
TEXT_POLICY = ("The image tool draws no text, numbers, logos or UI. Only verified attributes and approved copy "
               "may appear, added with `studio.py overlay`.")
IDENTITY_KEYS = {"name": ("product_name", "title"), "brand": ("brand", "manufacturer"), "model": ("model_number", "model", "mpn")}


def path(prod: Product) -> Path:
    return prod.work / "metadata" / "product.json"


def _facts_path(prod: Product) -> Path:
    return prod.work / "factcheck" / "facts.verified.json"


def _input_hashes(prod: Product) -> dict:
    return {
        "intake": paths.sha256_file(intake.json_path(prod)),
        "facts_verified": paths.sha256_file(_facts_path(prod)),
        "design_resolved": paths.sha256_file(design.resolved_path(prod)),
        "reference_images": {paths.rel(i): paths.sha256_file(i) for i in [*prod.images, *prod.style_refs]},
    }


def _reference_images(prod: Product) -> list[dict]:
    out = []
    for img in [*prod.images, *prod.style_refs]:
        role = "primary" if img == prod.primary_image else "subject" if img in prod.images else "style_ref"
        with Image.open(img) as im:
            w, h = im.size
        out.append({"file": paths.rel(img), "role": role, "sha256": paths.sha256_file(img), "width": w, "height": h})
    return out


def _research(prod: Product, intake_data: dict) -> tuple[dict, dict | None]:
    """Returns (research block, facts.verified.json or None). Dies unless research is finished or skipped."""
    stages = paths.load_manifest(prod)["stages"]
    verified = paths.read_json(_facts_path(prod))
    idx = [{k: s.get(k) for k in ("id", "tier", "url", "title", "sha256", "retrieved_at")} for s in sources.load_index(prod)]
    if verified:
        return {"status": "done", "reason": None, "sources": idx, "verification": {
            "summary": verified["summary"], "extracted_by": verified.get("extracted_by"),
            "checked_by": verified.get("checked_by"), "independent_check": verified.get("independent_check"),
            "required": verified.get("required", []), "missing_required": verified.get("missing_required", []),
        }}, verified
    skipped = [stages.get(s, {}) for s in ("research", "factcheck")]
    if all(s.get("status") == "skipped" for s in skipped):
        needed = intake_data["facts_needed"]
        if needed["needed"]:
            die(f"intake says facts are needed ({', '.join(needed.get('keys', [])) or 'no keys listed'}) but research and "
                "fact-check were skipped. Run them, or correct intake.json and re-run `studio.py intake`.")
        return {"status": "skipped", "reason": skipped[0].get("reason"), "sources": idx, "verification": None}, None
    die("fact-check is not finished: no factcheck/facts.verified.json. Run product-research + product-factcheck, "
        "or record that no facts are needed with `studio.py skip` for both stages.")


def _fact(f: dict) -> dict:
    return {
        **{k: f.get(k) for k in ("key", "label", "variant", "value", "unit", "status", "basis")},
        "sources": [{k: e.get(k) for k in ("source_id", "tier", "url", "quote")} for e in f.get("evidence", [])],
    }


def _tokens(value) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(value).lower()))


def _attributes(verified: dict | None, intake_data: dict) -> tuple[dict, list[str]]:
    facts = verified["facts"] if verified else []
    by_status = {s: [f for f in facts if f["status"] == s] for s in ("verified", "needs_review", "conflict", "rejected")}
    v = intake_data["visual"]
    observed = {
        "shape": v.get("shape"), "construction": v.get("construction"), "material": v.get("materials"),
        "color": [c["name"] for c in v.get("colors", [])], "finish": v.get("finish"), "parts": v.get("parts"),
    }
    inferred = [{"key": k, "value": val, "basis": "photo observation at intake"} for k, val in observed.items() if val]

    warnings = []
    for obs in inferred:
        for f in by_status["verified"]:
            if f["key"] == obs["key"] and not _tokens(f["value"]) & _tokens(obs["value"]):
                warnings.append(f"verified {f['key']} {f['value']!r} shares no word with what the photos show "
                                f"({obs['value']!r}) — check the sources describe this exact subject/variant.")

    required = set(verified.get("required", []) if verified else []) | set(intake_data["facts_needed"].get("keys", []))
    found = {f["key"] for s in ("verified", "needs_review", "conflict") for f in by_status[s]}
    return {
        "verified": [_fact(f) for f in by_status["verified"]],
        "unverified": [_fact(f) for f in by_status["needs_review"]],
        "conflicting": [{"key": f["key"], "variant": f.get("variant"), "candidates": f["conflicts"]} for f in by_status["conflict"]],
        "rejected": [{"key": f["key"], "variant": f.get("variant"), "reason": f["basis"]} for f in by_status["rejected"]],
        "inferred": inferred,
        "unavailable": sorted(required - found),
    }, warnings


def _identification(intake_data: dict, attributes: dict) -> dict:
    ident, subject = intake_data["identity"], intake_data["subject"]
    verified = {f["key"]: f["value"] for f in attributes["verified"] if not f.get("variant")}

    def field(name: str) -> dict:
        for key in IDENTITY_KEYS[name]:
            if key in verified and isinstance(verified[key], (str, int, float)):
                return {"value": verified[key], "status": "verified"}
        return {"value": ident[name], "status": "inferred"} if ident.get(name) else {"value": None, "status": "unknown"}

    return {
        "subject_type": subject["type"], "category": subject["category"], "industry": subject.get("industry"),
        "name": field("name"), "brand": field("brand"), "model": field("model"),
        "identifiers": ident.get("identifiers", {}), "confidence": ident["confidence"], "basis": ident.get("basis"),
    }


def _traceability_errors(meta: dict) -> list[str]:
    """Checks a schema can't express: every verified attribute points at a saved source or a human decision."""
    errors = []
    known = {s["id"] for s in meta["research"]["sources"]}
    for f in meta["attributes"]["verified"]:
        if f["basis"].startswith("human override"):
            continue
        if not f["sources"]:
            errors.append(f"verified '{f['key']}' has no source")
        for s in f["sources"]:
            if s["source_id"] not in known:
                errors.append(f"verified '{f['key']}' cites unknown source {s['source_id']}")
    clash = {f["key"] for f in meta["attributes"]["verified"]} & set(meta["attributes"]["unavailable"])
    if clash:
        errors.append(f"keys both verified and unavailable: {sorted(clash)}")
    return errors


def build(prod: Product) -> dict:
    intake_data = intake.load(prod)
    people = intake_data["people"]
    if people["identifiable"] and people["consent"] != "confirmed":
        die("identifiable people without confirmed consent. Ask the user, set people.consent to 'confirmed' in "
            "intake.json and re-run `studio.py intake` — or stop.")
    resolved = design.load_resolved(prod)
    research, verified = _research(prod, intake_data)
    attributes, warnings = _attributes(verified, intake_data)
    warnings += [f"design: {w['note']} (mockup {w['mockup']}, {w['path']})" for w in resolved["warnings"]]
    if attributes["unavailable"]:
        warnings.append(f"required facts unavailable: {', '.join(attributes['unavailable'])} — they cannot appear on images or listings.")

    meta = {
        "schema_version": SCHEMA_VERSION,
        "product_id": prod.id,
        "generated_at": paths.now(),
        "identification": _identification(intake_data, attributes),
        "reference_images": _reference_images(prod),
        "attributes": attributes,
        "research": research,
        "visual": {**intake_data["visual"], "visible_text": intake_data.get("visible_text", [])},
        "generation_constraints": {
            "fidelity": intake_data["fidelity"]["mode"],
            "preservation_checklist": intake_data["preservation_checklist"],
            "identity_constraints": resolved["identity_constraints"],
            "must_avoid": resolved["must_avoid"],
            "compliance_cues": intake_data.get("compliance_cues", []),
            "text_policy": TEXT_POLICY,
        },
        "design": {k: resolved[k] for k in ("name", "version", "layers", "style", "generation", "must_avoid",
                                            "identity_constraints", "locked", "mockups", "resolution_log", "warnings")},
        "inputs_sha256": _input_hashes(prod),
        "warnings": warnings,
    }
    errors = schema.validate(meta, *schema.load("product")) + _traceability_errors(meta)
    if errors:
        die("product metadata failed validation — nothing written:\n  - " + "\n  - ".join(errors))
    paths.write_json(path(prod), meta)
    paths.record(prod, "metadata", verified=len(attributes["verified"]), unverified=len(attributes["unverified"]),
                 conflicting=len(attributes["conflicting"]), unavailable=len(attributes["unavailable"]),
                 mockups=len(resolved["mockups"]), warnings=len(warnings))
    return meta


def stale_reason(prod: Product) -> str | None:
    """None when product.json exists, is valid and matches its inputs on disk; else why not."""
    meta = paths.read_json(path(prod))
    if not meta:
        return "no metadata/product.json — run `studio.py design` then `studio.py metadata`"
    reason = design.stale_reason(prod)
    if reason:
        return reason
    now = _input_hashes(prod)
    for key, label in (("intake", "intake.json"), ("facts_verified", "factcheck/facts.verified.json"),
                       ("design_resolved", "design/design.resolved.json"), ("reference_images", "the subject photos / refs")):
        if meta["inputs_sha256"].get(key) != now[key]:
            return f"{label} changed since metadata was built — run `studio.py metadata` again"
    errors = schema.validate(meta, *schema.load("product"))
    if errors:
        return "metadata/product.json no longer matches its schema: " + "; ".join(errors[:3])
    return None


def require_current(prod: Product) -> dict:
    reason = stale_reason(prod)
    if reason:
        die(f"product metadata is not ready: {reason}")
    return paths.read_json(path(prod))


def mockup(meta: dict, shot: str) -> dict | None:
    return design.mockup(meta["design"], shot)
