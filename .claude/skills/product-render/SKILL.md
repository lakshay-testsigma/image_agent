---
name: product-render
description: Stage 5 for ONE product — generate mockup / product photography from the shot plan with the harness's own image-generation tool, attaching the real product photos as references so the product stays identical, and log every result. Use when the user wants images, mockups or renders generated for a product image.
argument-hint: <product-image-path> [shot names]
---

# Render with your own image tool

**Product:** `$ARGUMENTS`. The first token is the product image path; further tokens name the shots to render (default: every shot in the plan without an approved render). If you see the literal text `$ARGUMENTS`, take them from the user's message. Needs `output/<id>/creative/shot-plan.md` and `creative/prompts/<shot>.md`; run `product-creative` first if they're missing.

If the user gives a one-off direction ("just make a quick lifestyle shot in a café"), you can skip the full plan: write a prompt file under `creative/prompts/` following `../product-creative/prompting.md` and render it.

## Which tool

Use the image-generation tool your harness provides, the one that can take reference images:
- **Codex:** built-in `image_gen`
- **Claude Code / OpenCode:** an image-generation MCP tool the user has connected (look through your tool list)

If no such tool is available, stop and tell the user. Don't write a script that calls an image API and don't ask for an API key. Prefer the tool's edit / image-to-image / reference mode over pure text-to-image so the real product is kept.

## Render a shot

1. Get the reference images in the right order (the prompt describes them in this order):
   ```bash
   uv run scripts/studio.py refs <product-path>                       # all product photos, primary first
   uv run scripts/studio.py refs <product-path> --only-primary --with-style-refs --ref assets/<p>/refs/mood.jpg
   ```
   Use the flags the shot plan lists for that shot.
2. Call your image tool with the full text of `output/<id>/creative/prompts/<shot>.md` as the prompt and those images as references. Use the plan's size/aspect, and the number of variations it asks for.
3. Log every image it produced (paths where the tool saved them), with the **same ref flags**:
   ```bash
   uv run scripts/studio.py register <product-path> --shot lifestyle-loft \
     --image /path/from/tool/img-1.png --image /path/from/tool/img-2.png \
     --prompt-file output/<id>/creative/prompts/lifestyle-loft.md \
     --engine "<harness>+<tool name>" --model "<image model if known>" --size 1536x1024
   ```
   This copies them to `output/<id>/renders/<shot>/vN-1.png …` and writes `vN.json` (prompt, engine, model, params, references, time). That's the audit trail, so don't rename files and don't write into `renders/` by hand. If the tool returns an image without saving a file, save it to a scratch path first.

## After each render

1. Open the images and compare them with the product photos. Make a side-by-side sheet if useful:
   ```bash
   uv run scripts/studio.py contact-sheet <product-path>
   ```
2. If the product drifted (shape, logo, label, colour) or the scene misses the brief, adjust the prompt. Change one thing at a time, note why in the shot plan, and render again (the next `register` becomes `vN+1`). Stop after about 3 tries per shot and report the issue.
3. Then go to `product-overlay` (if the shot needs text) and `product-qa`.

## Budget

Before a batch, tell the user the number of generations (shots × variations) and get a go-ahead (unless on autopilot). Explore concepts at lower quality/size if the tool offers it; use full quality only for chosen concepts.
