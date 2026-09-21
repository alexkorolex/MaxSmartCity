# Reviewed MVP report dataset v1

This directory contains the first reviewed text dataset for category, clarification and OOD
baselines. It contains 362 texts derived from 181 locked canonical scenarios: one deterministic
template and one selected or manually corrected LLM-assisted lexicalization per scenario.

The dataset is suitable for MVP pipeline and baseline experiments. It is not marked `FROZEN`
because a project member must still provide final human sign-off. It does not contain real
anonymized reports, report-to-Incident reranking pairs or hard negatives.

Files:

- `reports.jsonl` — all 362 reviewed records;
- `train.jsonl`, `validation.jsonl`, `test.jsonl` — deterministic scenario-level splits
  (258/56/48 records); explicit overrides preserve electricity and non-incident coverage;
- `manifest.json` — counts, SHA-256 hashes, source provenance and excluded scope.

All variants of the same `scenario_spec_id` are assigned to the same split. Do not make a new
row-level random split because that would leak near-paraphrases into evaluation.

Rebuild locally from the retained AI Tunnel run:

```powershell
uv run --locked python -m maxsmartcity.ml.data.gold.cli `
  --config ml/configs/gold-mvp.v1.json `
  --taxonomy ml/configs/taxonomy.v1.json `
  --canonical ml/data/external/canonical/v1/scenarios.jsonl `
  --seed-config ml/configs/canonical-template-seeds.v1.json `
  --candidates `
    ml/data/external/interim/template-paraphrase-full-v1/candidates.jsonl `
    ml/data/external/interim/template-paraphrase-full-v1/quarantine.jsonl `
  --output-dir ml/data/gold/v1
```

Manual semantic corrections are versioned in `ml/configs/gold-mvp.v1.json`. The raw API run is
Git-ignored; the reviewed output and its input hashes are committed artifacts.
