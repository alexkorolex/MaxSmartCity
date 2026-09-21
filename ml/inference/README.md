# Inference

Локальный smoke-test обученного category checkpoint:

```bash
uv run --locked python -m maxsmartcity.ml.inference.cli \
  --artifact ml/artifacts/category-tfidf-logreg-v2 \
  --text "В доме 12 третий час нет холодной воды"
```

Ответ содержит ранжированные category scores, `abstain`, причину отказа, model version и taxonomy
version. Пустой текст всегда приводит к `ABSTAIN`.

`joblib` нельзя загружать из недоверенного источника. Веса не коммитятся; для передачи checkpoint
нужны checksum/manifest или доверенное artifact storage.

HTTP transport остаётся ответственностью интеграции с backend. Его следующий этап: async Litestar
boundary, bounded queue, batch, timeout/graceful fallback, `/health`, `/ready` и `/v1/models`.
