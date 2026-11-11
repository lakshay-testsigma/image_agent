---
name: product-qa
description: Stage 8 for ONE subject (any genre or industry) — quality control of every generated image: deterministic checks (delivery size, attempt budget, references, drawn facts) plus three judgement gates (factual + compliance, visual fidelity per the job's fidelity mode, creative fit to the design and brief), a set-level consistency verdict, and controlled retries. Use when reviewing, checking, approving or rejecting generated images, mockups or creatives.
argument-hint: <subject-image-path>
---

# QA — deterministic checks, three gates, one set verdict

**Subject:** `$ARGUMENTS` (first token = subject image path; if you see the literal text `$ARGUMENTS`, take it from the user's message).

Inputs: subject photos (none for concept jobs), `output/<id>/metadata/product.json` (fidelity mode, preservation checklist, identity constraints, verified attributes, each mockup's resolved style and avoid list), `creative/shot-plan.md`, every render in `renders/`, and the `.overlay.json` sidecars.

Review the **final candidate** of each shot: the overlay output if the shot has one, else the render.

## What the script checks for you

`qa-mark` runs these itself and an image can't be approved while one fails, whatever your gates say:

| Check | Fails when | Fix |
|---|---|---|
| `planned_mockup` | the shot isn't in the resolved design | add it via `product-design` |
| `delivery_size` | pixels ≠ the mockup's width × height (or aspect, if no size is set) | overlay `canvas` at the delivery size |
| `attempt_budget` | generated past the budget without the user's go-ahead | escalate to the user |
| `subject_reference` | an `exact`/`likeness` render was made with no subject photo attached | render again with references |
| `overlay_facts` | a drawn fact no longer equals its verified value | re-run `overlay` |

Don't spend judgement on these. Spend it on the gates below.

## Prepare

```bash
uv run scripts/studio.py status <path>                 # list renders
uv run scripts/studio.py contact-sheet <path>          # photos + renders side by side → qa/contact-sheet.png
uv run scripts/studio.py inspect output/<id>/renders/*/*.png   # size, aspect, alpha, sharpness
```
Open the contact sheet and each candidate at full size with your file-reading tool. For an independent second opinion, spawn a subagent (Claude Code: Agent tool; OpenCode: `task` tool) that has not seen your verdicts. It's useful for catching what you overlooked, but it doesn't replace your own look. Brief it like this:
> Open `<subject-photo>` (the real subject) and `<render>` (a generated image). The fidelity mode is `<mode>`. List every difference in the subject itself: shape, parts, proportions, colour, logo, label text letter by letter, materials; for people/pets the identifying features; for rooms the structure. Ignore the background and anything the brief asked to change.

## Gate 1: Factual (`--factual pass|fail|na`)
- Every number or claim drawn on the image traces to a **verified** attribute. Check the sidecar's `facts_rendered`, and check the value matches the variant.
- Copy text is approved copy (the overlay guard enforces the wording; you check it suits this image and channel).
- The image tool added no text, numbers or logos of its own (garbled pseudo-text, invented badges, spec-like digits).
- The scene doesn't imply false facts: wrong scale against verified dimensions, a different colour variant, extra included items, certifications or badges that aren't real.
- Industry compliance from the brief and `../product-creative/genres.md`: required disclosures present (e.g. "Virtually staged", disclaimers), no forbidden claims (health, financial, efficacy), no minors/alcohol/unsafe-use issues, no logos, characters or real people without rights or consent, nothing that could pass as real news, documents or evidence.
- `na` only if the image has no added text, makes no implicit claims and has no compliance cues. The script refuses `na` when facts or copy were drawn.

## Gate 2: Visual fidelity (`--visual pass|fail`)
Judge against the job's fidelity mode, going through the preservation checklist and the identity constraints item by item:
- **exact:** shape, proportions, part count, hardware; colour, material and finish (view at full size; warm light shifts colour); logo and printed label letter by letter; UI/artwork/labels are the real composited files
- **likeness:** the person/pet/dish/place is clearly recognisable: face shape, skin tone, hair, glasses, markings; room structure, windows and views unchanged; the dish has only its real components
- **inspired:** borrowed elements are there, and nothing the brief forbade crept in
- **none:** the subject matches the brief's description
- Always: artifacts (warped geometry, melted edges, duplicates, extra limbs or fingers, garbled pseudo-text, broken reflections, bad compositing shadows or perspective)
- Fashion: print alignment, seams, cut, drape. People: hands, eyes, teeth. Always flag garments and real people for human review.

A similarity impression is not proof. When in doubt, fail it and say why.

## Gate 3: Creative (`--creative pass|fail`)
- Does it follow the mockup's resolved design: lighting, palette, background, composition, camera, mood?
- Does it do what the shot plan and brief asked inside that design?
- Does it respect the mockup's `must_avoid`?
- Would a professional in that medium (photographer, illustrator, 3D artist, art director) put it in a portfolio? Lighting, realism or stylistic consistency, crop, negative space, legibility at channel size (thumbnails!).
- Does it fit the brand profile?

## Record verdicts (every reviewed image)

```bash
uv run scripts/studio.py qa-mark <path> output/<id>/renders/lifestyle-loft/v2-1.png \
  --factual na --visual pass --creative pass --notes "label crisp; warm grade per brief"
```
An image is approved only when all three gates are `pass` (or `na` for factual) **and** every deterministic check passes. The output shows `checks`, `blocked_by`, and `next`:
- `approved`
- `gates passed but deterministic checks failed — fix: ...` → do the fix (usually an overlay `canvas`), then mark the new file
- `retry: ...` → hand back to `product-render` with one specific change
- `escalate: ...` → the attempt budget is used up; report to the user, don't render again

The approval is bound to the file's hash. If the file changes afterwards (overlay re-run, re-render), mark it again.

## Set verdict (when 2+ images are approved)

Open the approved images together (`contact-sheet`) and judge the set, not the single images:
- **Consistent:** same design system across all of them — light direction and quality, palette, grade, background family, the subject's colour and scale reading the same everywhere.
- **Useful variation:** each mockup adds something (angle, context, crop, use); no near-duplicates.
- **Same subject:** the product is recognisably the same object in every image (no variant drift between shots).

```bash
uv run scripts/studio.py qa-set <path> --consistency pass --notes "same key light and warm grade; catalog front, lifestyle three-quarter in use"
```
On `fail`, say which image is the outlier and send that one back to render. Export of 2+ images needs a `pass` that covers exactly the images being exported, so re-run `qa-set` after any image is replaced.

## Report: `output/<id>/qa/qa-report.md`

Use [qa-report-template.md](qa-report-template.md). For each failed image, write a specific fix for the next render ("label text drifted: 'NORDlK'; retry with --only-primary 02-label.jpg and smaller label in frame"), then hand back to `product-render` or `product-overlay`. Escalate to the user when `qa-mark` says `escalate` (attempt budget used up). Always list images that need **human review** (fashion fit and drape, real people, regulated industries, high-value items, anything you passed with doubts).
