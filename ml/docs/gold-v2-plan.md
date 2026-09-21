# Gold v2: backend-aligned generation plan

## Why v1 is not the final Gold

Backend stores zero or one `ProblemCategory` on a report. `NEEDS_CLARIFICATION` is a report status,
while danger flags and extracted features have their own fields. Gold v1 mixed these concerns in a
single label list, so it remains a useful pipeline smoke dataset but must not be frozen as the final
category benchmark.

Gold v2 uses four independent targets:

1. `primary_category`: one of the eight codes in `taxonomy.backend-aligned.v2.json`, or null when the
   routing outcome prevents classification;
2. `routing_outcome`: `ACCEPT`, `NEEDS_CLARIFICATION`, `NON_INCIDENT` or `ABSTAIN`;
3. `danger_signals`: a multi-label list;
4. observable extraction fields such as raw address, entrance, floor, duration, scale and
   `problem_continues`.

## Implemented size and provenance

| Slice | Current result | How it is produced |
|---|---:|---|
| Full Gold v2 candidate | 261 scenarios / 522 texts | grounded template plus one reviewed controlled LLM paraphrase |
| Accepted category records | 241 scenarios / 482 texts | eight backend-aligned primary categories |
| Routing cases | 20 scenarios / 40 texts | 26 clarification and 14 non-incident messages |
| Frozen real/OOD test | not collected | team-authored or anonymized real reports; no sibling paraphrases in train |

The generated target was reduced after review: 522 clean texts are preferable to padding the set
with low-value paraphrases. The remaining priority is 80–120 independent real/OOD texts, not more
siblings of the same synthetic scenarios. Class balance is enforced by scenario.

## API policy

- Accepted generation model: `mistral-medium-3-5` through AITUNNEL. Small/Qwen pilot outputs were
  not selected.
- Temperature: `0.25` for fact-preserving lexicalization. Diversity comes from seed frames and
  explicit style, not high-temperature improvisation.
- One API call returns exactly two variants (`neutral`, `natural`), both schema validated.
- Emoji, slang, invented urgency, organizations, time, address and danger facts are rejected.
- First run a 20-scenario pilot. Continue only if factual preservation is at least 95% after manual
  review and no systematic style defect is observed.
- API outputs are candidates, never Gold. Accepted records retain prompt/model/version provenance;
  rejected records stay quarantined.

At the price recorded on 2026-09-21 (30 ₽ input and 120 ₽ output per 1M tokens), even a conservative
100k input + 100k output budget costs about 15 ₽. The 300 ₽ balance is therefore ample; quality and
review time, not token cost, are the limiting factors.

## Completed gate and remaining freeze gate

The controlled run and semantic review are complete. Before declaring the dataset `FROZEN`:

1. backend/team approves the same eight stable `ProblemCategory.code` values;
2. a human-authored/anonymized frozen test is separated before further model selection;
3. extraction targets receive their own annotation pass.

The rebuild snapshot and non-secret API audit live under `ml/data/gold/v2/sources`. The key remains
only in `.env.local`; neither plans nor manifests contain it.
