---
name: product-factcheck
description: Stage 3 for ONE subject (any industry) — independently verify every researched fact (in a fresh subagent that never saw the extraction) plus deterministic checks (quote really in source, value in quote, unit-aware conflict detection, variant separation, source tiers), then resolve conflicts with the user. Use when the user wants facts about a subject fact-checked or verified.
argument-hint: <subject-image-path> [required fact keys]
---

# Product fact-check

**Subject:** `$ARGUMENTS` (first token = subject image path; further tokens are fact keys that must end up verified). If you see the literal text `$ARGUMENTS`, take them from the user's message. Needs `research/facts.draft.json`; run `product-research` first if it's missing.

## 1. Prepare the claims

```bash
uv run scripts/studio.py verify <path> --prepare
```
This runs the deterministic checks (source exists, same product, the extractor's quote really occurs in the saved text, the value occurs in that quote) and writes `output/<id>/factcheck/claims.json`: every surviving claim, grouped by source, **without the extractor's quotes**.

## 2. Independent check (a fresh checker, not you)

The checker must not see `facts.draft.json`, `research/`, or your reasoning, so it can't just repeat the extraction. Spawn one subagent per source (or one for all):
- **Claude Code:** Agent tool (`general-purpose`)
- **OpenCode:** `task` tool (`general` subagent)
- **Codex / no subagents:** do it yourself in a separate pass, reading only the files below, and set `"checked_by"` to say it was a self-check.

Give it exactly this brief (fill in the paths):

> You are an independent fact-checker. Read `prompts/factcheck-verify.md` and follow it exactly. Check the claims for source `<SID>` listed in `output/<id>/factcheck/claims.json` against `output/<id>/sources/<SID>.txt` ONLY. Do not open any other file in `output/<id>/` and use no memory. Write the JSON result to `output/<id>/factcheck/verdicts-<SID>.json`, with `"checked_by": "<your model name>"`.

## 3. Decide

```bash
uv run scripts/studio.py verify <path> --require height,width,depth,material
```
Build `--require` from the brief's "Facts to verify / show" and `facts_needed.keys` in `intake.json` (plus anything the user named), using the snake_case keys from the draft. `verify` refuses to run if any claim lacks a verdict, or if the draft changed after `--prepare`.

**Exit code 2** means the report was written but a required fact is not verified. That is a checkpoint, not a crash: go to step 5.

Per claim: a `supported` verdict counts only if the checker's own evidence quote is found in the source. Per fact (key + variant) across sources:
- `verified`: claims agree, and either an authoritative source (client / manufacturer / gs1) supports it, or 2+ distributor/retailer sources on different web domains agree
- `needs_review`: weaker support — one secondary source, two pages of the same domain, sources without a URL, or only `other`-tier sources (reviews, forums, sources whose product match is `unclear`) however many
- `conflict`: sources disagree and no single strongest-tier value settles it
- `rejected`: nothing survived

Agreement is strict: numbers must match within 2% after unit conversion; text must contain the same words ("oak" vs "oak veneer" is a conflict, "solid white oak" vs "white oak, solid" is not).

`--deterministic-only` skips step 2 (offline dry runs only). Then nothing except client facts gets past `needs_review`.

## 4. Read the report

`output/<id>/factcheck/report.md` (human-readable) and `facts.verified.json` (machine-readable).
```bash
uv run scripts/studio.py facts <path>          # verified only
uv run scripts/studio.py facts <path> --all    # everything
```

## 5. Resolve what's open

- **Conflicts / missing required facts:** first look for a better (authoritative) source with `product-research`, extract it, then `verify --prepare`, check, `verify`. If that fails, ask the user. Show the competing values with their sources.
- **Human decisions** get recorded, never edited into the JSON by hand:
  ```bash
  uv run scripts/studio.py override <path> --key weight --value 6.2 --unit kg --note "client confirmed by email 2026-11-06"
  uv run scripts/studio.py override <path> --key max_load --reject --note "retailer figure, not manufacturer"
  uv run scripts/studio.py verify <path> --require ...
  ```
  Never use `override` to make a fact verified on your own judgement. It records a decision the user made.
- Variant safety: a value with a `variant` only applies to that variant. Check that size or colour specific values didn't merge.

## 6. Hand-off

Tell the user the counts and the open items in a short table. Downstream stages read facts from `metadata/product.json` (built in `product-design`), where only `verified` facts count; `needs_review` facts are listed as `unverified` and can be mentioned to the user but must not appear on images or listings. Required facts with nothing usable are listed as `unavailable`.

Re-running `verify` after the metadata was built makes the metadata stale — rebuild it with `studio.py metadata <path>`.

Checker rules live in `prompts/factcheck-verify.md`; tier/tolerance logic in `scripts/lib/factcheck.py`. Adjust them if a client needs stricter rules.
