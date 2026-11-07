"""Research model pass: extract product facts (with verbatim quotes) from each saved source.

The research model never answers from memory — it only reads text we saved in sources/.
One call per source (chunked if long), cached by content hash, merged into facts.draft.json.
"""
from __future__ import annotations

import os
import re
import sys

from . import models, paths, sources
from .paths import Product, die

MATCH_RANK = {"yes": 3, "likely": 2, "unclear": 1, "no": 0}


def identity_hints(prod: Product) -> str:
    parts = []
    intake = prod.work / "intake.md"
    if intake.exists():
        parts.append("INTAKE NOTES (from the product photos):\n" + intake.read_text(encoding="utf-8")[:6000])
    if prod.brief:
        sec = paths.brief_section(paths.brief_text(prod), "Product")
        if sec:
            parts.append("CLIENT BRIEF — product identity:\n" + sec)
    return "\n\n".join(parts) or "(no identity hints available)"


def _chunks(text: str, size: int, overlap: int = 1500) -> list[str]:
    if len(text) <= size:
        return [text]
    out, i = [], 0
    while i < len(text):
        out.append(text[i : i + size])
        i += size - overlap
    return out


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


def extract(prod: Product, only: list[str] | None = None, force: bool = False) -> dict:
    idx = sources.load_index(prod)
    if not idx:
        die("no sources saved yet — add some with `fetch` / `add-source` first.")
    system = (paths.PROMPTS / "research-extract.md").read_text(encoding="utf-8")
    hints = identity_hints(prod)
    max_chars = int(os.getenv("RESEARCH_MAX_SOURCE_CHARS", "24000"))
    _, _, model = models.role_config("research")
    out_dir = prod.work / "research"

    results = []
    for s in idx:
        cache = out_dir / f"extract-{s['id']}.json"
        cached = paths.read_json(cache)
        skip = only and s["id"] not in only
        if cached and (skip or (not force and cached.get("sha256") == s["sha256"])):
            results.append(cached)
            continue
        if skip:
            continue

        text = sources.source_text(prod, s["id"])
        parts = _chunks(text, max_chars)
        facts, best, reason = [], None, ""
        for i, chunk in enumerate(parts, 1):
            print(f"[research] {s['id']} part {i}/{len(parts)} ({len(chunk)} chars) → {model}", file=sys.stderr)
            user = (
                f"PRODUCT IDENTITY HINTS\n{hints}\n\n"
                f"SOURCE {s['id']} — tier: {s['tier']}; title: {s.get('title') or '-'}; url: {s.get('url') or '-'}"
                f" (part {i} of {len(parts)})\n<<<SOURCE\n{chunk}\nSOURCE>>>\n\nReturn the JSON object only."
            )
            data = models.parse_json(models.chat("research", system, user, json_mode=True, temperature=0))
            match = str(data.get("same_product", "unclear")).lower()
            if best is None or MATCH_RANK.get(match, 1) > MATCH_RANK.get(best, 1):
                best, reason = match, str(data.get("same_product_reason", ""))
            facts += [cf for f in data.get("facts", []) if (cf := _clean_fact(f, s["id"]))]

        result = {
            "source_id": s["id"],
            "sha256": s["sha256"],
            "tier": s["tier"],
            "url": s.get("url"),
            "model": model,
            "same_product": best or "unclear",
            "same_product_reason": reason,
            "facts": facts,
            "extracted_at": paths.now(),
        }
        paths.write_json(cache, result)
        results.append(result)

    all_facts = []
    for r in results:
        for f in r["facts"]:
            all_facts.append({"id": f"F{len(all_facts) + 1}", **f})
    draft = {
        "product_id": prod.id,
        "generated_at": paths.now(),
        "model": model,
        "sources": {
            r["source_id"]: {"tier": r["tier"], "url": r.get("url"), "same_product": r["same_product"],
                             "reason": r["same_product_reason"], "facts": len(r["facts"])}
            for r in results
        },
        "facts": all_facts,
    }
    paths.write_json(out_dir / "facts.draft.json", draft)
    paths.record(prod, "research", facts=len(all_facts), sources=len(results), model=model)
    return draft
