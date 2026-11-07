# Product Studio — agent instructions

This repo turns ONE product photo into researched, fact-checked product data and AI product photography.
Skills live in `.claude/skills/` (Claude Code). `.agents/skills` is a symlink to the same folder (Codex).

## Model roles
| Role | Who | Configured in |
|---|---|---|
| Orchestrator | you (Claude Code / Codex): find sources, plan creative, review images, talk to the user | — |
| Research | extracts facts + verbatim quotes from saved sources (DeepSeek / Qwen / any OpenAI-compatible) | `RESEARCH_*` in `.env` |
| Fact-check | independently re-verifies each claim against the source (ideally a different model) | `FACTCHECK_*` |
| Vision (optional) | second opinion on photos / renders | `VISION_*` |
| Image | OpenAI gpt-image, edit mode with the real product photos as references | `OPENAI_API_KEY`, `IMAGE_*` |

## Skills (all take the product image path as their first argument)
`product-studio` (runs everything) → `product-intake` → `product-research` → `product-factcheck` → `product-creative` → `product-render` → `product-overlay` (optional) → `product-qa` → `product-export`

## Golden rules
1. **One product per session.** Every command gets the same product path, e.g. `assets/001-oak-chair/01-front.jpg`.
2. **Never modify `assets/`.** All work goes to `output/<product-id>/`.
3. **Never invent facts.** Facts come from saved sources and pass `verify`, or from a user decision recorded with `override`. Only `verified` facts go on images and listings.
4. **No text from the image model.** Specs, copy and logos are added with `overlay`.
5. **Keep the product identical**: shape, proportions, colours, materials, logo, label.
6. **The user's creative direction leads.** There are no mandatory presets. Session instructions beat the brief, which beats the brand profile, which beats defaults.
7. **Ask before spending** (image renders) and before exporting. Never publish anywhere.

## CLI
`uv run scripts/studio.py <command> <product-path> ...` — commands: `init status search fetch add-source sources extract verify override facts ask render register overlay inspect contact-sheet qa-mark export` (`-h` on any).

## Layout
```
assets/NNN-name/            input photos + brief.md + refs/   (user-owned, read-only for agents)
assets/_template/           brief template
brands/                     optional per-client brand profiles
prompts/                    system prompts for research + fact-check models (editable)
scripts/studio.py, lib/     deterministic plumbing
output/<id>/                manifest.json, intake.md, sources/, research/, factcheck/, creative/, renders/, qa/, final/
```
