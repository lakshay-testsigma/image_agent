---
name: product-intake
description: Stage 1 for ONE subject (any genre or industry) — resolve the image path, create the workspace, read the brief, study the photos, and record subject type, industry, fidelity mode, identity, visible text, materials and colours as a schema-validated intake.json. Use when starting work on an image job or when the user asks what a subject is.
argument-hint: <subject-image-path>
---

# Intake

**Subject:** `$ARGUMENTS` (first token = subject image path or folder). If you see the literal text `$ARGUMENTS`, take the path from the user's message; ask for it if missing.

## Steps

1. **Init the workspace.**
   ```bash
   uv run scripts/studio.py init <path>
   ```
   Output JSON gives `product_id` (the job id), all subject photos, style refs, the brief path, the workspace, and warnings. If the brief has "Known facts", they're saved as source `S0` (tier `client`). A folder with a brief but no subject photo is a **concept job**.

2. **Read the brief** (`assets/<job>/brief.md`) and the brand profile it points to (if any). The brief is the user's intent: subject, industry, fidelity, creative direction, visual style, deliverables, must-keep, must-avoid, approved copy, compliance notes, and which facts matter.
   - If there's no brief or no creative direction, say so. In an interactive session, ask the user, or offer to draft one from the photos. Don't silently invent a direction.

3. **Study every subject photo**: open each image file with your file-reading tool and look at it yourself. For a second opinion, hand the photos to a subagent (Claude Code: Agent tool; OpenCode: `task` tool) and ask it to list what it sees. Record only what you can actually see.

4. **Classify the job.**
   - **Subject type and industry** (product, food, fashion, beauty, property, vehicle, device/app, person, pet, place, artwork, packaging, event, campaign ...). Open `.claude/skills/product-creative/genres.md` and note the closest playbook(s).
   - **Fidelity**: `exact` | `likeness` | `inspired` | `none`. Use the brief's choice; otherwise propose the playbook default and confirm with the user (unless on autopilot, then record the assumption).
   - **Facts needed?** Will any factual claim (specs, numbers, ingredients, prices, dates) appear on images or in a listing? If not, research and fact-check can be skipped (see `product-studio`).
   - **People:** if real, identifiable people are in the photos and the brief doesn't confirm their consent, ask before going further.

5. **Write `output/<id>/intake.json`** (shape: `schemas/intake.schema.json`; unknown keys are rejected, so check the schema rather than guessing):

   ```json
   {
     "subject": {"type": "product", "category": "furniture / lounge chair", "industry": "homeware", "playbooks": ["Retail products / e-commerce"]},
     "fidelity": {"mode": "exact", "source": "brief"},
     "facts_needed": {"needed": true, "keys": ["height", "material"], "reason": "spec callouts on the catalog image"},
     "identity": {"name": "Nordlys lounge chair", "brand": "Nordlys", "model": null, "identifiers": {"sku": "NL-204"},
                  "confidence": "medium", "basis": "brand tag under the seat; model not visible"},
     "visible_text": [{"text": "NORDLYS", "location": "woven tag, rear left leg"}],
     "visual": {
       "shape": "low lounge chair, curved arms, tapered legs",
       "construction": "mortise joints, woven seat",
       "materials": ["oak", "paper cord"],
       "colors": [{"name": "natural oak", "hex": "#C9A46B", "where": "frame"}],
       "finish": "matte oil",
       "parts": ["4 legs", "2 arms", "woven seat"],
       "distinguishing_features": ["visible joint at the arm", "three-strand weave"],
       "extra": {"hardware": "none visible"}
     },
     "photos": [{"file": "01-front.jpg", "angle": "front three-quarter", "background": "grey wall", "lighting": "window light", "issues": "slight glare on the arm"}],
     "preservation_checklist": ["curved arm profile", "woven paper-cord seat, three-strand pattern", "four tapered legs", "tag on rear left leg"],
     "compliance_cues": ["no health claims"],
     "people": {"identifiable": false, "consent": "not_applicable"},
     "research_leads": ["\"Nordlys\" lounge chair NL-204", "https://..."],
     "direction": {"summary": "calm Scandinavian studio set", "deliverables": ["1 catalog 1:1", "1 lifestyle 4:5"], "constraints": ["no plants"]}
   }
   ```

   - `visual.extra` takes any category-specific observation (neckline, screen bezel, label layout, facade material ...), so the same shape works for every kind of subject.
   - `identity` is a hypothesis with a confidence, not a fact. `null` for what you can't tell.
   - `facts_needed.keys` uses the snake_case keys from `prompts/research-extract.md`.
   - `people.consent`: `confirmed` only if the brief or the user says so; `not_confirmed` blocks the job at the metadata stage.
   - The preservation checklist is checked item by item in QA, so make it concrete. For concept jobs, write what the brief says the subject must be.

6. **Validate it.**
   ```bash
   uv run scripts/studio.py intake <path>
   ```
   This checks the schema plus the rules a schema can't express (`exact`/`likeness` needs photos and a checklist; every file under `photos` must be a real subject photo), then writes the readable view `intake.md`. Fix every error it lists and re-run. Act on its `warnings` (undescribed photos, missing consent, no fact keys).

7. Check progress:
   ```bash
   uv run scripts/studio.py status <path>
   ```

## Notes

- Visible text and observations are *hints*, not verified facts. Only the fact-check stage produces facts. In the product metadata they appear as `inferred`.
- `intake.json` is the source of truth; `intake.md` is generated from it. To change the intake later, edit the JSON and re-run `studio.py intake` (the metadata then needs rebuilding — `status` tells you).
- Tell the user about photo quality problems (low res, harsh glare, cropped subject) now, since every generation inherits them.
- Files in `refs/` are style references, never the subject.
