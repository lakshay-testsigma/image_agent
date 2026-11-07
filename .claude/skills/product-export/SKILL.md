---
name: product-export
description: Stage 8 for ONE subject — package QA-approved images into output/<id>/final/ with a listing.json (verified facts only, full audit trail of prompts/engines/refs/QA) and optional copy (product description, alt text, captions). Never publishes. Use when the user wants final deliverables, a listing or a hand-off package.
argument-hint: <subject-image-path>
---

# Export approved assets

**Subject:** `$ARGUMENTS` (first token = subject image path; if you see the literal text `$ARGUMENTS`, take it from the user's message).

## 1. Optional: description, alt text, captions

If the user wants listing copy, alt text or social captions, write `output/<id>/final/description.md` using **only verified facts** (`uv run scripts/studio.py facts <path>`) and the brief's tone and brand profile. Claims without a verified fact behind them ("waterproof", "best-selling", "eco") are out unless they're in the brief's approved copy. List any `needs_review` facts you left out so the user knows.

## 2. Export

```bash
uv run scripts/studio.py export <path> --description-file output/<id>/final/description.md
# or pick specific images (each must be QA-approved):
uv run scripts/studio.py export <path> --image output/<id>/renders/catalog-white/v2-1-callouts.png --image ...
```
This copies the images to `output/<id>/final/<id>-<shot>-NN.png` and writes `final/listing.json` with:
- identity and verified facts only (unverified keys go under `excluded_unverified`)
- per image: the source render, engine (which harness + tool made it), model, full prompt, reference images, overlay facts and copy, and the QA verdict
- status `draft — awaiting client approval`

`--force` exports images that haven't passed QA. Use it only when the user explicitly asks, and say so in your summary.

## 3. Hand-off

Tell the user where `final/` is, what's in it, and what's still open (needs-review facts, human-review images). Publishing to Shopify, WooCommerce or a custom store is a separate, user-approved step. Keep products as drafts until the client signs off.
