---
name: product-research
description: Stage 2 for ONE subject (any industry) — find authoritative sources (manufacturer, brand, official listing, registry, distributors) with your own web tools, save them as evidence, and extract every fact with a verbatim quote. Use when the user wants details / specs / facts found for a subject image, or when images or a listing will show factual claims.
argument-hint: <subject-image-path>
---

# Product research

**Subject:** `$ARGUMENTS` (first token = subject image path). If you see the literal text `$ARGUMENTS`, take the path from the user's message; ask if missing. Run `product-intake` first if `output/<id>/intake.md` doesn't exist.

**Needed only when facts will appear** on images, alt text or a listing (specs, ingredients, nutrition, area, range, prices, dates, awards, certifications). For a portrait, an art piece or a mood campaign with only approved copy, skip it: `uv run scripts/studio.py skip <path> --stage research --reason "..."` (and the same for `factcheck`).

**How it works:** you search the web and save page text as evidence. Then you read each saved source and extract facts with verbatim quotes, following `prompts/research-extract.md`. The scripts store and merge your extractions. Every fact traces back to a file in `output/<id>/sources/`. Nothing comes from memory.

## 1. Find sources (priority order)

| Tier | What | Use as |
|---|---|---|
| `client` | Brief "Known facts" (auto-saved as S0), client spec sheets / PDFs | authoritative |
| `manufacturer` | The subject's official owner: brand product page, manual, spec sheet, menu, official listing, developer, venue, organiser, artist | authoritative |
| `gs1` | Official registries: GS1 / GTIN lookup, land/property register, vehicle type approval, regulator database | authoritative for identity |
| `distributor` | Authorised distributor / agent / official reseller listings | secondary |
| `retailer` | Other retailers | supplementary only |
| `other` | Reviews, forums, blogs | never enough alone |

Search with your harness's web search tool (Claude Code: WebSearch; OpenCode: `websearch`/`webfetch`; Codex: web search). Use the intake's research leads: visible label text, model numbers, barcode, brief URLs. Aim for one or two manufacturer or client sources, plus one or two independent secondary sources. Skip pages about a different model, size, unit or edition unless they're clearly labelled.

## 2. Save evidence

```bash
# web page or PDF URL → text (JSON-LD product data is captured too)
uv run scripts/studio.py fetch <path> "<url>" --tier manufacturer

# local file from the client (pdf / html / txt / md)
uv run scripts/studio.py add-source <path> --file path/to/spec.pdf --tier client

# a page the script couldn't download (bot-blocked): open it with your own web tool,
# save the readable text to a scratch file, then:
uv run scripts/studio.py add-source <path> --text-file /path/to/page.txt --url "<url>" --tier retailer --title "<page title>"

uv run scripts/studio.py sources <path>      # list what's saved
```
Pick the tier honestly. The tier decides what counts as verified. When saving text by hand, copy the page faithfully: don't summarise or fix anything.

## 3. Extract facts (you do this, one source at a time)

For each source listed by `sources` (including `S0`):
1. Read `prompts/research-extract.md` (the rules and output format) and the saved text `output/<id>/sources/<SID>.txt`. Use only that text: identity hints from `intake.md` tell you which product, never what its values are.
2. Write the JSON object to `output/<id>/research/input-<SID>.json`. Quotes must be copied character-for-character from the source file.
3. Store it:
   ```bash
   uv run scripts/studio.py extract <path> --source S1 --input output/<id>/research/input-S1.json --by "<your model name>"
   ```
`extract` with no `--input` just re-merges and lists `pending_sources` (no extraction yet) and `stale_sources` (source text changed — extract again). Output: `output/<id>/research/facts.draft.json`.

Many sources? You may hand each one to a subagent (Claude Code: Agent tool; OpenCode: `task` tool) with the prompt file and source path, and store what it writes.

## 4. Review the draft

Open `facts.draft.json` and check it against the brief's "Facts to verify / show":
- Are the required facts present? If not, search for more sources and repeat steps 2–3.
- Did a source get `same_product: no`? Its facts will be rejected. Check that this is right.
- Facts are still **unverified**. Don't present them as true yet. Go on to `product-factcheck`.

## Tuning

The extraction rules are in `prompts/research-extract.md`. Edit them to add category-specific keys (e.g. `thread_count`, `spf`) or rules.
