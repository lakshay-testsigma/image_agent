# Product Studio

Agent workflow that takes **one subject photo (or just a brief)**, from **any genre or industry**, and turns it into:
1. images in any medium: photography, 3D, illustration, posters, ad creatives, thumbnails, UI/device mockups, virtual staging, packaging mockups, made by your harness's image tool with the real photo as reference (identical, recognisable or freely inspired: you choose the fidelity),
2. researched facts, every one traced to a saved source, plus an independent fact-check by a fresh subagent (when facts appear on images or listings; skippable otherwise),
3. one look across every subject: a required global design system, optional per-product overrides, merged by fixed rules into a schema-validated product metadata file that generation must go through,
4. deterministic text, logos and real-asset composites (screenshots, artwork, labels in perspective) and exact channel sizes,
5. QA with deterministic checks plus three judgement gates (factual + compliance, fidelity, creative), a set-level consistency verdict, a retry budget, and an export package with a full audit trail.

Subjects: retail products, food & drink, fashion, beauty, real estate & interiors, automotive, tech & SaaS, healthcare, finance/B2B, people, pets, travel, packaging, art & merch, events, ad campaigns. Playbooks per industry are in `.claude/skills/product-creative/genres.md`; skill names say "product" but mean any subject.

**No API keys, no `.env`.** Everything model-shaped (research, fact-check, looking at images, image generation) is done by the CLI harness you run the skills in: **Claude Code**, **OpenCode** or **Codex**. The Python scripts only save, validate and log.

```
photo ─► intake ─► research ─► fact-check ─► design + metadata ─► creative ─► render ─► overlay ─► QA ─► export
         (agent,   (agent:     (subagent +    (scripts: merge      (agent)     (harness  (Pillow)  (agent +  (final/)
         schema-   web +       scripts)       design layers,                   image               script
         checked)  extract)                   validate JSON)                   tool)               checks)
```

## Setup

```bash
uv sync                                               # pillow + pypdf (+ pytest for the test suite)
cp design/global.example.json design/global.json      # then edit: this is YOUR required global design system
uv run pytest                                         # optional: test suite, a few seconds, no network / model / image tool
```

Image generation needs an image tool in your harness that accepts reference images:
- **Codex:** built-in `image_gen` works out of the box.
- **Claude Code / OpenCode:** connect an image-generation MCP server. Without one, stages 1–4 still run and the agent stops before rendering.

## Add a job

```bash
cp -r assets/_template assets/001-oak-chair
# drop subject photos in: assets/001-oak-chair/01-front.jpg, 02-side.jpg ...   (none = concept job)
# optional mood boards / model refs / logo / screenshots: assets/001-oak-chair/refs/
# fill in assets/001-oak-chair/brief.md: subject, industry, fidelity, direction, style, deliverables, approved copy
# optional: assets/001-oak-chair/design.json — this subject's own look / shot list (delete it to use the global design as is)
```
Optional client notes (voice, audience): copy `brands/_template.md` → `brands/<client>.md` and reference it from the brief.

## Design system: two levels

| Level | File | Required | Holds |
|---|---|---|---|
| Global | `design/global.json` | **yes** | theme, palette, typography, lighting, shadows, background, composition, camera, positioning, output size, generation budget, avoid list, identity constraints, default mockups, and `locked` paths |
| Per product | `assets/<job>/design.json` | no | only the fields this subject changes, extra avoid/identity entries, its own mockup list with per-mockup style |
| Session | `output/<id>/design/session.json` | no | what you asked for in the chat, recorded by the agent |

`uv run scripts/studio.py design <path>` merges them into `output/<id>/design/design.resolved.json`:

1. start from global;
2. product, then session: later wins field by field, objects merge key by key;
3. a path in global `locked` keeps the global value — the override is dropped and logged;
4. `must_avoid` and `identity_constraints` only grow;
5. the last layer that defines `mockups` replaces the list (none anywhere → one mockup `main`);
6. output aspect and size are kept in agreement;
7. a style text that mentions an avoided thing is flagged; the avoid list wins.

The result lists every override applied, every override blocked and every warning, so "why does this shot look like that" always has an answer. Shapes: `schemas/design.schema.json`.

## Run it (one product per session)

Claude Code (skills in `.claude/skills/`):
```
/product-studio assets/001-oak-chair/01-front.jpg
/product-studio assets/001-oak-chair/01-front.jpg moody dark editorial, 3 shots, autopilot
/product-studio assets/002-ramen/01-bowl.jpg 90s anime key visual, Instagram 4:5 + story, no research
/product-studio assets/003-launch-poster/  Swiss poster for our SaaS launch, A3 + LinkedIn banner
```
OpenCode (reads `.claude/skills/` natively; slash commands in `.opencode/commands/`):
```
/product-studio assets/001-oak-chair/01-front.jpg
```
Codex (`.agents/skills` → same folder):
```
Use the product-studio skill on assets/001-oak-chair/01-front.jpg
```
Every stage is also its own skill / command, taking the same path:

| Skill | Does |
|---|---|
| `product-intake` | workspace, brief, photo analysis → schema-validated `intake.json`: subject type, fidelity mode, visual traits, preservation checklist |
| `product-research` | agent finds + saves sources, extracts facts with verbatim quotes (skip when no facts are shown) |
| `product-factcheck` | deterministic checks + independent subagent check, conflicts, human overrides |
| `product-design` | global + per-product + session design → `design.resolved.json`; then `metadata/product.json`, validated against its schema |
| `product-creative` | resolved design + your direction → shot plan → one prompt per mockup |
| `product-render` | `preflight` gate, harness image tool with subject photos as references, logged with `register`, limited retries |
| `product-overlay` | text, callouts, logos, perspective composites, channel resizes, all deterministic |
| `product-qa` | deterministic checks + factual / fidelity / creative gates per image + a set verdict |
| `product-export` | `final/` images + `listing.json` (verified facts with sources) + `product.json` |

The agent pauses for your OK when the brief is missing direction, when facts conflict or a required fact is missing, when a design override is blocked, before generating images, when a mockup's retry budget is used up, and before export. Say "autopilot" to skip the pauses that are only confirmations.

## What each stage needs, produces and refuses

| Stage | Needs | Produces | Checked by the script | Stops when |
|---|---|---|---|---|
| intake | photos and/or brief | `intake.json`, `intake.md` | schema; fidelity vs photos; photo files exist | invalid JSON shape, `exact` without photos or checklist |
| research | intake, web | `sources/`, `facts.draft.json` | source hash per extraction; malformed facts dropped and counted | unknown source, extraction not an object with `facts` |
| fact-check | draft, saved sources | `facts.verified.json`, `report.md` | quote in source, value in quote, checker's evidence in source, unit-aware agreement, tiers, variants | a claim has no verdict; draft changed after `--prepare`; exit 2 if a required fact is not verified |
| design | `design/global.json` | `design.resolved.json` | schemas; the 7 rules above | no global file; unknown keys; contradictory output; duplicate mockups |
| metadata | intake, facts or skip, resolved design | `metadata/product.json` | product schema; every verified attribute has a source; input hashes | fact-check neither done nor skipped; skipped but facts needed; no consent; stale design |
| creative | `product.json` | `shot-plan.md`, `prompts/<mockup>.md` | (prompt must exist at preflight) | — |
| render | current metadata, prompt | `renders/<shot>/vN-i.png`, `vN.json` | `preflight`: planned mockup, references fit fidelity, attempt budget | stale metadata; unplanned shot; no prompt; budget used up |
| overlay | render, verified facts, approved copy | image + `.overlay.json` | fact is verified; copy is an approved phrase; files exist | unverified fact; unapproved or partial copy |
| QA | renders, `product.json` | `qa.json`, `qa-report.md` | delivery size, attempt budget, subject reference, drawn facts still current; approval bound to file hash | `--factual na` on an image with drawn text |
| export | approvals | `final/` + `listing.json` + `product.json` | approvals and hashes; set verdict covers the images; every mockup covered | unapproved or changed image; no passing set verdict; missing mockup (`--partial`) |

## Where things go

```
output/<product-id>/
├── manifest.json            stage status + event log
├── brief.snapshot.md        brief as it was when the run started
├── intake.json              structured observations (source of truth) + intake.md (readable view)
├── sources/                 S0 (client brief facts), S1.. saved evidence + index.json
├── research/                input-<S>.json (agent extraction), extract-<S>.json, facts.draft.json
├── factcheck/               claims.json, verdicts-<S>.json, facts.verified.json, report.md, overrides.json
├── design/                  session.json (optional), design.resolved.json (merged design + override log)
├── metadata/                product.json (validated; the only place later stages read facts and design from)
├── creative/                shot-plan.md, prompts/<mockup>.md, overlays/<shot>.json
├── renders/<shot>/          vN-i.png + vN.json (prompt, engine, model, refs, attempt), attempts.json
├── qa/                      qa.json (verdicts, checks, file hashes, set verdict), qa-report.md, contact-sheet.png
└── final/                   approved images + listing.json + product.json (+ description.md)
```

`uv run scripts/studio.py status <path>` shows where a job stands: stages done and skipped, the next stage, whether the metadata is still current (and why not), and attempts used per mockup. `manifest.json` keeps a timestamped event for every command that changed something.

## Customising

- **Creative freedom:** nothing in the scripts picks a style, genre or industry. The frame is your design system; inside it, direction comes from you (session > brief > brand profile). Optional idea libraries in `.claude/skills/product-creative/`: `genres.md` (industry playbooks + compliance), `style-inspiration.md` (looks and mediums), `formats.md` (channel sizes).
- **Extraction and fact-check rules:** edit `prompts/research-extract.md` and `prompts/factcheck-verify.md`.
- **Verification policy** (tiers, tolerance, what counts as verified): `scripts/lib/factcheck.py`.
- **Design rules and defaults:** `scripts/lib/design.py` (`RULES`, default budget). **Data shapes:** `schemas/*.json`, checked by the small validator in `scripts/lib/schema.py` (a subset of JSON Schema; no extra dependency).
- **QA checks and export rules:** `scripts/lib/review.py`. **Render gate and retry budget:** `scripts/lib/renders.py`.
- **Fonts for overlays:** drop `.ttf`/`.otf` files in `fonts/` and reference them by name.

## CLI reference

`uv run scripts/studio.py -h`. Commands: `init status intake skip fetch add-source sources extract verify override facts design metadata refs preflight register overlay inspect contact-sheet qa-mark qa-set export`.

## Tests

```bash
uv run pytest
```
`tests/` covers each stage on its own (`test_schema`, `test_design`, `test_factcheck`, `test_overlay`, `test_metadata`, `test_gates`) and two full runs through the CLI (`test_e2e`: a product with photos, facts and a per-product design; a concept job with none of them). The agent's work (intake JSON, extractions, checker verdicts) and the image tool are replaced by small fixture files, so the tests need no network and no model, and every script gate runs for real.

## Design decisions and limits

- **Scripts decide, the model proposes.** Anything that can be checked without judgement is checked by code: quotes exist in sources, statuses follow tier rules, design merges follow fixed rules, sizes match, files haven't changed since review. Judgement (does this look like the same chair?) stays with the agent and is recorded, never trusted to block or unblock a deterministic check.
- **One file per boundary.** `intake.json` → `facts.verified.json` → `design.resolved.json` → `product.json` → `vN.json` → `qa.json` → `listing.json`. Each records the hash of what it was built from, so a change upstream makes everything downstream visibly stale instead of silently wrong.
- **Global design is required, product design never is.** A missing per-product file is the normal case and resolves to the global look.
- **Locks instead of priorities.** "Which instruction wins" is answered by one list in the global file, not by wording in a prompt.
- **Not checked by code (know the limits):** whether a render really matches the subject or the design (the agent's eye, plus an optional second-opinion subagent); whether the image tool sneaked text into a picture; whether a source tagged `manufacturer` really is the official one (the report names every source treated as authoritative); whether the "independent" checker is truly independent (it gets the claims without quotes, but it is the same kind of model); design contradictions written in prose are only flagged when a style text names an avoided term.
- **Fact-check is strict on purpose.** Text values must contain the same words to agree, so near-matches ("oak" / "oak veneer") surface as conflicts for a person to settle rather than merging.
- **One subject per session.** Consistency across subjects comes from the shared `design/global.json`, not from batching.
