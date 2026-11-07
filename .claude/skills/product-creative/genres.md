# Genre & industry playbooks (starting points, not rules)

Pick the closest row(s), then follow the user's direction. Each entry: default **fidelity**, whether **research** is usually needed, typical shots, what drifts, and compliance cues. Combine entries freely (e.g. a food brand's packaging = Packaging + Food).

Fidelity modes: `exact` (identical subject), `likeness` (clearly the same subject, pose/angle/styling may change), `inspired` (photo is a starting point), `none` (no subject photo, concept from the brief).

---

### Retail products / e-commerce (furniture, homeware, gadgets, toys, tools)
- Fidelity `exact` · research: yes (specs on images / listing)
- Shots: marketplace white, lifestyle in use, scale-with-human, detail macro, infographic with callouts, comparison, what's-in-the-box
- Drifts: proportions, part count, logo, label text, colour under warm light
- Compliance: marketplace main-image rules (pure white, no text, product ≥85% of frame); no implied accessories that aren't included

### Fashion & accessories (apparel, shoes, bags, jewellery, eyewear, watches)
- Fidelity `exact` for the garment/item, `likeness` or `none` for models · research: sizes, materials, care if shown
- Shots: on-model (front/back/3/4/motion), ghost mannequin, flat lay, editorial location, macro of fabric/stone/engraving, on-wrist/on-ear scale
- Drifts: print alignment, seams, hardware, stone count, dial text, metal tone
- Compliance: model diversity per brand; no real-person likeness without permission; always flag garments for human review

### Beauty & personal care (skincare, makeup, fragrance, hair)
- Fidelity `exact` for packaging · research: volume, SPF, key ingredients
- Shots: hero bottle with texture swatches, ingredient still life, water/splash, skin close-up, shelfie, routine flat lay
- Drifts: label text, cap shape, liquid colour, swatch colour vs real shade
- Compliance: no efficacy/medical claims, before/after or "clinically proven" unless in approved copy; don't retouch skin to imply results

### Food & beverage (packaged food, restaurants, menus, drinks, alcohol)
- Fidelity `exact` for packaging, `likeness` for plated dishes · research: nutrition, allergens, volume when shown
- Shots: hero plate, overhead table spread, ingredient deconstruction, pour/splash, steam, menu tiles, delivery-app thumbnails, packaging on shelf
- Drifts: garnish/ingredients not in the dish, portion size, glass/bottle shape, label
- Compliance: don't show ingredients the product doesn't contain; alcohol — no minors, no driving, local rules; "serving suggestion" if styled beyond the product

### Real estate, interiors & architecture
- Fidelity `likeness` (structure must stay; staging/lighting may change) · research: area, bedrooms, address facts if shown
- Shots: virtual staging, day-to-dusk, sky replacement, decluttered room, aerial/context, floor-plan infographic, amenity lifestyle
- Drifts: windows, walls, room size, views, fixtures — never add or remove structural features
- Compliance: virtual staging / renders must be disclosed ("Virtually staged"); no misleading views or space

### Automotive & mobility (cars, bikes, EVs, scooters, boats)
- Fidelity `exact` · research: range, power, 0–100, battery, price-related specs if shown
- Shots: 3/4 front hero, side profile, motion blur road, studio cyclorama, interior/dash, detail (wheels, lights), charging scene
- Drifts: wheel design, badge, light signature, panel lines, number plate (use blank or approved plate)
- Compliance: no unsafe driving; spec claims only verified; regional plate rules

### Tech, electronics & SaaS / apps
- Fidelity `exact` for devices; UI content is **composited**, never generated · research: specs if shown
- Shots: device mockup with real screenshot (generate device with blank/neutral screen, then `overlay` with `corners`), desk setup, feature tiles, dashboard hero, App Store / Play screenshots, launch banner
- Drifts: port layout, camera bump, bezels, UI text (always replace with the real screenshot)
- Compliance: real screenshots only; no fake metrics or logos of customers unless approved

### Healthcare, pharma & wellness
- Fidelity `exact` for packaging, `none` or `likeness` for scenes · research: only approved facts
- Shots: calm lifestyle, clinician/patient scenes, packaging hero, explainer illustrations
- Drifts: packaging text, dosage forms
- Compliance: strict — no therapeutic claims beyond approved copy, required disclaimers via overlay, no real patients without consent, avoid graphic medical imagery unless requested for education

### Finance, insurance, B2B & corporate
- Fidelity `none`/`inspired` usually; `likeness` for team headshots · research: rarely
- Shots: conceptual metaphors, abstract 3D, team portraits, office/culture, report covers, LinkedIn/ads banners, infographic backgrounds
- Compliance: no implied guaranteed returns; disclaimers via overlay; headshots need consent

### People: portraits, headshots, creators, events
- Fidelity `likeness` · research: no (`skip --stage research`)
- Shots: studio headshot, environmental portrait, speaker/event banner, avatar/illustrated version, thumbnail
- Drifts: face identity, skin tone, hair, glasses, tattoos, age
- Compliance: only real people who consented; no sexualised, demeaning or deceptive depictions; no images that could pass as real news/evidence; never depict minors in adult contexts

### Pets & animals
- Fidelity `likeness` · research: usually no
- Shots: studio portrait, adventure scene, illustrated/painted pet, product-with-pet
- Drifts: markings, eye colour, ear shape, breed traits

### Travel, hospitality & places
- Fidelity `likeness` for real locations/hotels · research: amenities, distances if shown
- Shots: hero landscape, room/suite, experience moments, map/illustrated poster, seasonal variants
- Compliance: don't invent views, beaches or amenities a real place doesn't have

### Packaging & label design
- Fidelity `exact` (existing pack) or `inspired` (new concepts) · research: facts printed on pack if shown
- Shots: 3D pack render, shelf/retail context, unboxing, dieline-to-mockup (composite the real label art with `overlay` `corners`)

### Art, illustration & creative merchandise (prints, books, album covers, games, posters)
- Fidelity `exact` when reproducing an artwork (composite it, don't redraw); `inspired`/`none` for new art · research: rarely
- Shots: framed on wall, book/cover mockup, poster in street, merch (tee, mug, tote), key art, character sheets, storyboards
- Compliance: don't imitate a specific living artist's signature style on request without the user owning the rights; no copyrighted characters or logos the user doesn't own

### Events, education, non-profit, government
- Fidelity `none`/`inspired` · research: dates/venues/numbers shown on images must be verified or approved copy
- Shots: posters, social announcements, campaign visuals, explainer illustrations, certificates, slides backgrounds

### Advertising campaigns & social content (any industry)
- Fidelity from the subject · research: any claim, price or stat on the creative
- Shots: ad sets in multiple aspect ratios, carousels, thumbnails, UGC-style, memes, seasonal/holiday variants, A/B concepts
- Compliance: platform ad policies, prices/discounts only from approved copy, "#ad"/disclosures if required

---

## General safety for any genre
- Real, identifiable people only with permission; never deceptive, sexualised, or defamatory depictions; no minors in inappropriate contexts.
- No trademarks, logos, or characters the user doesn't own or have rights to.
- Nothing that could pass as real news, documents, IDs, receipts, or evidence.
- Claims, numbers, prices, and disclaimers: verified facts or approved copy only, drawn by `overlay`.
