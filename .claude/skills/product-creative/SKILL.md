---
name: product-creative
description: Stage 5 for ONE subject (any genre or industry — product, food, fashion, beauty, real estate, automotive, tech/app, portrait, pet, travel, art, event, ad campaign) — turn the resolved design system, the user's creative direction, brand profile, photos and verified facts into a shot plan and one image-generation prompt per shot, in any medium (photo, 3D, illustration, poster ...). Use when planning mockups, photography concepts, ad creatives, scenes or prompts for an image job.
argument-hint: <subject-image-path> [creative direction]
---

# Creative direction → shot plan → prompts

**Subject:** `$ARGUMENTS`. The first token is the subject image path (or its folder). Any words after it are creative direction from the user, and they override the brief where the two conflict. If you see the literal text `$ARGUMENTS`, take the path and direction from the user's message.

Inputs to read: `output/<id>/metadata/product.json` (the one source for facts, visual traits, constraints and the resolved design; run `product-design` first if `status` says it's missing or stale), the brief (`assets/<job>/brief.md`), its brand profile (if referenced), the subject photos, and anything in the `refs/` folder.

From `product.json` you use: `design.mockups` (the shots to plan — name, type, variations, and each one's fully resolved `style` and `must_avoid`), `generation_constraints` (fidelity, preservation checklist, identity constraints, text policy), `attributes.verified` (the only facts you may state or plan as overlays), `attributes.inferred` and `visual` (what the subject looks like — for describing it, never as claims).

## Priority of intent

1. **Never overridable:** the subject's identity and facts — `generation_constraints.identity_constraints`, the preservation checklist, verified attributes.
2. **The resolved design** (`design` in `product.json`): global design → per-product design → session layer, already merged by fixed rules. Each mockup's `style` and `must_avoid` are binding: lighting, palette, background, composition, camera, output size.
3. **Inside that frame**, for everything the design leaves open (concept, story, props, exact set, mood details): what the user said in this session, then the brief (creative direction, must keep, must avoid, compliance notes), then the brand profile.
4. Your own craft. Idea libraries, all optional: [genres.md](genres.md) (industry playbooks: typical shots, what drifts, compliance), [style-inspiration.md](style-inspiration.md) (looks and mediums), [formats.md](formats.md) (channel sizes)

If the user's direction contradicts the resolved design (a different palette, another aspect, an extra shot), don't bend the prompt: go back to `product-design`, put the change in the session layer and re-resolve. If the global design locks that field, tell the user.

There are no fixed presets and no fixed genre. A luxury watch in a desert at dusk, a ramen bowl as a 90s anime still, a founder headshot as a Swiss poster, a SaaS dashboard on a billboard, an apartment staged in Japandi style, a pet as an oil painting: if the user wants it, plan it. If the direction is vague, propose 2–3 distinct concepts and ask the user to choose (unless on autopilot).

## 1. Decide the fidelity (from intake / brief)

- `exact`: the subject must look identical (products, packaging, vehicles, devices, logos, artwork). Attach the subject photos and write a strict preservation contract. Real UI, artwork, labels and logos are **composited** with `product-overlay` (`corners` for perspective), not redrawn by the image tool.
- `likeness`: clearly the same subject; pose, angle, expression, styling and setting may change (people, pets, dishes, rooms, places). Attach the photos and list the identity traits that must hold.
- `inspired`: the photo is a starting point; reinterpretation, new styles and designs are allowed. Say what to borrow and what's free.
- `none`: concept job with no subject photo. Everything comes from the brief and `refs/`.

## 2. Write `output/<id>/creative/shot-plan.md`

Start from [shot-plan-template.md](shot-plan-template.md). **One shot per mockup in `design.mockups`, with the same name** — no more, no fewer; `preflight` refuses shots that aren't planned mockups. For each shot, cover: purpose and channel, delivery size (see [formats.md](formats.md)), medium/style, concept, scene/set, lighting, camera (or illustration viewpoint), composition and negative space, props and people, mood/grade, fidelity notes (from the intake checklist), overlay/composite plan (verified facts, approved copy, logos, screenshots, or none), and which reference images to attach.

Good defaults, which the brief can override:
- For retail/e-commerce subjects, suggest at least one **honest catalog shot** (neutral background, true colours, whole subject visible) if the mockup list has none.
- Different mockups should differ in something useful (angle, context, crop, use) while sharing the design's light, palette and mood. QA reviews the set for exactly that.
- Use **verified facts to get scale right** ("the chair is 85 cm tall", "the room is 4 × 5 m").
- Plan all text, prices, claims, disclaimers, logos and UI as **overlays**, never inside the generated image.
- Check the matching row in [genres.md](genres.md) for what usually drifts and for industry compliance (disclosures, claims, people's consent), and plan around it.
- One deliverable in several channels? Plan one master image at the largest aspect you need, then crops/canvas variants via overlay — or separate generations if composition must change.

## 3. Write one prompt per shot: `output/<id>/creative/prompts/<shot>.md`

The whole file is passed to your image tool as-is, so write only the prompt in it. The file name is the mockup name. Follow [prompting.md](prompting.md): what each reference image is for, the fidelity contract (identity constraints + the fragile checklist items), medium/style, scene, lighting, camera, composition, mood, the avoid list (the mockup's `must_avoid`), and the text policy.

Size and number of variations come from the mockup (`style.output`, `variations`); don't restate different ones. Note per shot in the plan: transparent background or not, and which refs to attach (`--only-primary`, `--with-style-refs`, `--ref <file>`, `--no-product-refs`, as used by `studio.py preflight` / `register`). The render stage reads these.

## 4. Checkpoint

Show the user a compact shot list and the total number of generations (sum of `variations`; each mockup may be retried up to `design.generation.max_attempts` times). Ask before rendering, unless on autopilot.

The shot plan existing counts as creative done (`uv run scripts/studio.py status <path>`).
