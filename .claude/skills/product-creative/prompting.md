# Writing image prompts for any subject, genre or medium

The render stage passes the subject photos (if any) and other references to your harness's image tool, together with your prompt file. Image models work best with plain, concrete language in roughly this order.

## 1. Say what each image is for
Images are attached in the order `studio.py refs` prints: the primary subject photo, the other subject photos, then extra `--ref` files, then `refs/` (if `--with-style-refs`).

> Images 1–3 show the exact product: a solid white-oak lounge chair with a woven paper-cord seat. Image 4 is a mood reference — borrow only its warm late-afternoon light and muted palette, not its objects.

> Image 1 is the person to portray. Image 2 is a style reference — borrow only its gouache texture and colour palette.

## 2. Fidelity contract (match the job's fidelity mode)

**exact** (products, packaging, vehicles, devices, artwork):
> Keep the subject exactly as in the reference photos: same shape, proportions, number of parts, materials, colours, finish, hardware, logo and label text and their positions. Do not redesign, simplify, add or remove any part. It must look like a real photograph of this exact item.

**likeness** (people, pets, dishes, rooms, places):
> Keep this person clearly recognisable: same face shape, eyes, nose, skin tone, hair colour and length, glasses, and the small scar above the left eyebrow. Pose, expression, clothing and setting may change as described.

> Keep the room's architecture exactly: walls, windows, doors, ceiling height and floor. Only furniture, decor and lighting change.

**inspired:** say what to borrow and what's free.
> Use the bottle in image 1 as inspiration for the silhouette only; redesign the label and colours freely in an Art Deco style.

**none:** no subject reference. Describe the subject fully and concretely.

In every mode, list the 3–6 most fragile details from the intake checklist. Concrete details hold up better than general reminders.

## 3. Medium and style first
State the medium up front if it isn't a photo: "Flat vector illustration, limited 4-colour palette, subtle grain", "Isometric 3D render, soft clay materials", "35 mm film photograph, Portra 400 grain", "Anime key visual, cel-shaded". With `exact` fidelity in a stylised medium, keep the subject photographic inside the stylised world or plan a composite.

## 4. Scene, then light, then camera
- **Scene:** surfaces, materials, era, location, props. Fewer, more specific props beat clutter.
- **Lighting:** source, direction, quality, time of day ("large soft window light from camera left, gentle fill, soft contact shadow").
- **Camera / viewpoint:** angle, height, lens feel, depth of field ("eye-level three-quarter view, 50 mm, f/5.6, subject fully in frame, sharp"). For illustrations: viewpoint and framing.
- **Composition:** where the subject sits and the negative space to leave for overlays ("leave the top third calm for a headline").
- **Mood / grade:** "editorial, quiet, slightly desaturated warm grade".

## 5. Scale from verified facts
> The chair is 85 cm tall with a 45 cm seat height. A 30 cm ceramic vase stands beside it for scale.

Only use `verified` values here.

## 6. Avoid list
> No extra products, no duplicates, no people, no visible brand names other than the subject's own label, no watermarks, no warped geometry, no extra fingers.

Add the brief's "Must avoid" and the industry's compliance cues from [genres.md](genres.md).

## 7. Text policy
> Do not add any text, numbers, captions or logos to the image. The only lettering allowed is the subject's existing printed label, reproduced exactly.

Headlines, specs, prices, disclaimers, logos and UI screenshots go on later through `product-overlay`. For screens, signs, frames and labels, ask for a **plain, evenly lit blank area** ("the laptop screen is plain mid-grey, straight-on, no reflections") so a real asset can be composited with `corners`.

## Size / variations
- Use the closest aspect your image tool supports (see [formats.md](formats.md)), then crop/pad to exact delivery size with an overlay `canvas`.
- Full quality for finals; lower quality/size for concept exploration, if the tool offers it.
- Transparent background (png/webp) for cut-outs, if the tool supports it.
- 2–4 variations give you a choice.
- Text-to-image without subject references only for `none`/`inspired` jobs, background plates or abstract concepts. It doesn't preserve the subject.

## Iterating
- Change one thing per retry and note what changed in the shot plan.
- If a label, logo or face keeps drifting, attach only the clearest photo (`--only-primary`), make that detail smaller or angled, or plan a composite.
- If colours shift, name the exact colour ("deep forest green, approx #1F3D2B, matte") and reduce coloured light.
- Keep prompts under roughly 250 words. Past that, extra detail starts to compete with itself.
