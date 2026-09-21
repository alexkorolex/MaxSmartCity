# MaxSmartCity — «Дом.Сигнал»

MVP связывает сообщения жителей о проблемах МКД с единой карточкой инцидента. ML-слой
классифицирует текст, извлекает наблюдаемые признаки и ранжирует только те инциденты, которые
backend передал в allow-list. Любой неуверенный или некалиброванный результат остаётся
рекомендацией для ручной проверки.

Текущий датасет — подготовленная синтетика и LLM-assisted примеры. Реальное подключение к ГИС
ЖКХ или данным управляющей организации не заявляется.

## Запуск одной командой

```bash
docker compose up --build
```

После сборки:

- health: `http://localhost:8000/health`;
- readiness: `http://localhost:8000/ready`;
- модели: `http://localhost:8000/v1/models`;
- OpenAPI: `http://localhost:8000/schema/openapi.json`.

Образ обучает небольшой CPU baseline на versioned Gold v2 во время сборки. Рабочие токены для
инференса не нужны. Настройки без секретов приведены в `.env.example`.

## Локальная разработка

Нужны Python 3.12+ и [uv](https://docs.astral.sh/uv/).

После клонирования установите зависимости и Git-хук:

```bash
uv sync --locked --group dev
uv run --locked pre-commit install
```

[pre-commit](https://pre-commit.com/) перед каждым коммитом запускает проверки
всего проекта: `ruff check .`, `ruff format --check .`, `ty check` и `pytest`.
Ошибка любой проверки блокирует коммит. Версии инструментов берутся из `uv.lock`;
хуки не исправляют код автоматически.

Запуск всех проверок вручную:

```bash
uv run --locked pre-commit run --all-files
```

Запуск только тестов:

```bash
uv run --locked pytest
```

Исправление замечаний Ruff и форматирование:

```bash
uv run --locked ruff check --fix .
uv run --locked ruff format .
```

## ML / DL

Автономный ML-контур, CPU baseline, синтетические данные и интеграционные контракты описаны
в [`ml/README.md`](ml/README.md). Обучение baseline не вызывает LLM, не скачивает веса и не
требует готовых API backend/Data Ingestion.

Быстрый локальный запуск ML API:

```bash
uv run --locked python -m maxsmartcity.ml.training.cli
uv run --locked litestar --app main:app run --host 0.0.0.0 --port 8000
```

HTTP-контракты и проверочный `openapi.yaml` находятся в `ml/contracts/backend/v2`. Минимальный рабочий контур поддерживает
`POST /v1/classify`, `POST /v1/classify:batch`, `POST /v1/decide`, `GET /health`, `GET /ready` и
`GET /v1/models`. Ограничение длины текста задаётся через `ML_MAX_INPUT_CHARACTERS`.
