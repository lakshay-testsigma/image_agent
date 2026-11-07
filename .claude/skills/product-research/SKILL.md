---
name: product-research
description: Stage 2 for ONE product — find authoritative sources (manufacturer, GS1, distributors), save them as evidence, and have the RESEARCH model (DeepSeek or another open model from .env) extract every product fact with verbatim quotes. Use when the user wants product details / specs found for a product image.
argument-hint: <product-image-path>
---

# Product research

**Product:** `$ARGUMENTS` (first token = product image path; ask if missing). Run `product-intake` first if `output/<id>/intake.md` doesn't exist.

**How it works:** the research model doesn't browse and isn't trusted to remember. You (the agent) find pages and save their text as evidence. The research model then reads each saved source and pulls out facts with quotes. Every fact traces back to a file in `output/<id>/sources/`.

## 1. Find sources (priority order)

| Tier | What | Use as |
|---|---|---|
| `client` | Brief "Known facts" (auto-saved as S0), client spec sheets / PDFs | authoritative |
| `manufacturer` | Official brand product page, manual, spec sheet, datasheet | authoritative |
| `gs1` | Verified by GS1 / GEPIR lookup for the GTIN | authoritative for identity (brand, GTIN, name) |
| `distributor` | Authorised distributor listings | secondary |
| `retailer` | Other retailers | supplementary only |
| `other` | Reviews, forums, blogs | never enough alone |

Search with your own web search tool, or with the configured provider:
```bash
uv run scripts/studio.py search <product-path> "<brand> <model> specifications"
```
Use the intake's research leads: visible label text, model numbers, barcode, brief URLs. Aim for one or two manufacturer or client sources, plus one or two independent secondary sources. Skip pages about a different model or size unless they're clearly labelled.

## 2. Save evidence

```bash
# web page or PDF URL → text (JSON-LD product data is captured too)
uv run scripts/studio.py fetch <product-path> "<url>" --tier manufacturer

# local file from the client (pdf / html / txt / md)
uv run scripts/studio.py add-source <product-path> --file path/to/spec.pdf --tier client

# a page the script couldn't download (bot-blocked): open it with your own web tool,
# save the readable text to a scratch file, then:
uv run scripts/studio.py add-source <product-path> --text-file /path/to/page.txt --url "<url>" --tier retailer --title "<page title>"

uv run scripts/studio.py sources <product-path>      # list what's saved
```
Pick the tier honestly. The tier decides what counts as verified. When saving text by hand, copy the page faithfully: don't summarise or fix anything.

## 3. Extract facts with the research model

```bash
uv run scripts/studio.py extract <product-path>            # all new/changed sources (cached by hash)
uv run scripts/studio.py extract <product-path> --source S3 --force   # redo one source
```
Output: `output/<id>/research/facts.draft.json`. Each fact has key, value, unit, variant, a verbatim quote and a source id, and each source gets a same-product verdict.

## 4. Review the draft

Open `facts.draft.json` and check it against the brief's "Facts to verify / show":
- Are the required facts present? If not, search for more sources and repeat steps 2–3.
- Did a source get `same_product: no`? Its facts will be rejected. Check that this is right.
- Facts are still **unverified**. Don't present them as true yet. Go on to `product-factcheck`.

Optional free-form model help (e.g. to normalise a messy size chart):
```bash
uv run scripts/studio.py ask --role research --prompt-file <question.md> --json
```
Treat its answer as a lead, never as evidence.

## Tuning

The extraction instructions are in `prompts/research-extract.md`. Edit them to add category-specific keys (e.g. `thread_count`, `spf`) or rules. The model and endpoint come from `RESEARCH_*` in `.env`.
