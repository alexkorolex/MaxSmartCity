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

## Воспроизводимые benchmark-прогоны без изменения datasets

Rule-based incident ranking на существующем `matching/dev-v1`:

```bash
uv run python -m maxsmartcity.ml.evaluation.benchmark_cli \
  --output ml/evaluation/results/rule-matching-dev-v1.json \
  matching
```

Mass-outage stress test запущенного ML-сервиса. 10 000 обращений генерируются
детерминированно в памяти и не записываются в dataset:

```bash
uv run python -m maxsmartcity.ml.evaluation.benchmark_cli \
  --output ml/evaluation/results/stress-mass-outage-v1.json \
  stress --base-url http://127.0.0.1:8001 --reports 10000 --batch-size 256
```

Отчёт фиксирует throughput, p50/p95 batch latency, HTTP/model errors, top-1 accuracy и
abstain ratio. Synthetic quality metrics нельзя интерпретировать как качество на реальных
обращениях; они нужны для регрессии производительности и воспроизводимости.

Контрольный Docker-прогон на 10 000 сообщений: `0` ошибок, около `244 reports/s`, p95 batch
latency около `1.33 s` при batch size 256. Общая top-1 accuracy — `0.6866`, abstain ratio —
`0.3583`; среди 6 417 принятых ответов synthetic accuracy составила `1.0`. Это показывает, что
текущий threshold безопасно отсекает шумовые варианты, но coverage на искажённых сообщениях пока
недостаточен.
