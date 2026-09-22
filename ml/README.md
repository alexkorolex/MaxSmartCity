# ML-/DL-контур

ML-контур «Умного города»: контракты, локальные datasets, воспроизводимый CPU baseline и
заглушки для компонентов, которые зависят от backend/Data Ingestion или новых датасетов.
Репозиторий не содержит обученных checkpoints и не вызывает LLM при тестах/обучении baseline.

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

Подготовка публичных источников и 180 pre-LLM facts описана в
[`data/external/README.md`](data/external/README.md). Исходные CSV и EDA notebooks в Git не
добавляются.

Версионированный offline-пайплайн лексикализации через AI Tunnel также описан в
[`data/external/README.md`](data/external/README.md). Он по умолчанию строит только план;
реальный запрос требует явного `--execute`, а результат остаётся кандидатом до ручной ревизии.

Backend-aligned dataset находится в [`data/gold/v2`](data/gold/v2/README.md): 522 текста,
261 сценарий и leakage-safe train/validation/test splits. Category, routing и danger разделены;
статус остаётся `REVIEWED_PENDING_TEAM_SIGNOFF` до командной приёмки и независимого real/OOD test.

Отдельный synthetic benchmark для retrieval/reranking находится в
[`data/matching/dev-v1`](data/matching/README.md): 200 incidents, 1 100 queries, 1 000 qrels и
3 000 positive/hard-negative pairs. План Jev-like эксперимента с Qwen3.5-4B и RTX 3060 — в
[`docs/jev-qwen35-plan.md`](docs/jev-qwen35-plan.md).

## Структура

```text
maxsmartcity/ml/
├── domain/          # requests, results, feedback, async events
├── application/     # use cases, fallback and input policy
├── ports/           # model/backend/ingestion interfaces
├── adapters/        # baselines, Jev scaffold and dependency stubs
├── data/            # configs, splits and synthetic world generation
├── training/        # reproducible CPU training
├── evaluation/      # classification/calibration/selective metrics
└── inference/       # trusted local artifact loader

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

## Обучение, метрики и smoke inference

```powershell
uv sync --locked --group dev
.\ml\scripts\train_category_baseline.ps1
uv run --locked python -m maxsmartcity.ml.inference.cli `
  --artifact ml/artifacts/category-tfidf-logreg-v2 `
  --text "В доме 12 третий час нет холодной воды"
```

Подробности: [`training/README.md`](training/README.md),
[`evaluation/README.md`](evaluation/README.md), [`inference/README.md`](inference/README.md).

## Проверки

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest
```
