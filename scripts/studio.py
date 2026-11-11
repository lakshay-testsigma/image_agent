#!/usr/bin/env python3
"""Product Studio CLI — deterministic plumbing for the agent skills. ONE product per call.

No API keys, no .env, no model calls: the harness (Claude Code / OpenCode / Codex) does the research,
the independent fact-check and the image generation. These commands save, validate and log its work.

Every product command takes the product image path (or its folder) as the first argument:
    uv run scripts/studio.py init assets/001-oak-chair/01-front.jpg

Run `uv run scripts/studio.py <command> -h` for details on any command.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import paths  # noqa: E402
from lib.paths import die  # noqa: E402


def out(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def read_arg_text(text: str | None, file: str | None, what: str) -> str:
    if file:
        return paths.p(file).read_text(encoding="utf-8")
    if text:
        return text
    die(f"provide --{what} or --{what}-file")
    return ""


# ── commands ─────────────────────────────────────────────────────────────────

def cmd_init(a):
    from lib import sources

    prod = paths.resolve(a.product)
    prod.work.mkdir(parents=True, exist_ok=True)
    warnings = []
    s0 = None
    if prod.brief:
        text = paths.brief_text(prod)
        (prod.work / "brief.snapshot.md").write_text(text, encoding="utf-8")
        known = paths.brief_section(text, "Known facts")
        if known:
            s0, _ = sources.add_source(prod, f"CLIENT-APPROVED FACTS (from {paths.rel(prod.brief)})\n{known}",
                                       "client", title="Client brief — known facts", kind="brief", sid="S0", replace=True)
        if not paths.brief_section(text, "Creative direction"):
            warnings.append("brief has no 'Creative direction' — ask the user what look they want before planning shots.")
    else:
        warnings.append("no brief.md for this subject — copy assets/_template/brief.md next to the images, or ask the user.")
    if not prod.images:
        warnings.append("concept job: no subject photo — images are generated from the brief (+ refs/ as style references).")
    m = paths.load_manifest(prod)
    m["inputs"] = prod.to_dict()
    paths.write_json(prod.manifest_path, m)
    paths.record(prod, "init", images=len(prod.images), style_refs=len(prod.style_refs), brief=bool(prod.brief))
    out({**prod.to_dict(), "client_source": s0["id"] if s0 else None, "warnings": warnings})


STAGES = ["init", "intake", "research", "factcheck", "design", "metadata", "creative", "render", "qa", "export"]


def cmd_status(a):
    prod = paths.resolve(a.product)
    m = paths.load_manifest(prod)
    st = m["stages"]
    skipped = {k: v.get("reason") for k, v in st.items() if v.get("status") == "skipped"}
    done = {s for s in STAGES if s in st} | ({"render"} if any(k.startswith("render:") for k in st) else set())
    from lib import design, metadata, renders

    w = prod.work
    files = {
        "intake": w / "intake.json", "sources": w / "sources/index.json", "facts_draft": w / "research/facts.draft.json",
        "facts_verified": w / "factcheck/facts.verified.json", "factcheck_report": w / "factcheck/report.md",
        "design_resolved": w / "design/design.resolved.json", "metadata": w / "metadata/product.json",
        "shot_plan": w / "creative/shot-plan.md", "qa": w / "qa/qa.json", "qa_report": w / "qa/qa-report.md",
        "listing": w / "final/listing.json",
    }
    if (w / "creative/shot-plan.md").exists():
        done.add("creative")
    # design and metadata only count as done while they still match their inputs on disk
    if design.stale_reason(prod):
        done.discard("design")
    stale = metadata.stale_reason(prod)
    if stale:
        done.discard("metadata")
    meta = paths.read_json(files["metadata"]) if not stale else None
    shots = {m["name"]: renders.budget(prod, meta, m["name"]) for m in meta["design"]["mockups"]} if meta else None
    renders = sorted(paths.rel(f) for f in (w / "renders").rglob("*") if f.suffix.lower() in paths.IMAGE_EXTS) if (w / "renders").exists() else []
    nxt = next((s for s in STAGES if s not in done), None)
    out({
        "product_id": prod.id,
        "stages_done": [s for s in STAGES if s in done and s not in skipped],
        "stages_skipped": skipped,
        "next_stage": nxt,
        "files": {k: paths.rel(v) for k, v in files.items() if v.exists()},
        "renders": renders,
        "factcheck_summary": {k: st["factcheck"].get(k) for k in ("verified", "needs_review", "conflict", "rejected")} if "factcheck" in st else None,
        "metadata_ready": not stale, "metadata_problem": stale,
        "mockup_attempts": shots,
        "inputs": prod.to_dict(),
    })


def cmd_intake(a):
    from lib import intake

    prod = paths.resolve(a.product)
    out(intake.store(prod, paths.p(a.input) if a.input else None))


def cmd_design(a):
    from lib import design

    prod = paths.resolve(a.product)
    r = design.resolve(prod)
    out({"file": paths.rel(design.resolved_path(prod)), "design_system": r["name"], "layers": r["layers"],
         "mockups": [{"name": m["name"], "type": m["type"], "variations": m["variations"], "output": m["style"]["output"]}
                     for m in r["mockups"]],
         "generations_planned": sum(m["variations"] for m in r["mockups"]),
         "max_attempts_per_mockup": r["generation"]["max_attempts"],
         "overrides_applied": [e for e in r["resolution_log"] if e["applied"]],
         "overrides_blocked": [e for e in r["resolution_log"] if not e["applied"]],
         "warnings": r["warnings"], "next": "`studio.py metadata`"})


def cmd_metadata(a):
    from lib import metadata

    prod = paths.resolve(a.product)
    m = metadata.build(prod)
    at = m["attributes"]
    out({"file": paths.rel(metadata.path(prod)), "schema": "schemas/product.schema.json", "valid": True,
         "identification": m["identification"],
         "attributes": {k: (v if k == "unavailable" else [f["key"] for f in v]) for k, v in at.items()},
         "research": m["research"]["status"], "mockups": [x["name"] for x in m["design"]["mockups"]],
         "warnings": m["warnings"]})


def cmd_skip(a):
    prod = paths.resolve(a.product)
    paths.record(prod, a.stage, status="skipped", reason=a.reason)
    out({"stage": a.stage, "status": "skipped", "reason": a.reason})


def cmd_fetch(a):
    from lib import sources

    prod = paths.resolve(a.product)
    title, text = sources.fetch_url(a.url)
    entry, created = sources.add_source(prod, text, a.tier, url=a.url, title=a.title or title, replace=a.replace)
    out({**entry, "created": created, "preview": text[:600]})


def cmd_add_source(a):
    from lib import sources

    prod = paths.resolve(a.product)
    if a.file:
        f = paths.p(a.file)
        text, kind, title = sources.file_to_text(f), "file", a.title or f.name
    else:
        text, kind, title = read_arg_text(a.text, a.text_file, "text"), "text", a.title
    entry, created = sources.add_source(prod, text, a.tier, url=a.url, title=title, kind=kind, replace=a.replace)
    out({**entry, "created": created})


def cmd_sources(a):
    from lib import sources

    out(sources.load_index(paths.resolve(a.product)))


def cmd_extract(a):
    from lib import research

    prod = paths.resolve(a.product)
    stored = None
    if a.input:
        if not a.source or len(a.source) != 1:
            die("--input needs exactly one --source (the source the extraction was made from)")
        r = research.store(prod, a.source[0], research.load_input(a.input), a.by)
        stored = {"source": r["source_id"], "facts": len(r["facts"]), "dropped_invalid": r["dropped"]}
    draft = research.merge(prod)
    out({"stored": stored, "facts": len(draft["facts"]), "sources": draft["sources"],
         "pending_sources": draft["pending_sources"], "stale_sources": draft["stale_sources"],
         "file": paths.rel(prod.work / "research/facts.draft.json")})


def cmd_verify(a):
    from lib import factcheck

    prod = paths.resolve(a.product)
    if a.prepare:
        res = factcheck.prepare(prod)
        out({"claims_file": paths.rel(prod.work / "factcheck/claims.json"),
             "claims_to_check": sum(len(s["claims"]) for s in res["sources"]),
             "by_source": {s["source_id"]: len(s["claims"]) for s in res["sources"]},
             "failed_deterministic": res["failed_deterministic"],
             "next": "independent checker follows prompts/factcheck-verify.md and writes factcheck/verdicts.json "
                     "(or verdicts-<source>.json per source); then run `verify` without --prepare"})
        return
    require = [k.strip() for k in (a.require or "").split(",") if k.strip()]
    res = factcheck.verify(prod, independent=not a.deterministic_only, require=require)
    out({"summary": res["summary"], "missing_required": res["missing_required"],
         "report": paths.rel(prod.work / "factcheck/report.md"), "file": paths.rel(prod.work / "factcheck/facts.verified.json")})
    if res["missing_required"]:
        # results are written; the non-zero exit makes sure a missing required fact is never overlooked
        print(f"error: required fact(s) not verified: {', '.join(res['missing_required'])}", file=sys.stderr)
        sys.exit(2)


def cmd_override(a):
    from lib import factcheck

    prod = paths.resolve(a.product)
    if not a.reject and a.value is None:
        die("give --value (or --reject)")
    entry = factcheck.add_override(prod, a.key, a.value, a.unit, a.variant, a.label, a.note, a.reject)
    out({"override": entry, "next": "re-run `verify` to apply"})


def cmd_facts(a):
    from lib.factcheck import fmt_value

    prod = paths.resolve(a.product)
    v = paths.read_json(prod.work / "factcheck" / "facts.verified.json") or die("no verified facts yet — run `verify`.")
    rows = [f for f in v["facts"] if a.all or f["status"] == "verified"]
    out([{"key": f["key"], "label": f["label"], "variant": f.get("variant"), "value": fmt_value(f),
          "status": f["status"], "basis": f["basis"]} for f in rows])


def _refs(prod, a):
    from lib import renders

    return renders.reference_images(prod, only_primary=a.only_primary, no_product_refs=a.no_product_refs,
                                    extra=a.ref, with_style_refs=a.with_style_refs)


def cmd_refs(a):
    prod = paths.resolve(a.product)
    refs = _refs(prod, a)
    out({"reference_images": [str(r) for r in refs], "relative": [paths.rel(r) for r in refs],
         "note": "attach in this order; the prompt must say what each image is"})


def cmd_preflight(a):
    from lib import renders

    prod = paths.resolve(a.product)
    out(renders.preflight(prod, a.shot, _refs(prod, a), a.extra_attempt))


def cmd_register(a):
    from lib import renders

    prod = paths.resolve(a.product)
    prompt = read_arg_text(a.prompt, a.prompt_file, "prompt")
    params = {k: v for k, v in (("size", a.size), ("quality", a.quality), ("background", a.background)) if v}
    out(renders.register(prod, a.shot, [paths.p(i) for i in a.image], prompt, a.engine, _refs(prod, a),
                         a.model, params, a.notes))


def cmd_overlay(a):
    from lib import overlay

    prod = paths.resolve(a.product)
    out(overlay.render_overlay(prod, paths.p(a.spec)))


def cmd_inspect(a):
    from lib import review

    out([review.inspect(paths.p(i)) for i in a.images])


def cmd_contact_sheet(a):
    from lib import review

    prod = paths.resolve(a.product)
    imgs = [paths.p(i) for i in a.images] if a.images else []
    if not imgs:
        imgs = list(prod.images)
        if (prod.work / "renders").exists():
            imgs += sorted(f for f in (prod.work / "renders").rglob("*") if f.suffix.lower() in paths.IMAGE_EXTS)
    dest = paths.p(a.out) if a.out else prod.work / "qa" / "contact-sheet.png"
    out({"contact_sheet": paths.rel(review.contact_sheet(prod, imgs, dest)), "images": [paths.rel(i) for i in imgs]})


def cmd_qa_mark(a):
    from lib import review

    prod = paths.resolve(a.product)
    out(review.qa_mark(prod, paths.p(a.image), {"factual": a.factual, "visual": a.visual, "creative": a.creative}, a.notes or ""))


def cmd_qa_set(a):
    from lib import review

    out(review.qa_set(paths.resolve(a.product), a.consistency, a.notes or ""))


def cmd_export(a):
    from lib import review

    prod = paths.resolve(a.product)
    desc = paths.p(a.description_file).read_text(encoding="utf-8") if a.description_file else None
    listing = review.export(prod, [paths.p(i) for i in (a.image or [])], desc, a.force, a.partial)
    out({"listing": paths.rel(prod.work / "final/listing.json"), "metadata": listing["metadata"],
         "images": [i["file"] for i in listing["images"]], "excluded_unverified": listing["excluded_unverified"],
         "missing_mockups": listing["missing_mockups"], "forced": listing["forced"]})


# ── parser ───────────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(prog="studio.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    P = "subject image path (or its folder) — e.g. assets/001-oak-chair/01-front.jpg"

    def cmd(name, fn, help_):
        s = sub.add_parser(name, help=help_)
        s.set_defaults(fn=fn)
        return s

    s = cmd("init", cmd_init, "create the product workspace, snapshot the brief, register client facts as source S0")
    s.add_argument("product", help=P)

    s = cmd("status", cmd_status, "show what is done for this product and what comes next")
    s.add_argument("product", help=P)

    s = cmd("intake", cmd_intake, "validate the agent's intake.json against schemas/intake.schema.json and render intake.md")
    s.add_argument("product", help=P)
    s.add_argument("--input", help="intake JSON written elsewhere (default: output/<id>/intake.json)")

    s = cmd("design", cmd_design, "resolve global + per-product + session design layers into design.resolved.json")
    s.add_argument("product", help=P)

    s = cmd("metadata", cmd_metadata, "build and schema-validate metadata/product.json (required before any render)")
    s.add_argument("product", help=P)

    s = cmd("skip", cmd_skip, "mark a stage as not needed for this job (e.g. research for a portrait or a concept poster)")
    s.add_argument("product", help=P)
    s.add_argument("--stage", required=True, choices=["research", "factcheck"])
    s.add_argument("--reason", required=True, help="why, e.g. 'artwork reproduction: no factual claims on images'")

    tiers = ["client", "manufacturer", "gs1", "distributor", "retailer", "other"]
    s = cmd("fetch", cmd_fetch, "download a URL (HTML/PDF), convert to text, save as evidence")
    s.add_argument("product", help=P)
    s.add_argument("url")
    s.add_argument("--tier", required=True, choices=tiers)
    s.add_argument("--title")
    s.add_argument("--replace", action="store_true", help="replace an existing source with the same URL")

    s = cmd("add-source", cmd_add_source, "save evidence from a local file (pdf/html/txt/md) or raw text")
    s.add_argument("product", help=P)
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--file")
    g.add_argument("--text-file")
    g.add_argument("--text")
    s.add_argument("--tier", required=True, choices=tiers)
    s.add_argument("--url")
    s.add_argument("--title")
    s.add_argument("--replace", action="store_true")

    s = cmd("sources", cmd_sources, "list saved evidence")
    s.add_argument("product", help=P)

    s = cmd("extract", cmd_extract, "store the agent's fact extraction for a source, then merge all into facts.draft.json")
    s.add_argument("product", help=P)
    s.add_argument("--source", action="append", help="source id the --input extraction belongs to, e.g. S1")
    s.add_argument("--input", help="JSON extraction written by the agent (format: prompts/research-extract.md)")
    s.add_argument("--by", help="who extracted, e.g. 'claude-opus-5-5 (Claude Code)'")

    s = cmd("verify", cmd_verify, "deterministic checks + independent checker verdicts -> facts.verified.json + report.md")
    s.add_argument("product", help=P)
    s.add_argument("--prepare", action="store_true", help="write factcheck/claims.json (claims without quotes) for the checker")
    s.add_argument("--require", help="comma-separated fact keys that must end up verified, e.g. height,width,weight")
    s.add_argument("--deterministic-only", action="store_true",
                   help="skip the independent check (nothing above needs_review except client facts)")

    s = cmd("override", cmd_override, "record a HUMAN decision for a fact (set value or reject); re-run verify after")
    s.add_argument("product", help=P)
    s.add_argument("--key", required=True)
    s.add_argument("--value")
    s.add_argument("--unit")
    s.add_argument("--variant")
    s.add_argument("--label")
    s.add_argument("--note", required=True, help="who decided and why, e.g. 'client confirmed by email 2026-11-06'")
    s.add_argument("--reject", action="store_true")

    s = cmd("facts", cmd_facts, "print verified facts (what may appear on images / listings)")
    s.add_argument("product", help=P)
    s.add_argument("--all", action="store_true", help="include needs_review / conflict / rejected")

    def ref_flags(s):
        s.add_argument("--ref", action="append", help="extra reference image (style, model, logo); repeatable")
        s.add_argument("--with-style-refs", action="store_true", help="also include every image in the product's refs/ folder")
        s.add_argument("--only-primary", action="store_true", help="only the primary subject image, not all angles")
        s.add_argument("--no-product-refs", action="store_true", help="no subject photos (background plates / free concepts)")

    s = cmd("refs", cmd_refs, "ordered reference images to attach to the harness image tool for a shot")
    s.add_argument("product", help=P)
    ref_flags(s)

    s = cmd("preflight", cmd_preflight, "gate BEFORE generating a shot: metadata current, shot planned, prompt, refs, attempt budget")
    s.add_argument("product", help=P)
    s.add_argument("--shot", required=True, help="mockup name from the resolved design")
    s.add_argument("--extra-attempt", metavar="REASON", help="the user approved one more attempt past the budget; quote them")
    ref_flags(s)

    s = cmd("register", cmd_register, "log images made by the harness image tool into renders/<shot>/ (audit trail)")
    s.add_argument("product", help=P)
    s.add_argument("--shot", required=True, help="shot name, e.g. hero, lifestyle-kitchen, detail-stitching")
    s.add_argument("--image", action="append", required=True, help="generated image file; repeat for variations")
    s.add_argument("--prompt-file")
    s.add_argument("--prompt")
    s.add_argument("--engine", default="harness", help="e.g. claude-code+<mcp tool>, opencode+<tool>, codex-imagegen")
    s.add_argument("--model", help="image model the tool used, if known")
    s.add_argument("--size")
    s.add_argument("--quality")
    s.add_argument("--background")
    s.add_argument("--notes")
    ref_flags(s)

    s = cmd("overlay", cmd_overlay, "draw verified facts / approved copy / logos onto an image from a JSON spec")
    s.add_argument("product", help=P)
    s.add_argument("--spec", required=True)

    s = cmd("inspect", cmd_inspect, "size, aspect, alpha, sharpness of images")
    s.add_argument("images", nargs="+")

    s = cmd("contact-sheet", cmd_contact_sheet, "grid of product photos + renders for side-by-side review")
    s.add_argument("product", help=P)
    s.add_argument("images", nargs="*", help="default: all product photos + all renders")
    s.add_argument("--out")

    s = cmd("qa-mark", cmd_qa_mark, "record QA verdicts for one image (approved = three gates pass + deterministic checks)")
    s.add_argument("product", help=P)
    s.add_argument("image")
    for gate in ("factual", "visual", "creative"):
        s.add_argument(f"--{gate}", required=True, choices=["pass", "fail", "na"] if gate == "factual" else ["pass", "fail"])
    s.add_argument("--notes")

    s = cmd("qa-set", cmd_qa_set, "record the set-level verdict: approved images are consistent and usefully different")
    s.add_argument("product", help=P)
    s.add_argument("--consistency", required=True, choices=["pass", "fail"])
    s.add_argument("--notes")

    s = cmd("export", cmd_export, "copy approved images to final/ and write listing.json (verified facts only)")
    s.add_argument("product", help=P)
    s.add_argument("--image", action="append", help="default: every image approved in qa.json")
    s.add_argument("--description-file")
    s.add_argument("--force", action="store_true", help="export despite QA problems (only when the user asks)")
    s.add_argument("--partial", action="store_true", help="export although some planned mockups have no approved image")

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
