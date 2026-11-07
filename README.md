# Product Studio

Agent workflow that takes **one product photo** and turns it into:
1. researched product details, every one traced to a saved source,
2. an independent fact-check by a second model (DeepSeek / Qwen / any open model),
3. product photography and mockups from OpenAI `gpt-image`, using the real photo as reference so the product stays identical,
4. deterministic spec callouts and copy (only verified facts and approved text),
5. three-gate QA and an export package with a full audit trail.

The skills run in **Claude Code** (`.claude/skills/`) and **Codex** (`.agents/skills` → same folder).

```
product photo ─► intake ─► research ─► fact-check ─► creative plan ─► render ─► overlay ─► QA ─► export
                 (agent)   (RESEARCH   (FACTCHECK     (agent, your     (OpenAI    (Pillow)  (agent +  (final/ +
                           model)      model)         direction)       gpt-image)            vision)   listing.json)
```

## Setup

```bash
uv sync                       # installs openai, pillow, python-dotenv, pypdf into .venv
cp .env.example .env          # then fill in keys
```

`.env` roles (all OpenAI-compatible, so you can mix providers):

| Role | Example | Needed for |
|---|---|---|
| `RESEARCH_*` | DeepSeek `deepseek-chat` | extracting facts from sources |
| `FACTCHECK_*` | DeepSeek `deepseek-reasoner`, or Ollama `qwen2.5:14b` locally | independent verification |
| `VISION_*` (optional) | Ollama `qwen2.5vl:7b` | second opinion on photos and renders |
| `OPENAI_API_KEY`, `IMAGE_*` | `gpt-image-1` | rendering |
| `SEARCH_PROVIDER` (optional) | tavily / brave / searxng | the agent can use its own web search instead |

Fully local research and fact-check: run Ollama and point both roles at `http://localhost:11434/v1` with `API_KEY=ollama`. A different model per role is best.

## Add a product

```bash
cp -r assets/_template assets/001-oak-chair
# drop photos in: assets/001-oak-chair/01-front.jpg, 02-side.jpg ...
# optional mood boards / model refs / logo: assets/001-oak-chair/refs/
# fill in assets/001-oak-chair/brief.md (known facts + your creative direction for THIS product)
```
Optional shared house style per client: copy `brands/_template.md` → `brands/<client>.md` and reference it from the brief.

## Run it (one product per session)

Claude Code:
```
/product-studio assets/001-oak-chair/01-front.jpg
/product-studio assets/001-oak-chair/01-front.jpg moody dark editorial, 3 shots, autopilot
```
Codex:
```
Use the product-studio skill on assets/001-oak-chair/01-front.jpg
```
Or run single stages, each taking the same path:

| Skill | Does |
|---|---|
| `product-intake` | workspace, brief, photo analysis, preservation checklist |
| `product-research` | find and save sources, research model extracts facts with quotes |
| `product-factcheck` | fact-check model + deterministic checks, conflicts, human overrides |
| `product-creative` | your direction → shot plan → one prompt per shot |
| `product-render` | OpenAI gpt-image edit renders (or Codex built-in image_gen + `register`) |
| `product-overlay` | text, spec callouts and logos drawn deterministically |
| `product-qa` | factual / visual / creative gates per image |
| `product-export` | `final/` images + `listing.json` (verified facts only) |

The agent pauses for your OK when the brief is missing direction, when facts conflict, before spending on renders, and before export. Say "autopilot" to skip the pauses.

## Where things go

```
output/<product-id>/
├── manifest.json            stage status + event log
├── brief.snapshot.md        brief as it was when the run started
├── intake.md                identity, visible text, preservation checklist
├── sources/                 S0 (client brief facts), S1.. saved evidence + index.json
├── research/                per-source extractions + facts.draft.json
├── factcheck/               facts.verified.json, report.md, overrides.json
├── creative/                shot-plan.md, prompts/<shot>.md, overlays/<shot>.json
├── renders/<shot>/          vN-i.png + vN.json (prompt, model, params, refs)
├── qa/                      qa.json, qa-report.md, contact-sheet.png
└── final/                   approved images + listing.json (+ description.md)
```

## Customising

- **Creative freedom:** nothing in the scripts picks a style. Direction comes from you (session > brief > brand profile). `product-creative/style-inspiration.md` is an optional idea library.
- **Research and fact-check behaviour:** edit `prompts/research-extract.md` and `prompts/factcheck-verify.md`.
- **Verification policy** (tiers, tolerance, what counts as verified): `scripts/lib/factcheck.py`.
- **Fonts for overlays:** drop `.ttf`/`.otf` files in `fonts/` and reference them by name.

## CLI reference

`uv run scripts/studio.py -h`. Commands: `init status search fetch add-source sources extract verify override facts ask render register overlay inspect contact-sheet qa-mark export`.
