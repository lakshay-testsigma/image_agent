---
name: product-render
description: Stage 6 for ONE subject (any genre, industry or medium) — generate images from the shot plan with the harness's own image-generation tool, behind a deterministic preflight gate (valid metadata, planned mockup, attempt budget), attaching the subject photos as references per the fidelity mode, and log every result. Use when the user wants images, mockups, photography, illustrations, ad creatives or renders generated.
argument-hint: <subject-image-path> [shot names]
---

# Render with your own image tool

**Subject:** `$ARGUMENTS`. The first token is the subject image path; further tokens name the shots to render (default: every shot in the plan without an approved render). If you see the literal text `$ARGUMENTS`, take them from the user's message. Needs `output/<id>/metadata/product.json` (current), `creative/shot-plan.md` and `creative/prompts/<shot>.md`; run `product-design` / `product-creative` first if they're missing.

Only planned mockups can be rendered. If the user gives a one-off direction ("just make a quick lifestyle shot in a café"), add that mockup to `output/<id>/design/session.json`, re-run `studio.py design` and `studio.py metadata` (see `product-design`), write its prompt file following `../product-creative/prompting.md`, then render it. That keeps every image traceable to a design decision.

## Which tool

Use the image-generation tool your harness provides (for `exact` / `likeness` jobs, one that takes reference images):
- **Codex:** built-in `image_gen`
- **Claude Code / OpenCode:** an image-generation MCP tool the user has connected (look through your tool list)

If no such tool is available, stop and tell the user. Don't write a script that calls an image API and don't ask for an API key. For `exact` / `likeness` jobs use the tool's edit / image-to-image / reference mode so the real subject is kept. For `inspired` jobs references are optional; for `none` (concept jobs) generate from text plus any style refs.

## Render a shot

1. **Preflight — before every generation, including retries:**
   ```bash
   uv run scripts/studio.py preflight <path> --shot lifestyle                       # all subject photos, primary first
   uv run scripts/studio.py preflight <path> --shot lifestyle --only-primary --with-style-refs --ref assets/<job>/refs/mood.jpg
   uv run scripts/studio.py preflight <path> --shot main --no-product-refs --with-style-refs     # concept jobs only
   ```
   Use the ref flags the shot plan lists for that shot. Preflight stops (`error:`) unless: the metadata is valid and current, the shot is a planned mockup, its prompt file exists, an `exact`/`likeness` job has a subject photo attached, and the mockup still has attempts left. If it stops, fix that cause; don't generate anyway.
   It returns what the image tool needs: `reference_images` (in order), `prompt_file`, `output` (size/aspect), `variations`, `attempt` of `attempts_allowed`, plus the identity constraints and avoid list as a reminder.
2. Call your image tool with the full text of the prompt file as the prompt and those images as references, at the returned size/aspect (closest the tool supports) and number of variations.
3. Log every image it produced (paths where the tool saved them), with the **same ref flags**:
   ```bash
   uv run scripts/studio.py register <path> --shot lifestyle \
     --image /path/from/tool/img-1.png --image /path/from/tool/img-2.png \
     --prompt-file output/<id>/creative/prompts/lifestyle.md \
     --engine "<harness>+<tool name>" --model "<image model if known>" --size 1536x1024
   ```
   This copies them to `output/<id>/renders/<shot>/vN-1.png …` and writes `vN.json` (prompt, engine, model, params, references, attempt number, metadata hash, time). One `register` call is one attempt; it returns `attempts_left`. That's the audit trail, so don't rename files and don't write into `renders/` by hand. If the tool returns an image without saving a file, save it to a scratch path first.

## After each render

1. Open the images and compare them with the subject photos (or, for concept jobs, with the brief). Make a side-by-side sheet if useful:
   ```bash
   uv run scripts/studio.py contact-sheet <path>
   ```
2. If the subject drifted (shape, logo, label, colour, face, architecture) or the image misses the design or the brief, record the failure with `qa-mark` (see `product-qa`; its `next` field says `retry` or `escalate`), adjust the prompt, change one thing at a time, note why in the shot plan, and go back to step 1 of "Render a shot" (the next `register` becomes `vN+1`).
3. **Attempt budget.** Each mockup gets `max_attempts` generations (from the design, default 3). When preflight says the budget is used up, stop and tell the user what keeps going wrong and what you tried. Only if the user asks for another try:
   ```bash
   uv run scripts/studio.py preflight <path> --shot lifestyle --extra-attempt "user: try once more with the label smaller"
   ```
   Never grant yourself an extra attempt, in autopilot either. An image registered past the budget can't be approved.
4. Then go to `product-overlay` (if the shot needs text, logos, a composited screenshot/artwork, or a resize — an image that isn't at the mockup's exact delivery size can't be approved) and `product-qa`.

## Budget

Before a batch, tell the user the number of generations (`generations_planned` from `studio.py design`, i.e. the sum of variations) and get a go-ahead (unless on autopilot). Explore concepts at lower quality/size if the tool offers it; use full quality only for chosen concepts.
