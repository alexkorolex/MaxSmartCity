# Evaluation

Training сохраняет все метрики в `metrics.json`. Повторная оценка существующего checkpoint:

```bash
uv run --locked python -m maxsmartcity.ml.evaluation.cli \
  --artifact ml/artifacts/category-tfidf-logreg-v2 \
  --split test \
  --output ml/artifacts/category-tfidf-logreg-v2/test-rerun.json
```

Для категории считаются Macro/Weighted F1, per-class precision/recall/F1, one-vs-rest confusion
matrices, top-1 accuracy, Brier, ECE, coverage, selective accuracy, abstain ratio и risk-coverage.
Также сохраняется majority baseline. Test не используется для выбора threshold.

Отдельные будущие benchmark-наборы:

- retrieval: Recall@K и MRR;
- reranking: Top-K, MRR/NDCG, False Merge/False Split;
- Jev-like: accuracy при coverage, ECE/Brier и risk-coverage;
- stress: throughput, p50/p95, queue drain и RAM/GPU.
