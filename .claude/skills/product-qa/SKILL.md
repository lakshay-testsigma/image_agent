---
name: product-qa
description: Stage 7 for ONE product — three-gate quality control of every render (factual, visual fidelity to the real product, creative fit to the brief), with verdicts recorded per image and regeneration requests. Use when reviewing, checking, approving or rejecting generated mockups for a product image.
argument-hint: <product-image-path>
---

# Product QA — three gates

**Product:** `$ARGUMENTS` (first token = product image path).

Inputs: product photos, `output/<id>/intake.md` (preservation checklist), `creative/shot-plan.md`, `factcheck/facts.verified.json`, every render in `renders/`, and the `.overlay.json` sidecars.

## Prepare

```bash
uv run scripts/studio.py status <product-path>                 # list renders
uv run scripts/studio.py contact-sheet <product-path>          # photos + renders side by side → qa/contact-sheet.png
uv run scripts/studio.py inspect output/<id>/renders/*/*.png   # size, aspect, alpha, sharpness
```
Open the contact sheet and each candidate at full size. If `VISION_MODEL` is configured, get an independent second opinion. It's useful for catching what you overlooked, but it doesn't replace your own look:
```bash
uv run scripts/studio.py ask --role vision --image <product-photo> --image <render> \
  --prompt "Image 1 is the real product, image 2 a generated photo. List every difference in the product itself (shape, parts, proportions, colour, logo, label text, materials). Ignore the background." 
```

## Gate 1: Factual (`--factual pass|fail|na`)
- Every number or claim drawn on the image traces to a **verified** fact. Check the sidecar's `facts_rendered`, and check the value matches the variant.
- Copy text is in the brief verbatim.
- The scene doesn't imply false facts: wrong scale against verified dimensions, a different colour variant, extra included items, certifications or badges that aren't real.
- `na` if the image has no added text and makes no implicit claims.

## Gate 2: Visual fidelity (`--visual pass|fail`)
Go through the intake preservation checklist item by item:
- Shape, proportions, part count, hardware
- Colour, material and finish (view at full size; warm lighting can shift colour)
- Logo and printed label: compare the text letter by letter with the product photo
- Artifacts: warped geometry, melted edges, duplicate products, extra limbs or fingers, broken reflections, bad compositing shadows
- Fashion: print alignment, seams, cut, drape plausibility. Always flag garments for human review.

A similarity impression is not proof. When in doubt, fail it and say why.

## Gate 3: Creative (`--creative pass|fail`)
- Does it do what the shot plan and brief asked: mood, setting, composition, channel and aspect?
- Does it respect must-avoid?
- Would a professional photographer or art director be happy putting it in a portfolio? Lighting, realism, crop, negative space.
- Does it fit the brand profile?

## Record verdicts (every reviewed image)

```bash
uv run scripts/studio.py qa-mark <product-path> output/<id>/renders/lifestyle-loft/v2-1.png \
  --factual na --visual pass --creative pass --notes "label crisp; warm grade per brief"
```
An image is approved only when all three gates are `pass` (or `na` for factual).

## Report: `output/<id>/qa/qa-report.md`

Use [qa-report-template.md](qa-report-template.md). For each failed image, write a specific fix for the next render ("label text drifted: 'NORDlK'; retry with --only-primary 02-label.jpg and smaller label in frame"), then hand back to `product-render` or `product-overlay`. Escalate to the user after about 3 failed attempts on a shot. Always list images that need **human review** (fashion fit and drape, high-value items, anything you passed with doubts).
