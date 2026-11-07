---
name: product-studio
description: End-to-end pipeline for ONE product — intake, research, fact-check, creative direction, image generation with the harness's own image tool, overlays, QA and export. Use when the user gives a product image path (e.g. assets/001-oak-chair/01-front.jpg) and wants mockups / product photography / a verified listing for it.
argument-hint: <product-image-path> [extra instructions]
---

# Product Studio — full run for one product

**Product:** `$ARGUMENTS`. The first token is the product image path (or its folder); anything after it is extra direction from the user. If you see the literal text `$ARGUMENTS` (OpenCode/Codex don't substitute it), take the path and direction from the user's message. If there is no path, ask for one. Never process more than one product in a session — if the user lists several, do the first and tell them to start a new session for the next.

**You are every model in this pipeline.** There are no API keys and no `.env`. You (the harness: Claude Code, OpenCode or Codex) do the web research, the fact extraction, the independent fact-check (in a subagent), the image review, and the image generation (with your own image tool). The scripts only save, validate and log your work. Never write code that calls a model or image API, and never ask the user for an API key.

All commands run from the repo root: `uv run scripts/studio.py <command> <product-path> ...`, always with the same product path.

## Pipeline

Run the stage skills in order. Load each one (Claude Code: Skill tool; OpenCode: `skill` tool; Codex: read `.agents/skills/<name>/SKILL.md`) and follow it:

| # | Stage | Skill | Produces in `output/<id>/` |
|---|---|---|---|
| 1 | Intake | `product-intake` | `intake.md`, `manifest.json` |
| 2 | Research | `product-research` | `sources/`, `research/facts.draft.json` |
| 3 | Fact-check | `product-factcheck` | `factcheck/facts.verified.json`, `report.md` |
| 4 | Creative plan | `product-creative` | `creative/shot-plan.md`, `creative/prompts/*.md` |
| 5 | Render | `product-render` | `renders/<shot>/vN-*.png` + `vN.json` |
| 6 | Overlay (only if a shot needs text) | `product-overlay` | `*-overlay.png` |
| 7 | QA | `product-qa` | `qa/qa.json`, `qa/qa-report.md` |
| 8 | Export | `product-export` | `final/` + `listing.json` |

Resuming: run `uv run scripts/studio.py status <product-path>` first. It lists finished stages and the next one. Skip what's done unless the user asks to redo it.

## Before you start: check your image tool

Stage 5 needs an image-generation tool in this harness that accepts reference images (Codex built-in `image_gen`, or an image MCP tool in Claude Code / OpenCode). If you have none, say so at the start: stages 1–4 can still run, and rendering resumes once a tool is connected. Don't fall back to writing an API script.

## Checkpoints (pause and ask the user)

Stop and ask at these points unless the user said to run unattended ("autopilot", "don't ask"):

1. **After intake** — only if there's no brief or no creative direction. Offer to draft a direction from the photos.
2. **After fact-check** — if there are `conflict` results or a required fact is missing. Show the short table and ask: provide the value, accept a source, or continue without it.
3. **Before rendering** — show the shot list (one line per shot: purpose, setting, aspect, text overlay yes/no) and the number of image generations. Get a go-ahead.
4. **Before export** — show which images passed QA.

In autopilot: never invent missing facts, skip shots that depend on unverified facts, and record every assumption in the QA report.

## Non-negotiables

- The user's creative direction leads. The style library is ideas, not rules. If the brief asks for something unusual, do that.
- Never invent product attributes. Only `verified` facts may appear in overlays, alt text or listings.
- Facts come from saved sources: you extract them with verbatim quotes, an independent checker re-verifies them, and the scripts decide the status. Your memory is never evidence.
- Never modify anything in `assets/`. Everything goes to `output/<id>/`.
- Don't ask the image tool to render specs, prices or claims as text. Add text with `product-overlay`.
- The real product must stay recognisably identical: shape, proportions, colours, logo, label, materials.

## Final summary to the user

When done, reply with: the product id, verified / needs-review / conflict counts, the final images (paths), anything blocked and why, and the next action for the user (e.g. "confirm weight with client, then re-run `product-factcheck`").
