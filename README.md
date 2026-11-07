# Product Studio

Agent workflow that takes **one product photo** and turns it into:
1. researched product details, every one traced to a saved source,
2. an independent fact-check by a fresh subagent that never saw the extraction,
3. product photography and mockups made by your harness's image tool, using the real photo as reference so the product stays identical,
4. deterministic spec callouts and copy (only verified facts and approved text),
5. three-gate QA and an export package with a full audit trail.

**No API keys, no `.env`.** Everything model-shaped (research, fact-check, looking at images, image generation) is done by the CLI harness you run the skills in: **Claude Code**, **OpenCode** or **Codex**. The Python scripts only save, validate and log.

```
product photo ─► intake ─► research ─► fact-check ─► creative plan ─► render ─► overlay ─► QA ─► export
                 (agent)   (agent:     (subagent:     (agent, your     (harness   (Pillow)  (agent)  (final/ +
                           web +       independent    direction)       image                       listing.json)
                           extract)    check)                          tool)
```

## Setup

```bash
uv sync     # installs pillow + pypdf into .venv — that's all
```

Image generation needs an image tool in your harness that accepts reference images:
- **Codex:** built-in `image_gen` works out of the box.
- **Claude Code / OpenCode:** connect an image-generation MCP server. Without one, stages 1–4 still run and the agent stops before rendering.

## Add a product

```bash
cp -r assets/_template assets/001-oak-chair
# drop photos in: assets/001-oak-chair/01-front.jpg, 02-side.jpg ...
# optional mood boards / model refs / logo: assets/001-oak-chair/refs/
# fill in assets/001-oak-chair/brief.md (known facts + your creative direction for THIS product)
```
Optional shared house style per client: copy `brands/_template.md` → `brands/<client>.md` and reference it from the brief.

## Run it (one product per session)

Claude Code (skills in `.claude/skills/`):
```
/product-studio assets/001-oak-chair/01-front.jpg
/product-studio assets/001-oak-chair/01-front.jpg moody dark editorial, 3 shots, autopilot
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
| `product-intake` | workspace, brief, photo analysis, preservation checklist |
| `product-research` | agent finds + saves sources, extracts facts with verbatim quotes |
| `product-factcheck` | deterministic checks + independent subagent check, conflicts, human overrides |
| `product-creative` | your direction → shot plan → one prompt per shot |
| `product-render` | harness image tool with product photos as references, logged with `register` |
| `product-overlay` | text, spec callouts and logos drawn deterministically |
| `product-qa` | factual / visual / creative gates per image |
| `product-export` | `final/` images + `listing.json` (verified facts only) |

The agent pauses for your OK when the brief is missing direction, when facts conflict, before generating images, and before export. Say "autopilot" to skip the pauses.

## Where things go

```
output/<product-id>/
├── manifest.json            stage status + event log
├── brief.snapshot.md        brief as it was when the run started
├── intake.md                identity, visible text, preservation checklist
├── sources/                 S0 (client brief facts), S1.. saved evidence + index.json
├── research/                input-<S>.json (agent extraction), extract-<S>.json, facts.draft.json
├── factcheck/               claims.json, verdicts-<S>.json, facts.verified.json, report.md, overrides.json
├── creative/                shot-plan.md, prompts/<shot>.md, overlays/<shot>.json
├── renders/<shot>/          vN-i.png + vN.json (prompt, engine, model, refs)
├── qa/                      qa.json, qa-report.md, contact-sheet.png
└── final/                   approved images + listing.json (+ description.md)
```

## Customising

- **Creative freedom:** nothing in the scripts picks a style. Direction comes from you (session > brief > brand profile). `product-creative/style-inspiration.md` is an optional idea library.
- **Extraction and fact-check rules:** edit `prompts/research-extract.md` and `prompts/factcheck-verify.md`.
- **Verification policy** (tiers, tolerance, what counts as verified): `scripts/lib/factcheck.py`.
- **Fonts for overlays:** drop `.ttf`/`.otf` files in `fonts/` and reference them by name.

## CLI reference

`uv run scripts/studio.py -h`. Commands: `init status fetch add-source sources extract verify override facts refs register overlay inspect contact-sheet qa-mark export`.
