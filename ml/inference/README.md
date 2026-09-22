# Инференс

Локальный smoke-test обученного category checkpoint:

```bash
uv run --locked python -m maxsmartcity.ml.inference.cli \
  --artifact ml/artifacts/category-tfidf-logreg-v2 \
  --text "В доме 12 третий час нет холодной воды"
```

Ответ содержит ранжированные category scores, `abstain`, причину отказа, model version и taxonomy
version. Пустой текст всегда приводит к `ABSTAIN`.

`joblib` нельзя загружать из недоверенного источника. Веса не коммитятся; локальный loader
проверяет SHA-256 модели и согласованность model/taxonomy version с manifest. Для передачи
checkpoint нужен доверенный artifact storage.

## Инференс по HTTP

После обучения:

```bash
uv run --locked litestar --app main:app run --host 0.0.0.0 --port 8000
```

Реализованы `/v1/classify`, `/v1/classify:batch`, `/v1/decide`, `/health`, `/ready` и
`/v1/models`. CPU inference выполняется вне event loop; `/v1/decide` соблюдает `deadline_ms` и
возвращает стабильные error envelopes. При отсутствии checkpoint health остаётся доступным,
readiness возвращает 503, а rule fallback сохраняет recommendation-only решение для backend.

Схемы wire-контрактов находятся в `ml/contracts/backend/v2`. Organization/action models пока
явно возвращают task-level `ABSTAIN`; rule incident ranking также не разрешён для автоматизации.
