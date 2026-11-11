# Shot plan — <job_id>

**Subject & industry:** <e.g. stoneware mug · homeware / founder portrait · B2B SaaS / 2-bed flat · real estate>
**Fidelity:** exact | likeness | inspired | none
**Direction in one line:** <the concept that ties the set together>
**Design system:** <design.name + version> · layers used: global [+ product] [+ session] · blocked overrides: <none | list>
**Source of direction (inside the design):** session / brief / brand profile / proposed by agent (approved by user? y/n)
**Identity constraints:** <from product.json generation_constraints — never overridable>
**Preservation checklist:** <from product.json — what must stay identical / recognisable>
**Verified facts available for overlays/scale:** <key: value, ... | none (research skipped: reason)>
**Not usable (unverified / conflicting / unavailable):** <keys | none>
**Compliance notes:** <from brief + genres.md, e.g. "label virtual staging", "no health claims">

---

## Shot: <mockup name from design.mockups>   (must match exactly, e.g. catalog, lifestyle, story)
- **Purpose / channel:** e.g. Amazon main / Instagram 4:5 / YouTube thumbnail / A3 print / website hero
- **Delivery size:** <mockup style.output, e.g. 1080×1350> (generate at the closest aspect, then overlay canvas) · variations: <mockup variations> · transparent bg: no
- **From the design (binding):** lighting / background / palette / composition / camera as resolved for this mockup
- **What makes this shot different from the others:** angle / context / crop / use
- **Medium / style:** e.g. studio photo / 3D render / flat vector / watercolour / anime key visual
- **References attached:** all subject photos | `--only-primary` | `--with-style-refs` | `--ref assets/<job>/refs/mood.jpg` | `--no-product-refs` (flags for `studio.py preflight` / `register`)
- **Concept:** one or two sentences
- **Set / environment:**
- **Lighting:**
- **Camera / viewpoint:** angle, lens feel (e.g. 85 mm, f/4), height, distance
- **Composition:** subject placement, crop, negative space (leave room where overlays go)
- **Props / people:**
- **Mood / colour grade:**
- **Scale cue:** how verified dimensions should read in the frame (if relevant)
- **Overlay / composite plan:** none | facts: height, width | copy: "<approved copy>" | logo file | screenshot into screen via `corners` | canvas resize to delivery size
- **Risks to watch in QA:** e.g. label text, face likeness, wheel design, UI blank area, colour shift
- **Prompt file:** `creative/prompts/<shot-name>.md`

## Shot: ...
