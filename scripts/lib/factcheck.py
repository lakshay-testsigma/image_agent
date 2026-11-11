"""Fact-check pass: deterministic checks + an independent re-verification of every claim.

No model is called from here. The independent check is done by the harness (Claude Code / OpenCode /
Codex), ideally in a fresh subagent that never saw the research extraction:
  `verify --prepare`  writes factcheck/claims.json — claims to check, grouped by source, WITHOUT the
                      extractor's quotes
  checker agent       follows prompts/factcheck-verify.md, writes factcheck/verdicts*.json
  `verify`            applies everything below and writes facts.verified.json + report.md

Per claim (one fact from one source):
  1. source exists and is about the same product
  2. the extractor's quote really occurs in the saved source text (exact or >=90% fuzzy)
  3. the value really occurs inside that quote (numbers matched numerically)
  4. the independent checker must answer supported / contradicted / not_found / ambiguous with its own
     evidence quote, and that evidence quote must also occur in the source.

Per fact (key + variant) across sources:
  verified      all surviving claims agree AND (an authoritative source — client / manufacturer /
                gs1 — supports it, OR >=2 distributor/retailer sources on different web domains agree)
  needs_review  weaker support: a single secondary source, only `other`-tier sources (reviews, forums,
                sources whose product match is unclear) however many, or the independent check was skipped
  conflict      surviving claims disagree and no client value settles it
  rejected      no claim survived the checks
Text values agree only when they contain the same words ("oak" and "oak veneer" are a conflict);
numbers agree within TOLERANCE after unit conversion.
Human overrides (studio.py override) always win and are marked basis="human override".
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import urllib.parse

from . import paths, sources
from .paths import Product, die

TOLERANCE = 0.02  # relative tolerance when comparing converted numeric values


# ── units ────────────────────────────────────────────────────────────────────

def _units() -> dict[str, tuple[str, float]]:
    table: dict[str, tuple[str, float]] = {}

    def add(dim: str, factor: float, *names: str) -> None:
        for n in names:
            table[n] = (dim, factor)

    add("length", 1, "mm", "millimeter", "millimeters", "millimetre", "millimetres")
    add("length", 10, "cm", "centimeter", "centimeters", "centimetre", "centimetres")
    add("length", 1000, "m", "meter", "meters", "metre", "metres")
    add("length", 25.4, "in", "inch", "inches", '"', "″")
    add("length", 304.8, "ft", "foot", "feet", "'")
    add("mass", 0.001, "mg", "milligram", "milligrams")
    add("mass", 1, "g", "gram", "grams", "gr")
    add("mass", 1000, "kg", "kilogram", "kilograms", "kgs")
    add("mass", 453.59237, "lb", "lbs", "pound", "pounds")
    add("mass", 28.349523125, "oz", "ounce", "ounces")
    add("volume", 1, "ml", "milliliter", "milliliters", "millilitre", "millilitres")
    add("volume", 10, "cl")
    add("volume", 100, "dl")
    add("volume", 1000, "l", "liter", "liters", "litre", "litres")
    add("volume", 29.5735, "fl oz", "fl. oz", "floz", "fl.oz")
    add("volume", 3785.41, "gal", "gallon", "gallons")
    add("power", 1, "w", "watt", "watts")
    add("power", 1000, "kw")
    add("voltage", 1, "v", "volt", "volts")
    add("charge", 1, "mah")
    add("charge", 1000, "ah")
    add("energy", 1, "wh")
    add("energy", 1000, "kwh")
    add("frequency", 1, "hz")
    add("frequency", 1e3, "khz")
    add("frequency", 1e6, "mhz")
    add("frequency", 1e9, "ghz")
    add("data", 1e-3, "mb")
    add("data", 1, "gb")
    add("data", 1e3, "tb")
    add("percent", 1, "%", "percent")
    add("area", 1, "m2", "m²", "sqm", "sq m", "square meter", "square meters", "square metre", "square metres")
    add("area", 0.09290304, "sq ft", "sqft", "ft2", "ft²", "square foot", "square feet")
    add("area", 0.0001, "cm2", "cm²")
    add("area", 10000, "ha", "hectare", "hectares")
    add("area", 4046.8564224, "acre", "acres")
    add("time", 1, "s", "sec", "second", "seconds")
    add("time", 60, "min", "minute", "minutes")
    add("time", 3600, "h", "hr", "hrs", "hour", "hours")
    add("speed", 1, "km/h", "kmh", "kph")
    add("speed", 1.609344, "mph")
    add("length", 1e6, "km", "kilometer", "kilometers", "kilometre", "kilometres")
    add("length", 1609344, "mi", "mile", "miles")
    add("energy_food", 1, "kcal", "cal", "calorie", "calories")
    add("energy_food", 0.239006, "kj")
    add("light", 1, "lm", "lumen", "lumens")
    add("sound", 1, "db", "dba", "db(a)")
    add("torque", 1, "nm")
    add("power", 745.7, "hp", "bhp")
    add("power", 735.5, "ps", "cv")
    return table


UNITS = _units()


def unit_info(unit: str | None) -> tuple[str, float] | None:
    if not unit:
        return None
    return UNITS.get(unit.strip().lower().rstrip("."))


# ── text helpers ─────────────────────────────────────────────────────────────

_TRANS = str.maketrans({"“": '"', "”": '"', "″": '"', "‘": "'", "’": "'", "′": "'", "–": "-", "—": "-", "×": "x", " ": " "})


def norm(s) -> str:
    return re.sub(r"\s+", " ", str(s).translate(_TRANS).lower()).strip()


def to_number(v) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and re.fullmatch(r"\s*-?\d+(?:[.,]\d+)?\s*", v):
        return float(v.strip().replace(",", "."))
    return None


def numbers_in(s: str) -> list[float]:
    out = []
    for raw in re.findall(r"\d[\d,.]*", str(s)):
        raw = raw.rstrip(".,")
        if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", raw):
            raw = raw.replace(",", "")
        elif raw.count(",") == 1 and "." not in raw:
            raw = raw.replace(",", ".")
        try:
            out.append(float(raw))
        except ValueError:
            continue
    return out


def locate(quote: str, lines: list[str]) -> tuple[float, int]:
    """Best coverage (0-1) of `quote` inside the source lines, and the line index where it sits."""
    q = norm(quote)
    if not q:
        return 0.0, -1
    normed = [norm(l) for l in lines]
    full = " ".join(normed)
    if q in full:
        for i in range(len(normed)):
            window = " ".join(normed[i : i + 4])
            if q in window or (normed[i] and normed[i] in q):
                return 1.0, i
        return 1.0, 0
    best, best_i = 0.0, -1
    for i in range(len(normed)):
        cand = " ".join(normed[i : i + 3])
        if not cand:
            continue
        sm = difflib.SequenceMatcher(None, cand, q, autojunk=False)
        if sm.real_quick_ratio() * (len(cand) + len(q)) / (2 * len(q)) < best:
            continue
        cov = sum(b.size for b in sm.get_matching_blocks()) / len(q)
        if cov > best:
            best, best_i = cov, i
    return best, best_i


def value_in_quote(value, quote: str) -> bool:
    if isinstance(value, list):
        return all(value_in_quote(v, quote) for v in value)
    # yes/no facts ("Dishwasher safe." → yes): the quote is the evidence; "no" needs a negation in it
    if isinstance(value, bool) or norm(value) in ("yes", "no", "true", "false"):
        positive = value is True or norm(value) in ("yes", "true")
        negated = bool(re.search(r"\b(not|no|non|never|without)\b|n't", norm(quote)))
        return bool(norm(quote)) and positive != negated
    n = to_number(value)
    if n is not None:
        return any(abs(x - n) <= 1e-9 + 1e-6 * abs(n) for x in numbers_in(quote))
    v, q = norm(value), norm(quote)
    if not v:
        return False
    if v in q:
        return True
    nums = numbers_in(v)
    if nums and not all(any(abs(x - y) < 1e-9 for y in numbers_in(q)) for x in nums):
        return False
    words = [w for w in re.findall(r"[a-z0-9]+", v) if len(w) > 2]
    return bool(words) and sum(w in q for w in words) / len(words) >= 0.6


def canon(value, unit):
    n = to_number(value)
    if n is not None:
        ui = unit_info(unit)
        return (ui[0], n * ui[1]) if ui else ("num:" + norm(unit or ""), n)
    # text: the set of words, so word order and punctuation don't matter but every word does
    return ("text", frozenset(re.findall(r"[a-z0-9]+", norm(json.dumps(value) if isinstance(value, list) else value))))


def same_value(a, b) -> bool:
    if a[0] != b[0]:
        return False
    if a[0] == "text":
        return a[1] == b[1]
    return abs(a[1] - b[1]) <= TOLERANCE * max(abs(a[1]), abs(b[1]), 1e-9)


def domain(url: str | None) -> str | None:
    """Web domain of a source, or None for sources without a URL (local files, pasted text)."""
    return (urllib.parse.urlparse(url).netloc.lower().removeprefix("www.") or None) if url else None


# ── independent check (done by the harness agent) ────────────────────────────

def _draft_sha(prod: Product) -> str:
    return hashlib.sha256((prod.work / "research" / "facts.draft.json").read_bytes()).hexdigest()


def _checks(prod: Product, draft: dict, idx: dict, src_lines: dict) -> list[dict]:
    src_meta = draft.get("sources", {})
    claims = []
    for f in draft["facts"]:
        c = dict(f)
        sid = c["source_id"]
        checks = {"source_exists": sid in idx}
        if checks["source_exists"]:
            checks["same_product"] = src_meta.get(sid, {}).get("same_product", "unclear")
            cov, line = locate(c.get("quote", ""), src_lines[sid])
            checks["quote_coverage"] = round(cov, 3)
            checks["quote_found"] = cov >= 0.9
            checks["value_in_quote"] = value_in_quote(c["value"], c.get("quote", ""))
            c["_line"] = line
        c["checks"] = checks
        c["det_ok"] = bool(
            checks["source_exists"] and checks.get("same_product") != "no"
            and checks.get("quote_found") and checks.get("value_in_quote")
        )
        claims.append(c)
    return claims


def _load(prod: Product):
    draft = paths.read_json(prod.work / "research" / "facts.draft.json")
    if not draft:
        die("no research/facts.draft.json — run `extract` first.")
    idx = {s["id"]: s for s in sources.load_index(prod)}
    src_lines = {sid: [l for l in sources.source_text(prod, sid).splitlines() if l.strip()] for sid in idx}
    return draft, idx, src_lines


def prepare(prod: Product) -> dict:
    """Write factcheck/claims.json: every claim that passed the deterministic checks, without quotes."""
    draft, idx, src_lines = _load(prod)
    claims = _checks(prod, draft, idx, src_lines)
    by_src: dict[str, list] = {}
    for c in claims:
        if c["det_ok"]:
            by_src.setdefault(c["source_id"], []).append({k: c.get(k) for k in ("id", "key", "label", "value", "unit", "variant")})
    out = {
        "product_id": prod.id,
        "prepared_at": paths.now(),
        "draft_sha256": _draft_sha(prod),
        "instructions": "prompts/factcheck-verify.md",
        "verdicts_file": paths.rel(prod.work / "factcheck" / "verdicts.json"),
        "sources": [
            {"source_id": sid, "tier": idx[sid]["tier"], "url": idx[sid].get("url"),
             "source_file": paths.rel(sources.src_dir(prod) / f"{sid}.txt"), "claims": cl}
            for sid, cl in by_src.items()
        ],
        "failed_deterministic": [c["id"] for c in claims if not c["det_ok"]],
    }
    paths.write_json(prod.work / "factcheck" / "claims.json", out)
    return out


def load_verdicts(prod: Product) -> tuple[dict[str, dict], list[str]]:
    """Read every factcheck/verdicts*.json the checker wrote. Returns (verdicts by claim id, checker names)."""
    fc = prod.work / "factcheck"
    prepared = paths.read_json(fc / "claims.json")
    if not prepared:
        die("no factcheck/claims.json — run `verify --prepare`, have the independent checker write "
            "factcheck/verdicts.json, then run `verify` again.")
    if prepared.get("draft_sha256") != _draft_sha(prod):
        die("research/facts.draft.json changed since `verify --prepare` — run it again and re-check the claims.")
    verdicts: dict[str, dict] = {}
    checkers: set[str] = set()
    for f in sorted(fc.glob("verdicts*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            die(f"{paths.rel(f)} is not valid JSON: {e}")
        if isinstance(data, list):
            data = {"verdicts": data}
        checkers.add(str(data.get("checked_by") or "harness agent"))
        for v in data.get("verdicts", []):
            if isinstance(v, dict) and v.get("id"):
                verdicts[str(v["id"])] = v
    wanted = [c["id"] for s in prepared["sources"] for c in s["claims"]]
    missing = [i for i in wanted if i not in verdicts]
    if missing:
        die(f"no verdict yet for {len(missing)} claim(s): {', '.join(missing[:30])}"
            f"{' ...' if len(missing) > 30 else ''}. Check them (see factcheck/claims.json) or run with --deterministic-only.")
    return verdicts, sorted(checkers)


# ── main ─────────────────────────────────────────────────────────────────────

def verify(prod: Product, independent: bool = True, require: list[str] | None = None) -> dict:
    draft, idx, src_lines = _load(prod)
    claims = _checks(prod, draft, idx, src_lines)

    checker = None
    if independent:
        verdicts, checkers = load_verdicts(prod)
        checker = ", ".join(checkers)
        for c in claims:
            if not c["det_ok"]:
                continue
            v = verdicts.get(c["id"], {"verdict": "no_answer"})
            verdict = str(v.get("verdict", "no_answer")).lower()
            ev = str(v.get("evidence") or "")
            ev_cov, _ = locate(ev, src_lines[c["source_id"]]) if ev else (0.0, -1)
            if verdict == "supported" and ev_cov < 0.9:
                verdict = "evidence_not_in_source"
            c["checker"] = {"verdict": verdict, "evidence": ev, "evidence_coverage": round(ev_cov, 3),
                          "correct_value": v.get("correct_value"), "note": v.get("note")}

    def survives(c) -> bool:
        return c["det_ok"] and (not independent or c.get("checker", {}).get("verdict") == "supported")

    def eff_tier(c) -> str:
        tier = idx[c["source_id"]]["tier"]
        if c["checks"].get("same_product") == "unclear" and tier != "client":
            return "other"
        return tier

    groups: dict[tuple, list] = {}
    for c in claims:
        groups.setdefault((c["key"], norm(c["variant"]) if c.get("variant") else ""), []).append(c)

    facts, rejected = [], []
    for (key, _), cs in groups.items():
        alive = [c for c in cs if survives(c)]
        for c in cs:
            if not survives(c):
                rejected.append(_claim_out(c, idx))
        if not alive:
            facts.append(_fact(cs[0], "rejected", "no claim survived fact-checking", [], idx))
            continue
        clusters: list[list] = []
        for c in alive:
            cv = canon(c["value"], c.get("unit"))
            for cl in clusters:
                if same_value(cv, canon(cl[0]["value"], cl[0].get("unit"))):
                    cl.append(c)
                    break
            else:
                clusters.append([c])

        # a disagreement is settled only by exactly one cluster backed by the strongest tier present
        client = [cl for cl in clusters if any(eff_tier(c) == "client" for c in cl)]
        auth = [cl for cl in clusters if any(eff_tier(c) in sources.AUTHORITATIVE for c in cl)]
        preferred = client or auth
        conflicts = []
        if len(clusters) > 1 and len(preferred) != 1:
            facts.append(_fact(alive[0], "conflict", "sources disagree", alive, idx,
                               conflicts=[_cluster_out(cl, idx) for cl in clusters]))
            continue
        chosen = preferred[0] if preferred else clusters[0]
        if len(clusters) > 1:
            conflicts = [_cluster_out(cl, idx) for cl in clusters if cl is not chosen]
        tiers = {eff_tier(c) for c in chosen}
        rep = sorted(chosen, key=lambda c: sources.TIERS.index(eff_tier(c)))[0]
        # corroboration counts distinct web domains of distributor/retailer sources only: `other`-tier
        # sources and sources without a URL can't vouch for each other
        domains = sorted({d for c in chosen if eff_tier(c) in sources.CORROBORATING
                          and (d := domain(idx[c["source_id"]].get("url")))})
        if "client" in tiers:
            status, basis = "verified", "client-approved brief"
        elif not independent:
            status, basis = "needs_review", "independent check skipped (--deterministic-only)"
        elif tiers & sources.AUTHORITATIVE:
            auth = sorted({f"{eff_tier(c)}: {domain(idx[c['source_id']].get('url')) or c['source_id']}"
                           for c in chosen if eff_tier(c) in sources.AUTHORITATIVE})
            status, basis = "verified", f"authoritative source ({', '.join(auth)}; tier assigned by the researcher)"
        elif len(domains) >= 2:
            status, basis = "verified", f"{len(domains)} independent distributor/retailer sources agree ({', '.join(domains)})"
        elif tiers <= {"other"}:
            status, basis = "needs_review", f"only `other`-tier sources ({len(chosen)}) — never enough on their own"
        else:
            status, basis = "needs_review", f"single {eff_tier(rep)} source only"
        if conflicts:
            basis += f"; overrides conflicting lower-tier sources ({', '.join(s for c in conflicts for s in c['sources'])})"
        facts.append(_fact(rep, status, basis, chosen, idx, conflicts=conflicts))

    _apply_overrides(prod, facts)

    present = {f["key"] for f in facts if f["status"] == "verified"}
    missing = [k for k in (require or []) if k not in present]
    out = {
        "product_id": prod.id,
        "generated_at": paths.now(),
        "extracted_by": draft.get("extracted_by"),
        "checked_by": checker,
        "independent_check": independent,
        "summary": {s: sum(f["status"] == s for f in facts) for s in ("verified", "needs_review", "conflict", "rejected")},
        "required": list(require or []),
        "missing_required": missing,
        "facts": sorted(facts, key=lambda f: (["verified", "needs_review", "conflict", "rejected"].index(f["status"]), f["key"])),
        "rejected_claims": rejected,
    }
    paths.write_json(prod.work / "factcheck" / "facts.verified.json", out)
    (prod.work / "factcheck" / "report.md").write_text(report_md(out), encoding="utf-8")
    paths.record(prod, "factcheck", **out["summary"], missing_required=len(missing), independent_check=independent)
    return out


def _claim_out(c: dict, idx: dict) -> dict:
    s = idx.get(c["source_id"], {})
    return {
        "claim_id": c["id"], "key": c["key"], "value": c["value"], "unit": c.get("unit"), "variant": c.get("variant"),
        "source_id": c["source_id"], "tier": s.get("tier"), "url": s.get("url"), "quote": c.get("quote"),
        "checks": c["checks"], "checker": c.get("checker"),
    }


def _cluster_out(cl: list, idx: dict) -> dict:
    return {"value": cl[0]["value"], "unit": cl[0].get("unit"), "sources": sorted({c["source_id"] for c in cl})}


def _fact(rep: dict, status: str, basis: str, support: list, idx: dict, conflicts=None) -> dict:
    return {
        "key": rep["key"], "label": rep.get("label"), "variant": rep.get("variant"),
        "value": rep["value"], "unit": rep.get("unit"), "status": status, "basis": basis,
        "evidence": [_claim_out(c, idx) for c in support], "conflicts": conflicts or [],
    }


def _apply_overrides(prod: Product, facts: list) -> None:
    for o in paths.read_json(prod.work / "factcheck" / "overrides.json", []):
        target = [f for f in facts if f["key"] == o["key"] and norm(f.get("variant") or "") == norm(o.get("variant") or "")]
        if o["action"] == "reject":
            for f in target:
                f.update(status="rejected", basis=f"human override: {o.get('note') or 'rejected'}")
            continue
        label = o.get("label") or (target[0].get("label") if target else None) or o["key"].replace("_", " ").capitalize()
        entry = {"key": o["key"], "label": label, "variant": o.get("variant"),
                 "value": o["value"], "unit": o.get("unit"), "status": "verified",
                 "basis": f"human override: {o.get('note') or ''}".strip(), "evidence": [], "conflicts": []}
        if target:
            target[0].update(entry)
            for extra in target[1:]:
                facts.remove(extra)
        else:
            facts.append(entry)


def add_override(prod: Product, key: str, value=None, unit=None, variant=None, label=None, note="", reject=False) -> dict:
    path = prod.work / "factcheck" / "overrides.json"
    items = [o for o in paths.read_json(path, []) if not (o["key"] == key and norm(o.get("variant") or "") == norm(variant or ""))]
    n = to_number(value)
    if n is not None:
        value = int(n) if n.is_integer() else n
    entry = {"action": "reject" if reject else "set", "key": key, "value": value,
             "unit": unit, "variant": variant, "label": label, "note": note, "at": paths.now()}
    items.append(entry)
    paths.write_json(path, items)
    return entry


def fmt_value(f: dict) -> str:
    v = f["value"]
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, list):
        v = ", ".join(map(str, v))
    return f"{v} {f['unit']}".strip() if f.get("unit") else str(v)


def report_md(out: dict) -> str:
    s = out["summary"]
    lines = [
        f"# Fact-check report — {out['product_id']}",
        "",
        f"Generated {out['generated_at']} · extracted by `{out['extracted_by'] or '-'}` · "
        f"independently checked by `{out['checked_by'] or 'skipped'}`",
        "",
        f"**{s['verified']} verified · {s['needs_review']} need review · {s['conflict']} conflicts · {s['rejected']} rejected**",
        "",
    ]
    if out["missing_required"]:
        lines += ["## Missing required facts", "", *[f"- `{k}` — no verified value" for k in out["missing_required"]], ""]
    lines += ["## Facts", "", "| Status | Fact | Variant | Value | Basis | Sources |", "|---|---|---|---|---|---|"]
    for f in out["facts"]:
        srcs = ", ".join(sorted({e["source_id"] for e in f["evidence"]})) or "-"
        lines.append(f"| {f['status']} | {f['label']} (`{f['key']}`) | {f.get('variant') or '-'} | {fmt_value(f)} | {f['basis']} | {srcs} |")
    conflicts = [f for f in out["facts"] if f["conflicts"]]
    if conflicts:
        lines += ["", "## Conflicts", ""]
        for f in conflicts:
            alts = "; ".join(f"{c['value']} {c.get('unit') or ''} ({', '.join(c['sources'])})".strip() for c in f["conflicts"])
            lines.append(f"- **{f['label']}**: kept `{fmt_value(f)}` ({f['status']}); other values: {alts}")
    if out["rejected_claims"]:
        lines += ["", "## Rejected claims", "", "| Claim | Fact | Value | Source | Why |", "|---|---|---|---|---|"]
        for c in out["rejected_claims"]:
            why = [k for k in ("quote_found", "value_in_quote") if c["checks"].get(k) is False]
            if c["checks"].get("same_product") == "no":
                why.append("different product")
            if c.get("checker"):
                why.append(f"checker: {c['checker']['verdict']}")
            lines.append(f"| {c['claim_id']} | {c['key']} | {c['value']} {c.get('unit') or ''} | {c['source_id']} | {', '.join(why) or '-'} |")
    lines += ["", "Resolve items with `studio.py override` (human decision) or add better sources and re-run.", ""]
    return "\n".join(lines)
