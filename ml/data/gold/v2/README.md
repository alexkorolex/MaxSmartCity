# Gold v2

Backend-aligned candidate dataset for category classification and routing experiments.

- 522 unique Russian report texts;
- 261 scenario groups (two lexical variants per scenario);
- 482 `ACCEPT`, 26 `NEEDS_CLARIFICATION`, 14 `NON_INCIDENT` records;
- deterministic scenario-level train/validation/test split;
- equal numbers of grounded template and reviewed LLM-assisted texts.

The committed `sources/llm-candidates.jsonl` is the minimal rebuild snapshot. Raw API responses
are intentionally ignored. `sources/api-runs.json` contains non-secret generation audit metadata.

Current status is `REVIEWED_PENDING_TEAM_SIGNOFF`: the data is ready for reproducible local
experiments, but metrics must not be presented as production quality until the team signs off and
adds a frozen set of anonymized real reports. Extraction spans are also not annotated yet.

Train the CPU baseline from the repository root:

```powershell
.\ml\scripts\train_category_baseline.ps1
```

The category loader trains only on `ACCEPT` records with a non-null `primary_category`. Routing
records stay in the dataset for the future routing model.
