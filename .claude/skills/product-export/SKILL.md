---
name: product-export
description: Stage 9 for ONE subject — package QA-approved images into output/<id>/final/ with a listing.json (verified facts with their sources, full audit trail of prompts/engines/refs/QA) and the product metadata JSON and optional copy (product description, alt text, captions). Never publishes. Use when the user wants final deliverables, a listing or a hand-off package.
argument-hint: <subject-image-path>
---

# Export approved assets

**Subject:** `$ARGUMENTS` (first token = subject image path; if you see the literal text `$ARGUMENTS`, take it from the user's message).

## 1. Optional: description, alt text, captions

If the user wants listing copy, alt text or social captions, write `output/<id>/final/description.md` using **only `attributes.verified`** from `output/<id>/metadata/product.json` and the brief's tone and brand profile. `inferred` attributes (what the photos show) are not facts and don't go in copy. Claims without a verified fact behind them ("waterproof", "best-selling", "eco") are out unless they're in the brief's approved copy. List the `unverified`, `conflicting` and `unavailable` facts you left out so the user knows.

## 2. Export

```bash
uv run scripts/studio.py export <path> --description-file output/<id>/final/description.md
# or pick specific images (each must be QA-approved):
uv run scripts/studio.py export <path> --image output/<id>/renders/catalog-white/v2-1-callouts.png --image ...
```
Export stops (`error:`) when: the metadata is missing or stale; an image isn't approved, or changed after it was reviewed; 2+ images have no passing `qa-set` verdict covering them; a planned mockup has no approved image.

It copies the images to `output/<id>/final/<id>-<shot>-NN.png`, copies the metadata to `final/product.json`, and writes `final/listing.json` with:
- identity (each field marked `verified` / `inferred` / `unknown`) and verified facts, each with its sources and quotes; other keys go under `excluded_unverified`
- the source list and the design system (name, version, layer files and hashes)
- per image: the source render, file hash, its mockup's resolved design, engine (which harness + tool made it), model, attempt number, full prompt, reference images, overlay facts and copy, and the QA entry with its deterministic checks
- the set verdict, `missing_mockups`, and `forced`
- status `draft — awaiting client approval`

`--partial` exports although some planned mockups have no approved image. `--force` exports despite QA problems and records them in the listing. Use either only when the user explicitly asks, and say so in your summary.

## 3. Hand-off

Tell the user where `final/` is, what's in it, and what's still open (needs-review facts, human-review images). Publishing to Shopify, WooCommerce or a custom store is a separate, user-approved step. Keep products as drafts until the client signs off.
