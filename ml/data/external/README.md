# External scenario preparation

This layer turns external source records into deterministic, Russian-domain scenario facts. It
does not create Gold examples and does not call an LLM. The LLM stage may later verbalize an
approved fact, but it must not invent its labels.

## Data flow

1. Keep downloaded CSV files under `raw/` (Git-ignored).
2. Record source, license, snapshot, size and SHA-256 in `manifests/`.
3. Stream source rows through the source-specific importer.
4. Resolve source concepts through versioned rules in `mappings/`.
5. Aggregate identical semantic combinations and select a category-balanced sample.
6. Replace all source locations with deterministic demo-city locations.
7. Append manually designed edge cases from `ml/configs/external-scenarios.v1.json`.
8. Write `canonical/v1/scenarios.jsonl`, validate it and review it before LLM enrichment.

The committed canonical file contains 181 pre-LLM facts: 100 from SF311 vocabulary, 60 sampled
from the synthetic BMC combinations, and 21 curated safety/OOD facts. Raw data and interim files
remain local.

## Rebuild

```powershell
uv run --locked python -m maxsmartcity.ml.data.external.cli `
  --config ml/configs/external-scenarios.v1.json `
  --taxonomy ml/configs/taxonomy.v1.json `
  --sf311-mapping ml/data/external/mappings/sf311-taxonomy.v1.json `
  --bmc-mapping ml/data/external/mappings/bmc-taxonomy.v1.json `
  --sf311-csv ml/data/external/raw/sf311/SF311_-_Recent_Cases_20260921.csv `
  --bmc-csv ml/data/external/raw/bmc/bmc_train.csv `
  --output-dir ml/data/external/canonical/v1
```

## Ownership / TODO

- **ML now:** source adapters, mappings, canonical facts, review, later prompt/version tracking.
- **ML later:** LLM paraphrases after manual fact approval; Gold annotation and split by scenario.
- **Data ingestion:** provide versioned production exports matching the ingestion contract.
- **Backend:** consume the decision API contract; it should not depend on these preparation files.

Never commit API keys, `.env.local`, downloaded raw files, or unreviewed LLM responses.

## Template-first candidate generation

The preferred pipeline first produces two deterministic Russian seeds for every canonical fact.
It uses Faker/pymorphy3 only for the small local preview; the canonical batch is driven
by versioned templates and explicit overrides for all curated edge cases. Augmentex is not used.

Build the 362 current local seeds without an API call:

```powershell
uv run --locked python -m maxsmartcity.ml.data.template_generation.canonical_cli `
  --config ml/configs/canonical-template-seeds.v1.json `
  --canonical ml/data/external/canonical/v1/scenarios.jsonl `
  --output-dir ml/data/external/interim/canonical-template-seeds-v1
```

Inspect the no-cost plan before execution. The current canonical set produces 181 calls and 362
requested variants:

```powershell
uv run --locked python -m maxsmartcity.ml.data.template_generation.paraphrase_cli `
  --seeds-file ml/data/external/interim/canonical-template-seeds-v1/examples.jsonl `
  --llm-config ml/configs/template-paraphrase.full-v1.json `
  --output-dir ml/data/external/interim/template-paraphrase-full-v1
```

Add `--env-file .env.local --execute` only after reviewing the seeds and a 20-example pilot.
The historical v1 full run completed 180 calls and produced 360 paraphrases for 4.0278 RUB:
353 passed deterministic validation and 7 went to quarantine. The later `thanks-only` negative
scenario was authored locally and did not require another API call. Exact duplicates and semantic
shifts found during review are corrected in `ml/configs/gold-mvp.v1.json`.

## Legacy AI Tunnel lexicalization

The older multi-pass generator is retained for reproducibility of rejected runs. The LLM is a
text lexicalizer, not an annotator: category, subcategory, organization,
severity, clarification and safety signals remain locked canonical facts. Every generated
record is a candidate until a human accepts it into Gold.

Copy `.env.ml.example` to `.env.local` and put the API key there. The local file is ignored by
Git. First inspect a no-cost plan:

```powershell
uv run --locked python -m maxsmartcity.ml.data.llm.cli `
  --config ml/configs/llm-augmentation.v2.json `
  --input ml/data/external/canonical/v1/scenarios.jsonl `
  --output-dir ml/data/external/interim/llm-pilot-v1
```

Execute one curated scenario (three API calls and ten requested variants):

```powershell
uv run --locked python -m maxsmartcity.ml.data.llm.cli `
  --config ml/configs/llm-augmentation.v2.json `
  --input ml/data/external/canonical/v1/scenarios.jsonl `
  --output-dir ml/data/external/interim/llm-pilot-v1 `
  --scenario-id CURATED-water-near-electric-panel `
  --execute
```

The run is resumable. It stores provider responses, deterministic validation results, token
usage and estimated cost under the ignored `interim/` directory. Review `candidates.jsonl` and
`quarantine.jsonl`; neither file is training data yet. Use `--full` only after the pilot has
been reviewed and the canonical facts are approved.

The main v1 batch is a deterministic 60-scenario selection: all 20 curated edge cases, 20 BMC
facts and 20 SF311 facts. External facts are quota-balanced by primary category and sampled
round-robin across subcategories. Rebuild its committed manifest before generation:

```powershell
uv run --locked python -m maxsmartcity.ml.data.llm.selection_cli `
  --config ml/configs/llm-selection.v1.json `
  --input ml/data/external/canonical/v1/scenarios.jsonl `
  --output ml/data/external/selections/llm-batch-v1.json
```

Then use `--selection-file ml/data/external/selections/llm-batch-v1.json` with the lexicalization
CLI. Under the current three-pass configuration this requests 440 candidates in 140 resumable
API calls. Do not use `--full` without inspecting a plan: it requests candidates from the entire
current canonical set.

After generation, create the local human-review queue from automatically accepted candidates:

```powershell
uv run --locked python -m maxsmartcity.ml.data.llm.review_cli `
  --candidates ml/data/external/interim/llm-main-v2/candidates.jsonl `
  --canonical ml/data/external/canonical/v1/scenarios.jsonl `
  --output ml/data/external/interim/llm-main-v2/review.csv
```

Fill `review_decision` with `ACCEPT`, `REJECT` or `EDIT`. Automated acceptance is not Gold:
the reviewer must compare every text with `locked_problem`, location, context and danger fields.
