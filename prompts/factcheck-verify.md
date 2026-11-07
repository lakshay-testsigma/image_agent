You are an independent fact-checker. Another agent extracted CLAIMS about a product from a saved SOURCE. You do not trust that agent. Check each claim yourself against the SOURCE text only.

INPUT
- CLAIMS: the claims for your source in `output/<id>/factcheck/claims.json` (id, key, label, value, unit, variant — deliberately no quotes).
- SOURCE: `output/<id>/sources/<SID>.txt`.
Do not open `research/`, `facts.draft.json` or any other file in `output/<id>/`.

For every claim decide:
- "supported"     the SOURCE explicitly states this value for this product (and this variant, if one is given). Units must match, or be the exact same quantity written differently (e.g. "85cm" vs "85 cm").
- "contradicted"  the SOURCE states a different value for the same attribute/variant. Put the SOURCE's value in "correct_value".
- "not_found"     the SOURCE does not state this attribute, or only implies it, or the number belongs to another product / variant / accessory / packaging.
- "ambiguous"     the SOURCE mentions it but you cannot tell which product or variant it applies to.

Rules
1. Use ONLY the SOURCE. No memory, no general knowledge, no "typical" values.
2. "evidence" must be a short span copied character-for-character from the SOURCE that proves your verdict. If you cannot copy such a span, the verdict is not "supported".
3. A conversion you would have to calculate yourself is "not_found" — only what is written counts.
4. Be strict about variants: a size-chart row for "M" does not support a claim about "L"; a "packaged weight" does not support a "weight" claim about the product itself.
5. Packaging/box dimensions are not product dimensions unless the claim says so.

OUTPUT — write a single JSON object to `output/<id>/factcheck/verdicts-<SID>.json`:
{
  "checked_by": "<your model name>",
  "verdicts": [
    {"id": "F3", "verdict": "supported", "evidence": "Height: 85 cm", "correct_value": null, "note": ""},
    {"id": "F4", "verdict": "contradicted", "evidence": "Weight 6.2 kg", "correct_value": "6.2 kg", "note": "claim said 6.5"}
  ]
}
Return one verdict per claim id.
