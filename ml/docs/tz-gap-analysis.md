# Сверка ML/DL Layer с ТЗ

Дата: 2026-09-21. Статусы относятся к `dev/ml-decision-layer` и не включают код из
`dev/backend_api`.

| ТЗ | Статус | Что есть сейчас | Следующий gate |
| --- | --- | --- | --- |
| ML-T00 taxonomy + schemas | Частично | Versioned draft taxonomy, backend/ingestion/dataset/artifact schemas | Совместно утвердить подкатегории, actions и stable codes |
| ML-T01 synthetic generator | Готов для data stage | Deterministic world, hard negatives, counterfactuals, noise, 10k mass outage, manifests | Визуально принять стили и расширить adversarial тексты |
| ML-T02 Gold | Не готов | 20 ранних drafts и 180 проверенных pre-LLM facts | LLM lexicalization, ручная проверка 300–500 reports и 50–100 multi-report scenarios |
| ML-T03 dataset builder | Частично | Source adapters, mappings, JSONL, source manifests, scenario-level split primitive | Объединение LLM/Gold/ingestion и manifests каждого split |
| ML-T04 rule baseline | Частично | Config-driven incident ranker, canonical house/category/time signals, forced abstain | Посчитать baseline metrics на frozen Gold |
| ML-T05 category/extraction | Заглушка | Порты, result types и input policy | Dataset approval, затем train/eval/inference на GPU |
| ML-T06 retrieval | Не начат | Candidate contract и synthetic candidates | Ingestion/backend snapshot и frozen benchmark |
| ML-T07 reranker | Заглушка | Jev-like NLI examples и untrained adapter | Русский pair dataset, model comparison, false merge/split metrics |
| ML-T08 decision model | Заглушка | Allowed candidates, allow-list validation, ABSTAIN | Backend actions/organizations, training and benchmark |
| ML-T09 calibration | Не начат | Scores не объявляются probability, automation off | Validation predictions: ECE, Brier, risk-coverage, thresholds |
| ML-T10 feedback loop | Контракт | Feedback/event schemas | Backend persistence and producer; privacy/redaction policy |
| ML-T11 inference service | Контракт | Request/response/batch/error/health schemas, sync application service | Async transport/queue integration with backend, timeout and batching |
| ML-T12 vision P1 | Не начат | Явно не блокирует MVP | Только после text pipeline |
| ML-T13 stress/failure | Частично | 10k linked dataset and contract/unit tests | Реальный service benchmark, p50/p95, queue drain, RAM/GPU |

## Что завершено для подготовки внешних данных

1. Raw CSV перенесены в Git-ignored `ml/data/external/raw`.
2. Для SF311 и BMC записаны source/license/hash manifests.
3. Внешние записи отделены от canonical scenario model.
4. SF311 импортируется потоково.
5. BMC (960k строк) потоково агрегируется и балансированно семплируется.
6. Mapping source taxonomy → project taxonomy находится в versioned JSON.
7. Детерминированно строятся 180 facts: 100 SF311, 60 BMC, 20 curated.
8. Результат и manifest сохраняются в JSONL/JSON.
9. Проверено 100 стратифицированных фактов; полный набор проходит structural checks.

Эти данные не являются Gold: SF311 не содержит свободного resident text, BMC полностью
синтетический, а русские описания пока являются нормализованными фактами.

## Асинхронность

Async нужен на границе: backend HTTP/queue → bounded ML queue → batcher → worker → idempotent
result event. Dataset transforms, validators, metrics и model forward остаются синхронными.
Добавлять async в CSV import/build сейчас не нужно: это локальный последовательный pipeline, а
BMC уже обрабатывается без загрузки всего файла в память.

## Контракт с backend

Сверка выполнена read-only с `origin/dev/backend_api` (`f20c6a0`), без merge веток.

- Backend передаёт UUID как строки и формирует allow-listed incidents/organizations/actions.
- Основная привязка местоположения — canonical `house_id`; `fias_guid` остаётся fallback/provenance.
- ML возвращает category code, а backend разрешает `ProblemCategory.code` в свой UUID.
- ML не импортирует SQLAlchemy domain backend и не изменяет backend state.
- Типы организаций совпадают со словарём backend: `ADMINISTRATION`, `POWER_GRID`,
  `WATER_UTILITY`, `EMERGENCY`.

Ожидаемые от backend части: transport adapter/DTO, список allowed actions, выборка кандидатов,
хранение Decision/feedback и async delivery policy. От ingestion ожидаются versioned canonical
addresses, organizations и external events.
