# Product Studio — agent instructions

This repo turns ONE subject photo (or a brief) into AI imagery for **any genre or industry**: products, food, fashion, beauty, real estate, automotive, tech/apps, portraits, pets, travel, art, events, ad campaigns. It's photography, 3D, illustration, posters, thumbnails or UI mockups, plus researched, fact-checked data whenever facts appear on images or listings.

"Product" in skill names means **any subject**. A folder with only `brief.md` (+ `refs/`) is a concept job.

There are **no API keys and no `.env`**: the harness running these skills (Claude Code, OpenCode or Codex) does all the model work. The Python scripts are deterministic plumbing only (save, validate, log).

Skills live in `.claude/skills/`. Claude Code and OpenCode read that folder directly; `.agents/skills` is a symlink to it (Codex). OpenCode slash commands that load each skill live in `.opencode/commands/`.

## Who does what
| Job | Who |
|---|---|
| Orchestrate, talk to the user, plan creative | you (the harness agent) |
| Web search + saving sources (only if facts will appear) | you, with your web tools + `studio.py fetch / add-source`; otherwise `studio.py skip` |
| Structured intake (what the photos show) | you → `output/<id>/intake.json` → `studio.py intake` (schema-validated) |
| Fact extraction with verbatim quotes | you, following `prompts/research-extract.md` → `studio.py extract --input` |
| Independent fact-check | a fresh subagent that never saw the extraction, following `prompts/factcheck-verify.md` → `studio.py verify` |
| Design decisions | the user: `design/global.json` (required) + `assets/<job>/design.json` (optional). You only record what they ask for this session in `output/<id>/design/session.json` |
| Design resolution, product metadata | `studio.py design` (fixed precedence rules) → `studio.py metadata` (schema-validated `product.json`) |
| Looking at photos and renders | you (open the image files); optional second-opinion subagent |
| Image generation | your harness's image tool (Codex `image_gen`, or an image MCP tool), with subject photos as references per fidelity mode: `studio.py preflight` before, `studio.py register` after |
| Approving images | you judge three gates (`qa-mark`) and the set (`qa-set`); the scripts add deterministic checks you can't override |
| Text, specs, logos, real screenshots/artwork, channel resizes | `studio.py overlay` (Pillow, incl. perspective `corners`), never the image tool |

Never write code that calls a model or image API, and never ask for an API key. If the harness has no image tool, stop before rendering and say so.

## Skills (all take the subject image path, or the job folder, as their first argument)
`product-studio` (runs everything) → `product-intake` → `product-research` → `product-factcheck` → `product-design` → `product-creative` → `product-render` → `product-overlay` (optional) → `product-qa` → `product-export`

## Golden rules
1. **One subject/job per session.** Every command gets the same path, e.g. `assets/001-oak-chair/01-front.jpg`.
2. **Never modify `assets/`.** All work goes to `output/<product-id>/`.
3. **Never invent facts.** Facts come from saved sources and pass `verify`, or from a user decision recorded with `override`. Only `verified` facts go on images and listings. Your memory is never evidence, and what the photos show is `inferred`, not fact.
4. **No text from the image tool.** Specs, copy, logos and real UI/artwork are added with `overlay`.
5. **Respect the fidelity mode**: `exact` = identical subject (shape, colours, materials, logo, label); `likeness` = clearly recognisable (people, pets, places, dishes); `inspired` / `none` = creative freedom per brief.
6. **A global design system is required; a per-product one is optional.** `studio.py design` merges global → product → session by fixed rules (locked fields keep the global value; avoid lists and identity constraints only grow) and logs every override and every blocked one. Never edit `design/global.json` or `assets/` to get a render through, and never invent a house style. The subject's identity and facts outrank every design layer.
7. **Inside the resolved design, the user's creative direction leads**, in any genre, industry or medium. `product-creative/genres.md`, `style-inspiration.md` and `formats.md` are idea libraries. For what the design leaves open: session instructions beat the brief, which beats the brand profile, which beats defaults.
8. **Don't work around a gate.** No render without current `metadata/product.json` and a passing `preflight`; retries stop at the attempt budget unless the user grants more; an image is approved only with three gates plus the deterministic checks; a command that stops with `error:` names the cause to fix.
9. **Industry compliance and people's rights**: disclosures, no unapproved claims, real people only with consent, no logos/characters without rights (see `genres.md`).
10. **Ask before generating images** and before exporting. Never publish anywhere.

## CLI
`uv run scripts/studio.py <command> <path> ...` — commands: `init status intake skip fetch add-source sources extract verify override facts design metadata refs preflight register overlay inspect contact-sheet qa-mark qa-set export` (`-h` on any).

Tests: `uv run pytest` (no network, no model, no image tool: the agent's parts are faked, every script gate runs for real). Run them after changing anything in `scripts/` or `schemas/`.

## Layout
```
design/global.json          REQUIRED global design system (user-owned; start from global.example.json)
assets/NNN-name/            subject photos (optional) + brief.md + design.json (optional) + refs/   (user-owned, read-only for agents)
assets/_template/           brief + per-product design templates
brands/                     optional per-client brand profiles (voice, audience; the design system rules on visuals)
prompts/                    rules for extraction + independent fact-check (editable)
schemas/                    JSON Schemas: intake, design (global / layer / resolved), product metadata
scripts/studio.py, lib/     deterministic plumbing (Pillow + pypdf only)
tests/                      pytest suite for every gate + two end-to-end runs
output/<id>/                manifest.json, intake.json (+ intake.md), sources/, research/, factcheck/, design/, metadata/, creative/, renders/, qa/, final/
```
