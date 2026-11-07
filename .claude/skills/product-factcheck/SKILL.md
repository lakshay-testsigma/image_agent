---
name: product-factcheck
description: Stage 3 for ONE product — independently verify every researched fact with the FACTCHECK model plus deterministic checks (quote really in source, value in quote, unit-aware conflict detection, variant separation, source tiers), then resolve conflicts with the user. Use when the user wants product details fact-checked or verified.
argument-hint: <product-image-path> [required fact keys]
---

# Product fact-check

**Product:** `$ARGUMENTS` (first token = product image path; any further tokens are fact keys that must end up verified). Needs `research/facts.draft.json`. Run `product-research` first if it's missing.

## 1. Run verification

```bash
uv run scripts/studio.py verify <product-path> --require height,width,depth,material
```
Build `--require` from the brief's "Facts to verify / show" (plus anything the user named), using the snake_case keys from the draft.

What happens to each claim:
1. Deterministic checks: the source exists, the source is about the same product, the extractor's quote really occurs in the saved text, and the value occurs inside that quote.
2. The FACTCHECK model (`FACTCHECK_*` in `.env`, ideally a different model than research) sees the source but **not** the extractor's quote. It must answer supported / contradicted / not_found / ambiguous and give its own evidence quote, and that quote must also be found in the source.
3. Each fact (key + variant) is decided across all sources:
   - `verified`: claims agree, and either an authoritative source (client / manufacturer / gs1) supports it or 2+ independent domains agree
   - `needs_review`: only one secondary source
   - `conflict`: sources disagree and there's no client value
   - `rejected`: nothing survived

Use `--no-model` only for offline dry runs. Then nothing except client facts gets past `needs_review`.

## 2. Read the report

`output/<id>/factcheck/report.md` (human-readable) and `facts.verified.json` (machine-readable).
```bash
uv run scripts/studio.py facts <product-path>          # verified only
uv run scripts/studio.py facts <product-path> --all    # everything
```

## 3. Resolve what's open

- **Conflicts / missing required facts:** first look for a better (authoritative) source: `product-research`, then re-run `extract` and `verify`. If that fails, ask the user. Show the competing values with their sources.
- **Human decisions** get recorded, never edited into the JSON by hand:
  ```bash
  uv run scripts/studio.py override <product-path> --key weight --value 6.2 --unit kg --note "client confirmed by email 2026-11-06"
  uv run scripts/studio.py override <product-path> --key max_load --reject --note "retailer figure, not manufacturer"
  uv run scripts/studio.py verify <product-path> --require ...
  ```
  Never use `override` to make a fact verified on your own judgement. It records a decision the user made.
- Variant safety: a value with a `variant` only applies to that variant. Check that size or colour specific values didn't merge.

## 4. Hand-off

Tell the user the counts and the open items in a short table. Downstream stages use only `verified` facts. `needs_review` facts can be mentioned to the user but must not appear on images or listings.

The verifier instructions are in `prompts/factcheck-verify.md`, and tier/tolerance logic is in `scripts/lib/factcheck.py`. Adjust them if a client needs stricter rules (e.g. require manufacturer source for every number).
