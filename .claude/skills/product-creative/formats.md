# Formats & channel sizes

Generate at the closest size/aspect your image tool supports, then use `overlay` with a `canvas` block to reach the exact delivery size (`base_fit: cover` crops to fill, `contain` pads with `fill`). Keep important content inside the safe zone. Platform specs change; check the platform if exactness matters.

| Channel | Size (px) | Aspect | Notes |
|---|---|---|---|
| Amazon / marketplace main | 2000×2000 | 1:1 | pure white #FFFFFF, product ≈85% of frame, no text |
| Shopify / PDP gallery | 2048×2048 | 1:1 | consistent across the set |
| Instagram feed | 1080×1350 | 4:5 | also 1080×1080 |
| Instagram / TikTok / Reels / Shorts | 1080×1920 | 9:16 | keep top 250 px and bottom 340 px clear of key content |
| Facebook / LinkedIn link image | 1200×628 | 1.91:1 | |
| LinkedIn / X banner | 1584×396 / 1500×500 | 4:1 / 3:1 | profile photo covers lower-left |
| YouTube thumbnail | 1280×720 | 16:9 | big subject, ≤4 words of approved copy |
| Pinterest | 1000×1500 | 2:3 | |
| Website hero | 2560×1080 / 1920×1080 | 21:9 / 16:9 | leave text-safe side |
| Email header | 1200×600 | 2:1 | |
| App Store screenshot | 1290×2796 | ~9:19.5 | composite real UI |
| Google Play feature graphic | 1024×500 | ~2:1 | |
| Display ads | 300×250, 728×90, 160×600, 320×50 | — | generate wide, crop per slot |
| Print A4 / A3 poster (300 dpi) | 2480×3508 / 3508×4961 | ~1:1.41 | upscale with your image tool if it can; add 3 mm bleed |
| Presentation slide | 1920×1080 | 16:9 | |
| Avatar / profile | 1024×1024 | 1:1 | circle-safe centre |

Aspect cheat-sheet for prompts: square 1:1 · portrait 4:5 / 2:3 / 9:16 · landscape 3:2 / 16:9 / 21:9.
