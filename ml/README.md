# ML / DL Layer

Каркас ML-контура «Умного города». Текущая стадия предназначена для согласования
контрактов и локальной отладки datasets. Она не скачивает модели, не вызывает LLM и не
содержит обученных checkpoints.

## Архитектурные правила

- ML принимает snapshot состояния и разрешённые backend-кандидаты.
- ML не меняет Incident, не вызывает организации и не выполняет actions.
- Категории и baseline weights находятся в versioned JSON, а не в Python enum/константах.
- Каждая задача имеет собственный `ABSTAIN`; уверенность в одной задаче не переносится на
  другую.
- Rule baseline — только benchmark. Его score не является вероятностью, automation
  выключена до calibration.
- Hard safety rules выполняет backend Policy Engine. Extraction-модель позже возвращает
  только наблюдаемые сигналы.
- ML не разрешает адрес в ФИАС, а принимает canonical ID от backend/ingestion.

Матрица ожиданий и владельцев: [`DEPENDENCIES.md`](DEPENDENCIES.md).

## Структура

```text
maxsmartcity/ml/
├── domain/          # requests, results, feedback, async events
├── application/     # use cases, fallback and input policy
├── ports/           # model/backend/ingestion interfaces
├── adapters/        # baselines, Jev scaffold and dependency stubs
└── data/            # configs, splits and synthetic world generation

ml/
├── configs/
├── contracts/
├── data/
├── docs/
├── evaluation/
├── experiments/
├── inference/
└── training/
```

## Локальная генерация

```bash
uv run python -m maxsmartcity.ml.data.synthetic.cli \
  --config ml/configs/synthetic.v2.json \
  --seed 42 \
  --output-dir ml/data/synthetic/dev-v2 \
  standard \
  --scenarios 200 \
  --reports-per-scenario 5 \
  --noise-reports 100
```

На выходе создаются:

- `scenarios.jsonl`, `houses.jsonl`, `organizations.jsonl`;
- `external_events.jsonl`;
- `incidents.jsonl`;
- `reports.jsonl`;
- `decisions.jsonl` с настоящими существующими hard-negative Incident IDs;
- `counterfactuals.jsonl`;
- `manifest.json` с версиями, seed, counts и SHA-256.

Seed каждого Scenario и Report выводится независимо через SHA-256. Поэтому добавление
нового Report не изменяет уже существующие примеры.

Массовый stress dataset:

```bash
uv run python -m maxsmartcity.ml.data.synthetic.cli \
  --config ml/configs/synthetic.v2.json \
  --seed 20260920 \
  --output-dir ml/data/synthetic/stress-mass-outage-v2 \
  mass-outage \
  --reports 10000
```

Сформированные локальные наборы:

- `dev-v2`: 300 Scenario (200 incident + 100 noise), 1 100 Reports, 200 counterfactuals;
- `stress-mass-outage-v2`: 10 000 Reports, 100 домов, один Incident.

## Что делать на ноутбуке

1. Согласовать draft taxonomy и schemas с backend/product.
2. Проверить synthetic records визуально и расширить configs.
3. Добавить noise, counterfactual, mass-event и adversarial generators.
4. Создать небольшой вручную проверенный Gold.
5. Зафиксировать dataset manifests и splits.
6. Реализовать TF-IDF/BM25 baseline и посчитать первые метрики.

## Что делать на машине с RTX 3060

Только после принятия datasets:

1. Подготовить train/evaluation scripts и locked model dependencies.
2. Обучить category/extraction baseline.
3. Подключить multilingual embeddings и candidate retrieval.
4. Обучить incident pair/cross-encoder или Jev-like NLI ranker.
5. Сохранить checkpoint вместе с dataset hash, taxonomy version, git commit и config hash.
6. Выполнить calibration: ECE, Brier, risk-coverage.
7. После этого реализовать inference/batch API и минимальные model-loading tests.

`UntrainedJevIncidentRanker` намеренно падает контролируемой ошибкой: случайный или
непроверенный checkpoint не должен незаметно стать production recommendation.

## Проверки

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest
```
