---
name: product-intake
description: Stage 1 for ONE subject (any genre or industry) — resolve the image path, create the workspace, read the brief, study the photos, and record subject type, industry, fidelity mode, identity, visible text, materials and colours. Use when starting work on an image job or when the user asks what a subject is.
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

5. **Write `output/<id>/intake.md`** in this shape (add sections freely):

   ```markdown
   # Intake — <job_id>
   ## Job
   - Subject type / industry / playbook(s) from genres.md
   - Fidelity: exact | likeness | inspired | none (source: brief / user / assumed)
   - Facts needed: yes (which) | no (why)
   - Deliverables / channels / medium (from brief)
   ## Identity hypothesis
   - What it is / name / brand / model (confidence + why)
   ## Visible text (verbatim, as printed)
   - "..." (on label / tag / packaging / sign / screen)
   ## Physical observations
   - Shape, construction, materials, colours (approx hex), finish, hardware, part count
   - People/pets: distinguishing features (face shape, hair, skin tone, glasses, markings)
   - Places/rooms: structure (walls, windows, doors, views)
   ## Photo set
   - 01-front.jpg: angle, background, lighting, quality issues (blur, crop, reflections)
   ## Preservation checklist (must stay identical / recognisable in every image)
   - e.g. logo top-left of tag, 4 brass rivets / round tortoiseshell glasses / bay window on the left
   ## Compliance cues
   - From the brief and the genre playbook
   ## Research leads
   - Search queries / URLs / barcode to check (or "none — no facts needed")
   ## From the brief
   - Creative direction summary, shots wanted, constraints, required facts
   ```

   The preservation checklist is used later by QA, so make it concrete. For concept jobs, write what the brief says the subject must be.

6. Check progress:
   ```bash
   uv run scripts/studio.py status <path>
   ```
   (`intake.md` existing counts as intake done.)

## Notes

- Visible text and observations are *hints*, not verified facts. Only the fact-check stage produces facts.
- Tell the user about photo quality problems (low res, harsh glare, cropped subject) now, since every generation inherits them.
- Files in `refs/` are style references, never the subject.
