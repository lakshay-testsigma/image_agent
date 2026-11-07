---
name: product-render
description: Stage 5 for ONE product — generate mockup / product photography with the OpenAI image model (gpt-image) from the shot plan, sending the real product photos as references so the product stays identical. Use when the user wants images, mockups or renders generated for a product image.
argument-hint: <product-image-path> [shot names]
---

# Render with OpenAI gpt-image

**Product:** `$ARGUMENTS`. The first token is the product image path. Optional further tokens name the shots to render (default: every shot in the plan without an approved render). Needs `output/<id>/creative/shot-plan.md` and `creative/prompts/<shot>.md`. Run `product-creative` first if they're missing.

If the user gives a one-off direction ("just make a quick lifestyle shot in a café"), you can skip the full plan: write a prompt file under `creative/prompts/` following `../product-creative/prompting.md` and render it.

## Render a shot

```bash
uv run scripts/studio.py render <product-path> --shot lifestyle-loft \
  --prompt-file output/<id>/creative/prompts/lifestyle-loft.md \
  --size 1536x1024 --quality high --n 2
```
Take the flags from the shot plan:
- References: all product photos by default (the primary one first). Use `--only-primary` when one photo shows the needed angle best, `--with-style-refs` to add the product's `refs/` folder, or `--ref <file>` for any extra image (model reference, logo, mood board). The prompt must say what each image is.
- `--mode edit` (default) keeps the real product. `--mode generate` is text-only, for background plates or concept art. Never use it for the product itself.
- `--background transparent` for cut-outs. `--mask <png>` to change only part of an image (transparent pixels = area to repaint).
- `--dry-run` shows the exact request without spending anything. Use it once when unsure.

Each call writes `output/<id>/renders/<shot>/vN-1.png …` and `vN.json`. The JSON records the full prompt, model, params, refs and time. That's the audit trail, so don't rename files.

Defaults (`IMAGE_MODEL`, `IMAGE_SIZE`, `IMAGE_QUALITY`, `IMAGE_INPUT_FIDELITY`) live in `.env`. Override per call with `--model`, `--size`, `--quality`, `--fidelity`.

## After each render

1. Open the images and compare them with the product photos. Make a side-by-side sheet if useful:
   ```bash
   uv run scripts/studio.py contact-sheet <product-path>
   ```
2. If the product drifted (shape, logo, label, colour) or the scene misses the brief, adjust the prompt. Change one thing at a time, note why in the shot plan, and re-render. The new version becomes `vN+1`. Stop after about 3 tries per shot and report the issue instead of burning credits.
3. Then go to `product-overlay` (if the shot needs text) and `product-qa`.

## Codex built-in image generation (no API key)

When running inside Codex, the built-in `image_gen` tool is available, and the user prefers it: generate with the same prompt and reference images, save the result, then log it so QA and export still work:
```bash
uv run scripts/studio.py register <product-path> --shot lifestyle-loft --image <saved.png> \
  --prompt-file output/<id>/creative/prompts/lifestyle-loft.md --engine codex-imagegen
```
Never switch to a paid API fallback without the user's OK.

## Cost discipline

Before a batch, tell the user the number of image calls (shots × n). Use `--quality low` or `medium` for concept exploration, and `high` only for chosen concepts.
