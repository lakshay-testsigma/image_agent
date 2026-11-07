---
name: product-qa
description: Stage 7 for ONE subject (any genre or industry) — three-gate quality control of every generated image (factual + compliance, visual fidelity per the job's fidelity mode, creative fit to the brief), with verdicts recorded per image and regeneration requests. Use when reviewing, checking, approving or rejecting generated images, mockups or creatives.
argument-hint: <subject-image-path>
---

# QA — three gates

**Subject:** `$ARGUMENTS` (first token = subject image path; if you see the literal text `$ARGUMENTS`, take it from the user's message).

Inputs: subject photos (none for concept jobs), `output/<id>/intake.md` (fidelity mode, preservation checklist, compliance cues), `creative/shot-plan.md`, `factcheck/facts.verified.json`, every render in `renders/`, and the `.overlay.json` sidecars.

## Prepare

```bash
uv run scripts/studio.py status <path>                 # list renders
uv run scripts/studio.py contact-sheet <path>          # photos + renders side by side → qa/contact-sheet.png
uv run scripts/studio.py inspect output/<id>/renders/*/*.png   # size, aspect, alpha, sharpness
```
Open the contact sheet and each candidate at full size with your file-reading tool. For an independent second opinion, spawn a subagent (Claude Code: Agent tool; OpenCode: `task` tool) that has not seen your verdicts. It's useful for catching what you overlooked, but it doesn't replace your own look. Brief it like this:
> Open `<subject-photo>` (the real subject) and `<render>` (a generated image). The fidelity mode is `<mode>`. List every difference in the subject itself: shape, parts, proportions, colour, logo, label text letter by letter, materials; for people/pets the identifying features; for rooms the structure. Ignore the background and anything the brief asked to change.

## Gate 1: Factual (`--factual pass|fail|na`)
- Every number or claim drawn on the image traces to a **verified** fact. Check the sidecar's `facts_rendered`, and check the value matches the variant.
- Copy text is in the brief verbatim.
- The scene doesn't imply false facts: wrong scale against verified dimensions, a different colour variant, extra included items, certifications or badges that aren't real.
- Industry compliance from the brief and `../product-creative/genres.md`: required disclosures present (e.g. "Virtually staged", disclaimers), no forbidden claims (health, financial, efficacy), no minors/alcohol/unsafe-use issues, no logos, characters or real people without rights or consent, nothing that could pass as real news, documents or evidence.
- `na` if the image has no added text, makes no implicit claims and has no compliance cues.

## Gate 2: Visual fidelity (`--visual pass|fail`)
Judge against the job's fidelity mode, going through the intake preservation checklist item by item:
- **exact:** shape, proportions, part count, hardware; colour, material and finish (view at full size; warm light shifts colour); logo and printed label letter by letter; UI/artwork/labels are the real composited files
- **likeness:** the person/pet/dish/place is clearly recognisable: face shape, skin tone, hair, glasses, markings; room structure, windows and views unchanged; the dish has only its real components
- **inspired:** borrowed elements are there, and nothing the brief forbade crept in
- **none:** the subject matches the brief's description
- Always: artifacts (warped geometry, melted edges, duplicates, extra limbs or fingers, garbled pseudo-text, broken reflections, bad compositing shadows or perspective)
- Fashion: print alignment, seams, cut, drape. People: hands, eyes, teeth. Always flag garments and real people for human review.

A similarity impression is not proof. When in doubt, fail it and say why.

## Gate 3: Creative (`--creative pass|fail`)
- Does it do what the shot plan and brief asked: mood, setting, composition, channel and aspect?
- Does it respect must-avoid?
- Would a professional in that medium (photographer, illustrator, 3D artist, art director) put it in a portfolio? Lighting, realism or stylistic consistency, crop, negative space, legibility at channel size (thumbnails!).
- Does it fit the brand profile?

## Record verdicts (every reviewed image)

```bash
uv run scripts/studio.py qa-mark <path> output/<id>/renders/lifestyle-loft/v2-1.png \
  --factual na --visual pass --creative pass --notes "label crisp; warm grade per brief"
```
An image is approved only when all three gates are `pass` (or `na` for factual).

## Report: `output/<id>/qa/qa-report.md`

Use [qa-report-template.md](qa-report-template.md). For each failed image, write a specific fix for the next render ("label text drifted: 'NORDlK'; retry with --only-primary 02-label.jpg and smaller label in frame"), then hand back to `product-render` or `product-overlay`. Escalate to the user after about 3 failed attempts on a shot. Always list images that need **human review** (fashion fit and drape, real people, regulated industries, high-value items, anything you passed with doubts).
