---
name: product-studio
description: End-to-end pipeline for ONE product — intake, research, fact-check, creative direction, OpenAI image rendering, overlays, QA and export. Use when the user gives a product image path (e.g. assets/001-oak-chair/01-front.jpg) and wants mockups / product photography / a verified listing for it.
argument-hint: <product-image-path> [extra instructions]
---

# Product Studio — full run for one product

**Product:** `$ARGUMENTS` — the first token is the product image path (or its folder); anything after it is extra direction from the user. If no path was given (here or in the user's message), ask for one. Never process more than one product in a session — if the user lists several, do the first and tell them to start a new session for the next.

All commands run from the repo root: `uv run scripts/studio.py <command> <product-path> ...`. Call the same product path every time.

## Pipeline

Run the stage skills in order. Each one is also usable on its own, so read its SKILL.md and follow it:

| # | Stage | Skill | Produces in `output/<id>/` |
|---|---|---|---|
| 1 | Intake | `product-intake` | `intake.md`, `manifest.json` |
| 2 | Research | `product-research` | `sources/`, `research/facts.draft.json` |
| 3 | Fact-check | `product-factcheck` | `factcheck/facts.verified.json`, `report.md` |
| 4 | Creative plan | `product-creative` | `creative/shot-plan.md`, `creative/prompts/*.md` |
| 5 | Render | `product-render` | `renders/<shot>/vN-*.png` + `vN.json` |
| 6 | Overlay (only if a shot needs text) | `product-overlay` | `*-callouts.png` |
| 7 | QA | `product-qa` | `qa/qa.json`, `qa/qa-report.md` |
| 8 | Export | `product-export` | `final/` + `listing.json` |

Resuming: run `uv run scripts/studio.py status <product-path>` first — it lists finished stages and the next one. Skip what's done unless the user asks to redo it.

## Checkpoints (pause and ask the user)

Stop and ask at these points unless the user said to run unattended ("autopilot", "don't ask"):

1. **After intake** — only if there's no brief or no creative direction. Offer to draft a direction from the photos.
2. **After fact-check** — if there are `conflict` results or any required fact is missing. Show the short table and ask: provide the value, accept a source, or continue without it.
3. **Before rendering** — show the shot list (one line per shot: purpose, setting, aspect, text overlay yes/no) and the estimated number of API image calls. Rendering costs money; get a go-ahead.
4. **Before export** — show which images passed QA.

In autopilot: never invent missing facts, skip shots that depend on unverified facts, and record every assumption in the QA report.

## Non-negotiables

- The user's creative direction leads. The style library and presets are ideas, not rules. If the brief asks for something unusual, do that.
- Never invent product attributes. Only `verified` facts may appear in overlays, alt text, or listings.
- Never modify anything in `assets/`. Everything goes to `output/<id>/`.
- Don't ask the image model to render specs, prices or claims as text. Add text with `product-overlay`, using verified facts and approved copy only.
- The real product must stay recognisably identical: shape, proportions, colours, logo, label, materials.
- Use the research and fact-check models in `.env` for facts. You (the orchestrating agent) can find and save sources, but verdicts come from the pipeline and from the user's overrides, not your own memory.

## Final summary to the user

When done, reply with: the product id, verified/needs-review/conflict counts, the list of final images (paths), anything blocked and why, and the next action for the user (e.g. "confirm weight with client, then re-run `product-factcheck`").
