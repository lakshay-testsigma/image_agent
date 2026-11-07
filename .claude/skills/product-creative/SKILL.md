---
name: product-creative
description: Stage 4 for ONE product — turn the user's creative direction, brand profile, photos and verified facts into a shot plan and one image-generation prompt per shot. Fully open-ended — follows whatever look the user wants. Use when planning mockups, photography concepts, scenes or prompts for a product image.
argument-hint: <product-image-path> [creative direction]
---

# Creative direction → shot plan → prompts

**Product:** `$ARGUMENTS`. The first token is the product image path. Any words after it are creative direction from the user, and they override the brief where the two conflict. If you see the literal text `$ARGUMENTS`, take the path and direction from the user's message.

Inputs to read: `assets/<product>/brief.md`, its brand profile (if referenced), `output/<id>/intake.md`, verified facts (`uv run scripts/studio.py facts <product-path>`), the product photos, and anything in the product's `refs/` folder.

## Priority of intent

1. What the user said in this session
2. The product brief: creative direction, shots wanted, must keep, must avoid
3. The brand profile
4. Your own craft and ideas. [style-inspiration.md](style-inspiration.md) has starting points, which you can mix, twist or ignore.

There are no fixed presets. A luxury watch in a desert at dusk, a mug on a brutalist concrete plinth, a linen shirt mid-jump in Lisbon: if the user wants it, plan it. If the direction is vague, propose 2–3 distinct concepts and ask the user to choose (unless on autopilot).

## 1. Write `output/<id>/creative/shot-plan.md`

Start from [shot-plan-template.md](shot-plan-template.md). For each shot, cover: purpose and channel, aspect/size, concept, scene/set, lighting, camera, composition and negative space, props and people, mood/grade, product preservation notes (from the intake checklist), overlay plan (which verified facts or approved copy, or none), and which reference images go to the model.

Good defaults, which the brief can override:
- If the brief doesn't say otherwise, include at least one **honest catalog shot**: a neutral background, true colours, and the whole product visible. That's the image that shows a customer what they're buying.
- Use **verified dimensions to get scale right**. "The chair is 85 cm tall, seat at 45 cm" tells the model how big the product should look next to props or people.
- Plan text as an **overlay**, never inside the generated scene.
- Fashion on-model: describe the model (or add a model reference in `refs/`) and stress keeping the garment's exact print, cut, seams, colour and logo. Garments need human QA.

## 2. Write one prompt per shot: `output/<id>/creative/prompts/<shot>.md`

The whole file is passed to your image tool as-is, so write only the prompt in it. Follow [prompting.md](prompting.md): say what each reference image is for, then the preservation contract, scene, lighting, camera, composition, mood, the avoid list, and the text policy.

Also note per shot in the plan: size/aspect, number of variations, transparent background or not, and which refs to attach (`--only-primary`, `--with-style-refs`, `--ref <file>`, as used by `studio.py refs` / `register`). The render stage reads these.

## 3. Checkpoint

Show the user a compact shot list and the total number of generations (shots × variations). Ask before rendering, unless on autopilot.

Record completion with `uv run scripts/studio.py status <product-path>`. The shot plan existing counts as creative done.
