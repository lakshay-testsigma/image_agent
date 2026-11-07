---
name: product-intake
description: Stage 1 for ONE product — resolve the product image path, create its workspace, read the brief, and study the photos to record identity, visible text, materials and colours. Use when starting work on a product image or when the user asks what a product is.
argument-hint: <product-image-path>
---

# Product intake

**Product:** `$ARGUMENTS` (first token = product image path or folder; ask for it if missing).

## Steps

1. **Init the workspace.**
   ```bash
   uv run scripts/studio.py init <product-path>
   ```
   Output JSON gives `product_id`, all product photos, style refs, the brief path, the workspace, and warnings. If the brief has "Known facts", they're saved as source `S0` (tier `client`).

2. **Read the brief** (`assets/<product>/brief.md`) and the brand profile it points to (if any). The brief is the user's intent: note the creative direction, shots wanted, must-keep, must-avoid, approved copy, and which facts matter.
   - If there's no brief or no creative direction, say so. In an interactive session, ask the user, or offer to draft one from the photos. Don't silently invent a direction.

3. **Study every product photo** (open them, they're images). If `VISION_MODEL` is set you can get a second opinion:
   ```bash
   uv run scripts/studio.py ask --role vision --image <photo> --prompt-file <your-question.md>
   ```
   Record what you can actually see. Don't guess what you can't.

4. **Write `output/<id>/intake.md`** in this shape (add sections freely):

   ```markdown
   # Intake — <product_id>
   ## Identity hypothesis
   - What it is / likely name / brand / model (and confidence + why)
   ## Visible text (verbatim, as printed)
   - "..." (on label / tag / packaging)
   ## Physical observations
   - Shape, construction, materials as they appear, colours (approx hex), finish, hardware, count of parts
   ## Photo set
   - 01-front.jpg: angle, background, lighting, quality issues (blur, crop, reflections)
   ## Preservation checklist (must stay identical in every render)
   - e.g. logo top-left of tag, 4 brass rivets, contrast stitching, matte finish
   ## Research leads
   - Search queries / URLs / barcode to check
   ## From the brief
   - Creative direction summary, shots wanted, constraints, required facts
   ```

   The preservation checklist is used later by QA, so make it concrete.

5. Log completion:
   ```bash
   uv run scripts/studio.py status <product-path>
   ```
   (`intake.md` counts as intake done.)

## Notes

- Visible text and observations are *hints*, not verified facts. Only the fact-check stage produces facts.
- Photo quality problems (low res, harsh glare, cropped product) are worth telling the user about now, since every render inherits them.
