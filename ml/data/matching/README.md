# Report-to-incident matching dataset

`dev-v1` is a deterministic, leakage-safe synthetic benchmark for two different stages:

- candidate retrieval: `corpus.jsonl`, `queries.jsonl`, `qrels.jsonl`;
- incident reranking: `pairs.jsonl` with `MATCH` and `NO_MATCH` labels.

The current build contains 200 incidents, 1,100 report queries, 1,000 positive qrels and 3,000
report/candidate pairs. Splits are assigned by scenario, so reports describing the same synthetic
event cannot leak between train, validation and test.

The incident corpus is deliberately shared across query splits, as it would be in an online search
index. Consequently this is a query-disjoint smoke benchmark, not an incident-disjoint proof of
generalization. The later frozen benchmark must add a time-based or incident-disjoint holdout.

Hard negatives include the same category at a different house and, when available, a different
category at the same house. Reports without a target incident are retained as negative queries for
the `NEW_INCIDENT`/abstain decision.

Rebuild locally:

```powershell
.venv\Scripts\python.exe -m maxsmartcity.ml.data.matching.cli `
  --config ml/configs/matching-dataset.v1.json
```

This data is intentionally marked as synthetic. Before production-like evaluation, backend or
ingestion must export active incident snapshots with canonical `house_id`, timestamps and stable
category codes. The team must then review at least 50–100 real or manually authored multi-report
scenarios, especially false-merge cases.
