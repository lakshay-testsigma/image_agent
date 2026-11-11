---
name: product-studio
description: End-to-end image pipeline for ONE subject in any genre or industry (products, food, fashion, beauty, real estate, automotive, tech/app, portraits, pets, travel, art, events, ad campaigns) — intake, optional research + fact-check, design-system resolution and validated product metadata, creative direction in any medium, image generation with the harness's own image tool, overlays/compositing, QA and export. Use when the user gives an image path (e.g. assets/001-oak-chair/01-front.jpg) or a brief folder and wants images, mockups, photography, ad creatives, posters, thumbnails or a verified listing.
argument-hint: <subject-image-path> [extra instructions]
---

# Product Studio — full run for one subject

**Subject:** `$ARGUMENTS`. The first token is the subject image path (or its folder); anything after it is extra direction from the user. If you see the literal text `$ARGUMENTS` (OpenCode/Codex don't substitute it), take the path and direction from the user's message. If there is no path, ask for one. Never process more than one subject in a session — if the user lists several, do the first and tell them to start a new session for the next.

"Product" in skill and command names means **any subject**: a retail product, a dish, a garment, a person, a pet, a room, a vehicle, an app, an artwork, a brand campaign. A folder with only `brief.md` (+ `refs/`) and no subject photo is a **concept job** (fidelity `none`). Any medium is fine: photography, 3D, illustration, posters, infographics, UI mockups.

**You are every model in this pipeline.** There are no API keys and no `.env`. You (the harness: Claude Code, OpenCode or Codex) do the web research, the fact extraction, the independent fact-check (in a subagent), the image review, and the image generation (with your own image tool). The scripts only save, validate and log your work. Never write code that calls a model or image API, and never ask the user for an API key.

All commands run from the repo root: `uv run scripts/studio.py <command> <path> ...`, always with the same path.

## Pipeline

Run the stage skills in order. Load each one (Claude Code: Skill tool; OpenCode: `skill` tool; Codex: read `.agents/skills/<name>/SKILL.md`) and follow it:

| # | Stage | Skill | Produces in `output/<id>/` |
|---|---|---|---|
| 1 | Intake | `product-intake` | `intake.json` (+ `intake.md` view), `manifest.json` |
| 2 | Research (if facts are needed) | `product-research` | `sources/`, `research/facts.draft.json` |
| 3 | Fact-check (if facts are needed) | `product-factcheck` | `factcheck/facts.verified.json`, `report.md` |
| 4 | Design system + metadata | `product-design` | `design/design.resolved.json`, `metadata/product.json` |
| 5 | Creative plan | `product-creative` | `creative/shot-plan.md`, `creative/prompts/*.md` |
| 6 | Render | `product-render` | `renders/<shot>/vN-*.png` + `vN.json` |
| 7 | Overlay / composite (text, logos, UI, resizes) | `product-overlay` | `*-overlay.png` + sidecar |
| 8 | QA | `product-qa` | `qa/qa.json`, `qa/qa-report.md` |
| 9 | Export | `product-export` | `final/` + `listing.json` + `product.json` |

Each stage is gated by the scripts, not by your memory of what happened: `metadata` refuses without a valid intake, a finished-or-skipped fact-check and a current design; `preflight` / `register` / `qa-mark` / `export` refuse on missing or stale metadata; `overlay` refuses unverified facts and unapproved copy; `export` refuses unapproved or changed images. When a command stops with `error:`, read the message, fix that cause, and don't work around it.

**When to skip research + fact-check:** only when no factual claim (specs, numbers, ingredients, prices, dates, awards) will appear on any image, alt text or listing, e.g. a portrait, a pet painting, a mood campaign, a concept poster with only approved copy. Record it, and then nothing but approved copy may be drawn:
```bash
uv run scripts/studio.py skip <path> --stage research --reason "portrait, no factual claims"
uv run scripts/studio.py skip <path> --stage factcheck --reason "portrait, no factual claims"
```
If in doubt, ask the user (or run them).

Resuming: run `uv run scripts/studio.py status <path>` first. It lists finished and skipped stages, the next one, whether the metadata is still current (`metadata_ready` / `metadata_problem`) and the attempts used per mockup. Skip what's done unless the user asks to redo it.

## Before you start: the global design system

Every job needs `design/global.json` (or the file the brief names on its `Design system:` line). If it's missing, say so at the start and ask the user for one — `design/global.example.json` is a starting point for them to edit. Stages 1–3 can run meanwhile. A per-product `assets/<job>/design.json` is optional; its absence never blocks anything.

## Before you start: check your image tool

Stage 5 needs an image-generation tool in this harness (Codex built-in `image_gen`, or an image MCP tool in Claude Code / OpenCode). For `exact`/`likeness` jobs it must accept reference images. If you have none, say so at the start: stages 1–4 can still run, and rendering resumes once a tool is connected. Don't fall back to writing an API script.

## Checkpoints (pause and ask the user)

Stop and ask at these points unless the user said to run unattended ("autopilot", "don't ask"):

1. **After intake** — if there's no brief or no creative direction, or the fidelity mode is unclear, or real identifiable people are involved and consent isn't stated. Offer to draft a direction from the photos.
2. **After fact-check** — if there are `conflict` results or a required fact is missing (`verify` exits with code 2). Show the short table and ask: provide the value, accept a source, or continue without it.
3. **After design resolution** — if there is no global design file, or an override the user asked for was blocked by a lock.
4. **Before rendering** — show the shot list (one line per shot: purpose, setting, size, text overlay yes/no) and the number of image generations. Get a go-ahead.
5. **When a mockup's attempt budget is used up** — report what keeps failing; only the user can grant another attempt.
6. **Before export** — show which images passed QA and the set verdict.

In autopilot: never invent missing facts, skip shots that depend on unverified facts, never grant yourself extra attempts, a missing global design or missing consent still stops the run, and record every assumption in the QA report.

## Non-negotiables

- The resolved design system is the visual frame; inside it, the user's creative direction leads, in any genre, industry or medium. The genre playbooks and style library are ideas, not rules. If the brief asks for something unusual, do that. If it asks for something the global design locks, say so instead of working around it.
- Everything later stages know about the subject comes from `metadata/product.json`. Only `attributes.verified` are facts; `inferred` values are what the photos show and guide the look only.
- Respect industry compliance (see `product-creative/genres.md`): disclosures, claims, people's consent, rights to logos and characters.
- Never invent facts about the subject. Only `verified` facts may appear in overlays, alt text or listings.
- Facts come from saved sources: you extract them with verbatim quotes, an independent checker re-verifies them, and the scripts decide the status. Your memory is never evidence.
- Never modify anything in `assets/`. Everything goes to `output/<id>/`.
- Don't ask the image tool to render specs, prices or claims as text. Add text with `product-overlay`.
- Respect the fidelity mode: `exact` subjects stay identical (shape, proportions, colours, logo, label, materials); `likeness` subjects stay clearly recognisable. Real logos, UI and artwork are composited, not redrawn.

## Final summary to the user

When done, reply with: the job id, verified / needs-review / conflict / unavailable counts, the design system used and any blocked overrides, the final images (paths) with attempts used, anything blocked and why, and the next action for the user (e.g. "confirm weight with client, then re-run `product-factcheck`").
