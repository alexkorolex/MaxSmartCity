# Canonical external scenarios v1 — pre-LLM review

Review date: 2026-09-21  
Dataset SHA-256: `8c77892bbb977e1e79a2b6099712d7a747271d8698964ea4e54f34ce993c4b2c`  
Decision: **accepted as input facts for LLM enrichment, not accepted as Gold**

## Scope

A deterministic, source-stratified sample of 100 unique facts was inspected: 40 of 100 SF311
facts, 40 of 60 BMC facts, and all 20 curated edge cases. The evenly spaced sample was taken from
each source after sorting by `scenario_spec_id`; it therefore does not depend on row order.

Automated checks cover all 180 facts:

- 180 unique `scenario_spec_id` values;
- only category IDs present in `taxonomy.v1.json`;
- every location is synthetic and belongs to `demo-city`;
- no source address columns are included in the canonical records;
- the file contains exactly 100 SF311, 60 BMC and 20 curated facts;
- all 13 BMC category rules are exercised;
- all 21 included SF311 mapping rules are exercised.

Source coverage measured before sampling:

| Source | Rows | Unique semantic keys | Mapped rows | Unmapped rows |
| --- | ---: | ---: | ---: | ---: |
| SF311 snapshot | 6,759 | 437 | 4,494 | 2,265 |
| BMC synthetic table | 960,000 | 1,871 | 960,000 | 0 |

The 2,265 omitted SF311 rows are deliberate: their source categories are outside the current
Smart City taxonomy (for example encampments, transport feedback, abandoned vehicles and permit
applications). They must not silently become `other`; adding one requires a reviewed mapping rule.

## Semantic findings

1. SF311 is useful as controlled vocabulary, not as Russian resident text. `TYPE` and `DETAILS`
   must be supplied to the later lexicalization prompt together with the normalized fact.
2. BMC adds property/channel/severity combinations, but its rows are synthetic and repetitive.
   They provide scenario structure, never evidence of real-world frequency or model quality.
3. `other` currently contains noise, air pollution, stray animals and public-health edge cases.
   This is acceptable for v1 only; the product/domain team should decide whether these become
   stable taxonomy categories before Gold annotation.
4. Emergency and multi-label behavior is intentionally concentrated in the 20 curated facts.
   External source mappings must not infer emergency status merely from severity wording.
5. The source descriptions are intentionally neutral and fact-like. Natural style, typos,
   ambiguity and paraphrases belong to the later LLM stage and must retain the locked labels.

## Gate for the next stage

Before an API run, a human should approve the taxonomy edge cases and the 20 curated facts. The
LLM output then needs schema validation, factual consistency checks, deduplication, scenario-level
splitting and a separate human Gold pass. The current review is a preparation audit, not an
annotation sign-off.
