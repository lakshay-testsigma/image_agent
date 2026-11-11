"""Research extractions: product facts (with verbatim quotes) pulled from each saved source.

The harness agent (Claude Code / OpenCode / Codex) reads one saved source text at a time, follows
prompts/research-extract.md, and writes a JSON extraction. `studio.py extract --source S1 --input x.json`
stores it here (validated, tied to the source's content hash); `studio.py extract` merges every stored
extraction into research/facts.draft.json. No model is called from these scripts.
"""
from __future__ import annotations

import re

from . import paths, sources
from .paths import Product, die

MATCH_VALUES = ("yes", "likely", "unclear", "no")


def _key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


def _clean_fact(f: dict, sid: str) -> dict | None:
    if not isinstance(f, dict):
        return None
    key = _key(f.get("key") or f.get("label") or "")
    value = f.get("value")
    if not key or value is None or (isinstance(value, str) and not value.strip()):
        return None
    return {
        "key": key,
        "label": (f.get("label") or key.replace("_", " ")).strip(),
        "value": value,
        "unit": (str(f["unit"]).strip() or None) if f.get("unit") not in (None, "") else None,
        "variant": (str(f["variant"]).strip() or None) if f.get("variant") not in (None, "") else None,
        "quote": str(f.get("quote") or "").strip(),
        "source_id": sid,
    }


def _cache(prod: Product, sid: str):
    return prod.work / "research" / f"extract-{sid}.json"


def store(prod: Product, sid: str, data: dict, by: str | None) -> dict:
    """Validate and save the agent's extraction for one source."""
    idx = {s["id"]: s for s in sources.load_index(prod)}
    if sid not in idx:
        die(f"unknown source '{sid}' — see `studio.py sources`.")
    if not isinstance(data, dict) or not isinstance(data.get("facts"), list):
        die('extraction must be a JSON object with a "facts" array (see prompts/research-extract.md).')
    match = str(data.get("same_product", "unclear")).lower()
    if match not in MATCH_VALUES:
        die(f"same_product must be one of {MATCH_VALUES}")
    raw = data["facts"]
    facts = [cf for f in raw if (cf := _clean_fact(f, sid))]
    s = idx[sid]
    result = {
        "source_id": sid,
        "sha256": s["sha256"],
        "tier": s["tier"],
        "url": s.get("url"),
        "extracted_by": by or data.get("extracted_by") or "harness agent",
        "same_product": match,
        "same_product_reason": str(data.get("same_product_reason", "")),
        "facts": facts,
        "dropped": len(raw) - len(facts),
        "extracted_at": paths.now(),
    }
    paths.write_json(_cache(prod, sid), result)
    return result


def merge(prod: Product) -> dict:
    """Merge every up-to-date stored extraction into facts.draft.json."""
    idx = sources.load_index(prod)
    if not idx:
        die("no sources saved yet — add some with `fetch` / `add-source` first.")
    results, pending, stale = [], [], []
    for s in idx:
        cached = paths.read_json(_cache(prod, s["id"]))
        if not cached:
            pending.append(s["id"])
        elif cached.get("sha256") != s["sha256"]:
            stale.append(s["id"])
        else:
            results.append(cached)

    all_facts = []
    for r in results:
        for f in r["facts"]:
            all_facts.append({"id": f"F{len(all_facts) + 1}", **f})
    by = sorted({r.get("extracted_by") or "harness agent" for r in results})
    draft = {
        "product_id": prod.id,
        "generated_at": paths.now(),
        "extracted_by": ", ".join(by) or None,
        "sources": {
            r["source_id"]: {"tier": r["tier"], "url": r.get("url"), "same_product": r["same_product"],
                             "reason": r["same_product_reason"], "facts": len(r["facts"])}
            for r in results
        },
        "pending_sources": pending,
        "stale_sources": stale,
        "facts": all_facts,
    }
    paths.write_json(prod.work / "research" / "facts.draft.json", draft)
    paths.record(prod, "research", facts=len(all_facts), sources=len(results), pending=len(pending), stale=len(stale))
    return draft


def load_input(path) -> dict:
    data = paths.read_json(paths.p(path))
    if data is None:
        die(f"extraction file not found: {path}")
    return data
