"""Intake record: the agent's structured observations of the subject, validated before anything builds on them.

The agent writes output/<id>/intake.json (shape: schemas/intake.schema.json). `studio.py intake` validates it,
adds the cross-checks a schema can't express, and renders intake.md for people to read. intake.json is the
source of truth; intake.md is only a view of it.
"""
from __future__ import annotations

from pathlib import Path

from . import paths, schema
from .paths import Product, die


def json_path(prod: Product) -> Path:
    return prod.work / "intake.json"


def _cross_checks(prod: Product, data: dict) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    mode = data["fidelity"]["mode"]
    if mode in ("exact", "likeness") and not prod.images:
        errors.append(f"fidelity '{mode}' needs subject photos, but this job has none (concept jobs use 'none').")
    if mode in ("exact", "likeness") and not data["preservation_checklist"]:
        errors.append(f"fidelity '{mode}' needs a preservation_checklist — QA checks renders against it.")
    if mode == "none" and prod.images:
        warnings.append("fidelity is 'none' but subject photos exist — they will not be used as references.")
    known = {i.name for i in prod.images}
    for ph in data.get("photos", []):
        if Path(ph["file"]).name not in known:
            errors.append(f"photos: '{ph['file']}' is not a subject photo of this job ({sorted(known) or 'none'}).")
    missing = sorted(known - {Path(ph["file"]).name for ph in data.get("photos", [])})
    if missing:
        warnings.append(f"subject photos not described in `photos`: {missing}")
    needed = data["facts_needed"]
    if needed["needed"] and not needed.get("keys"):
        warnings.append("facts_needed.needed is true but no keys are listed — name the facts that must be verified.")
    people = data["people"]
    if people["identifiable"] and people["consent"] != "confirmed":
        warnings.append("identifiable people without confirmed consent — ask the user; metadata is blocked until confirmed.")
    if not people["identifiable"] and people["consent"] == "not_confirmed":
        errors.append("people.consent is 'not_confirmed' but people.identifiable is false — use 'not_applicable'.")
    return errors, warnings


def store(prod: Product, source: Path | None = None) -> dict:
    """Validate the agent's intake JSON (from `source`, default output/<id>/intake.json) and render intake.md."""
    src = source or json_path(prod)
    data = paths.read_json(src)
    if data is None:
        die(f"no intake JSON at {paths.rel(src)} — write it first (shape: schemas/intake.schema.json).")
    schema.check(data, "intake", paths.rel(src))
    errors, warnings = _cross_checks(prod, data)
    if errors:
        die("intake is inconsistent:\n  - " + "\n  - ".join(errors))
    paths.write_json(json_path(prod), data)
    (prod.work / "intake.md").write_text(render_md(prod, data), encoding="utf-8")
    paths.record(prod, "intake", fidelity=data["fidelity"]["mode"], facts_needed=data["facts_needed"]["needed"],
                 warnings=len(warnings))
    return {"intake": paths.rel(json_path(prod)), "view": paths.rel(prod.work / "intake.md"), "warnings": warnings}


def load(prod: Product) -> dict:
    data = paths.read_json(json_path(prod))
    if data is None:
        die("no intake.json — run the product-intake skill (`studio.py intake`).")
    schema.check(data, "intake", paths.rel(json_path(prod)))
    errors, _ = _cross_checks(prod, data)
    if errors:
        die("intake is inconsistent:\n  - " + "\n  - ".join(errors))
    return data


def render_md(prod: Product, d: dict) -> str:
    def bullets(items, empty="-"):
        return [f"- {i}" for i in items] or [f"- {empty}"]

    s, i, v, f = d["subject"], d["identity"], d["visual"], d["facts_needed"]
    lines = [
        f"# Intake — {prod.id}",
        "",
        "_Generated from intake.json. Edit the JSON, then re-run `studio.py intake`._",
        "",
        "## Job",
        f"- Subject: {s['type']} · category: {s['category']} · industry: {s.get('industry') or '-'}",
        f"- Playbooks: {', '.join(s.get('playbooks', [])) or '-'}",
        f"- Fidelity: {d['fidelity']['mode']} (source: {d['fidelity']['source']})",
        f"- Facts needed: {'yes — ' + ', '.join(f.get('keys', [])) if f['needed'] else 'no'}"
        + (f" ({f['reason']})" if f.get("reason") else ""),
        f"- People: identifiable={d['people']['identifiable']}, consent={d['people']['consent']}",
        "",
        "## Identity hypothesis (not verified)",
        f"- Name: {i.get('name') or '-'} · brand: {i.get('brand') or '-'} · model: {i.get('model') or '-'}",
        f"- Identifiers: {', '.join(f'{k}={val}' for k, val in i.get('identifiers', {}).items()) or '-'}",
        f"- Confidence: {i['confidence']}" + (f" — {i['basis']}" if i.get("basis") else ""),
        "",
        "## Visible text (verbatim)",
        *bullets([f"\"{t['text']}\"" + (f" ({t['location']})" if t.get("location") else "") for t in d.get("visible_text", [])], "none"),
        "",
        "## Physical observations",
        f"- Shape: {v.get('shape') or '-'}",
        f"- Construction: {v.get('construction') or '-'}",
        f"- Materials: {', '.join(v.get('materials', [])) or '-'}",
        "- Colours: " + (", ".join(c["name"] + (f" {c['hex']}" if c.get("hex") else "") + (f" ({c['where']})" if c.get("where") else "")
                                   for c in v.get("colors", [])) or "-"),
        f"- Finish: {v.get('finish') or '-'}",
        f"- Parts: {', '.join(v.get('parts', [])) or '-'}",
        *[f"- {k}: {val}" for k, val in v.get("extra", {}).items()],
        "",
        "## Distinguishing features",
        *bullets(v.get("distinguishing_features", [])),
        "",
        "## Photo set",
        *bullets([f"{p['file']}: " + "; ".join(x for x in (p.get("angle"), p.get("background"), p.get("lighting"),
                                                           f"issues: {p['issues']}" if p.get("issues") else None) if x)
                  for p in d.get("photos", [])], "no subject photos (concept job)"),
        "",
        "## Preservation checklist",
        *bullets(d["preservation_checklist"]),
        "",
        "## Compliance cues",
        *bullets(d.get("compliance_cues", []), "none"),
        "",
        "## Research leads",
        *bullets(d.get("research_leads", []), "none"),
    ]
    direction = d.get("direction") or {}
    if direction:
        lines += ["", "## From the brief", f"- Direction: {direction.get('summary') or '-'}",
                  *[f"- Deliverable: {x}" for x in direction.get("deliverables", [])],
                  *[f"- Constraint: {x}" for x in direction.get("constraints", [])]]
    if d.get("notes"):
        lines += ["", "## Notes", d["notes"]]
    return "\n".join(lines) + "\n"
