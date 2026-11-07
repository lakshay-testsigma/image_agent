# Writing gpt-image prompts that keep the real product

The render stage sends the product photos as reference images (edit mode, `input_fidelity=high`) along with your prompt file. The model works best with plain, concrete language in roughly this order.

## 1. Say what each image is for
Images are sent in this order: the primary product photo, the other product photos, then extra `--ref` files, then `refs/` (if `--with-style-refs`).

> Image 1–3 show the exact product: a solid white-oak lounge chair with a woven paper-cord seat. Image 4 is a mood reference — borrow only its warm late-afternoon light and muted palette, not its objects.

## 2. Preservation contract (always include, adapt the specifics)
> Keep the product exactly as in the product photos: same shape, proportions, number of parts, materials, colours, finish, stitching, hardware, logo and label text and their positions. Do not redesign, simplify, add or remove any part of the product. The product must look like a real photograph of this exact item.

List the 3–6 most fragile details from the intake preservation checklist ("the tag reads 'NORDIK' in a serif font on the left back leg"). Concrete details hold up better than general reminders.

## 3. Scene, then light, then camera
- **Scene:** surfaces, materials, era, location, props. Choose fewer, more specific props over clutter.
- **Lighting:** source, direction, quality, time of day. For example "large soft window light from camera left, gentle fill, soft contact shadow under the legs".
- **Camera:** angle, height, lens feel, depth of field. For example "eye-level three-quarter view, 50 mm, f/5.6, product fully in frame, sharp".
- **Composition:** where the product sits, and the negative space to leave for a later overlay ("leave the right third empty and calm").
- **Mood / grade:** for example "editorial, quiet, Kinfolk-like, slightly desaturated warm grade".

## 4. Scale from verified facts
> The chair is 85 cm tall with a 45 cm seat height. A 30 cm ceramic vase stands on the floor beside it for scale.

Only use `verified` values here.

## 5. Avoid list
> No extra products, no duplicate chairs, no people, no visible brand names other than the product's own label, no watermarks, no warped geometry.

## 6. Text policy
> Do not add any text, numbers, captions or logos to the image. The only lettering allowed is the product's existing printed label, reproduced exactly.

Specs and copy go on later through `product-overlay`.

## Size / quality cheat-sheet (gpt-image-1)
- `1024x1024` square catalog/social · `1536x1024` landscape banner/lifestyle · `1024x1536` portrait/story/4:5 crop · `auto`
- `--quality high` for finals, `medium`/`low` for fast concept exploration
- `--background transparent` (png/webp) for cut-outs on transparent background
- `--n 2..4` to get variations to choose from (each costs)
- `--mode generate` (no product refs) only for empty background plates or abstract concepts. It doesn't preserve the product.

## Iterating
- Change one thing per retry and keep a note of what changed in the shot plan.
- If the label or logo keeps drifting, try `--only-primary` with the clearest label photo, move the camera so the label is smaller or angled, or plan a composite.
- If colours shift, name the exact colour ("deep forest green, approx #1F3D2B, matte") and reduce coloured light.
- Keep prompts under roughly 250 words. Past that, extra detail starts to compete with itself.
