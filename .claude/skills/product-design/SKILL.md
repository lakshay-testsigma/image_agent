---
name: product-design
description: Stage 4 for ONE subject (any genre or industry) — resolve the two-level design system (required global design + optional per-product design + what the user asked for this session) with fixed precedence rules, then build and schema-validate the product metadata JSON that every later stage reads. Use when setting up or changing the visual system, the mockup list, or when `status` says design or metadata is missing or stale.
argument-hint: <subject-image-path> [design changes for this session]
---

# Design system → validated product metadata

**Subject:** `$ARGUMENTS`. The first token is the subject image path (or its folder); words after it are design direction for this session. If you see the literal text `$ARGUMENTS`, take them from the user's message. Needs `output/<id>/intake.json` and a finished (or skipped) fact-check.

Nothing is generated here. This stage turns "what should it look like, and how many of what" into two files the scripts can check: `design/design.resolved.json` and `metadata/product.json`. No render is possible without them.

## The three layers

| Layer | File | Who writes it | Required |
|---|---|---|---|
| global | `design/global.json` (or the file named on the brief's `Design system:` line) | the user | **yes**: every job |
| product | `assets/<job>/design.json` (loose photo: `assets/<stem>.design.json`) | the user | no |
| session | `output/<id>/design/session.json` | you, from the user's words only | no |

Shapes: `schemas/design.schema.json` (`global` and `layer`). Start a global file from `design/global.example.json`.

- **No global file:** stop and ask the user for one (offer to copy the example for them to edit). Don't invent a house style and don't write `design/global.json` yourself without their say-so.
- **No product file:** fine. The global design applies unchanged. Never treat this as a blocker.
- **Never edit** `design/global.json` or anything in `assets/` to make a render work.

## Precedence (fixed, applied by the script)

1. Start from the global design.
2. Apply the product layer, then the session layer. Later wins, field by field; objects merge key by key.
3. Paths in the global `locked` list keep the global value. The attempted override is dropped and reported.
4. `must_avoid` and `identity_constraints` only grow. No layer removes an entry.
5. `mockups`: the last layer that defines them replaces the list. None anywhere: one mockup `main`. Each mockup's own `style` applies last.
6. Output aspect and size must agree: changing only the aspect drops the inherited size; changing only the size re-derives the aspect, unless the aspect is locked.
7. A style text that mentions something in `must_avoid` is flagged. `must_avoid` wins.

Above all layers: the subject's facts and identity (verified attributes, `identity_constraints`, the intake preservation checklist). No design layer can change them.

## Steps

1. **Write the session layer, only if the user asked for something.** `output/<id>/design/session.json`, same shape as a product file. Put in it:
   - visual changes the user asked for in this session ("make it moodier", "9:16 story too")
   - the mockup list, when the user named shots in the session, or when the brief's "Deliverables" ask for shots that neither the global nor the product design defines
   - nothing of your own. Concepts, props and stories belong in the shot plan (`product-creative`), inside this frame.
   Mockup names are lowercase slugs (`catalog`, `lifestyle-loft`); they become shot names and folder names.

2. **Resolve.**
   ```bash
   uv run scripts/studio.py design <path>
   ```
   Read the output: `mockups` (name, type, variations, output size), `generations_planned`, `overrides_applied`, `overrides_blocked`, `warnings`.
   - **Blocked override:** tell the user what they asked for is locked by the global design. They decide: live with it, or change `locked` in the global file themselves. Don't work around it in a prompt.
   - **Warning:** follow `must_avoid`; mention the clash to the user.
   - **Error** (schema, contradictory output, duplicate mockup names): fix the session file if it's yours; otherwise show the user the exact message.

3. **Build the metadata.**
   ```bash
   uv run scripts/studio.py metadata <path>
   ```
   Writes `output/<id>/metadata/product.json`, validated against `schemas/product.schema.json`. It refuses when: fact-check is neither done nor skipped; intake says facts are needed but research was skipped; identifiable people without confirmed consent; the design is stale; a verified attribute has no source.

   What's in it:
   - `identification`: name / brand / model, each `verified`, `inferred` or `unknown`
   - `reference_images`: every photo with hash and size
   - `attributes.verified` (with sources and quotes) · `unverified` · `conflicting` · `rejected` · `inferred` (seen in photos; hints only) · `unavailable`
   - `research`: sources and the verification summary, or the skip reason
   - `visual`, `generation_constraints` (fidelity, preservation checklist, identity constraints, avoid list, text policy)
   - `design`: the resolved style, generation budget and the mockups, each with its fully resolved style

4. **Tell the user** the mockup list with sizes, the number of generations, anything blocked or flagged, and any `warnings` from metadata (unavailable required facts, a verified fact that disagrees with the photos).

## When something changes later

`studio.py status <path>` shows `metadata_ready` and `metadata_problem`. Intake, facts, photos or any design layer changed → re-run `design` and/or `metadata`. `preflight`, `register`, `qa-mark` and `export` refuse to run on stale metadata, so there is no way to render from an outdated picture of the product.

To add or change a shot mid-job: edit `session.json` → `design` → `metadata` → write its prompt (`product-creative`).
