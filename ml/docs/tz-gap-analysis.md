# Сверка ML/DL Layer с ТЗ

Дата: 2026-09-21. Статусы относятся к `dev/ml-decision-layer`. Backend проверен read-only по
`origin/main` (`70afe51`); ветки не смешивались.

| ТЗ | Статус | Что есть сейчас | Следующий gate |
| --- | --- | --- | --- |
| ML-T00 taxonomy + schemas | Готово со стороны ML | Backend-aligned taxonomy v2: одна primary category, отдельно routing/danger/features; wire schemas | Backend должен seed-ить/утвердить те же stable codes |
| ML-T01 synthetic generator | Готов для data stage | Deterministic world, hard negatives, counterfactuals, noise, 10k mass outage, manifests | Визуально принять стили и расширить adversarial тексты |
| ML-T02 Gold | v2 candidate готов | 522 текста/261 сценарий, backend-aligned targets, API audit и rebuild snapshot | Team sign-off и 80–120 independent real/OOD texts |
| ML-T03 dataset builder | Готов для category v2 | External/template/LLM inputs, схема, manifest/hash и leakage-safe split | Добавить ingestion/feedback после появления контрактных exports |
| ML-T04 rule baseline | Частично | Config-driven incident ranker с ABSTAIN; majority category benchmark | Frozen pair dataset и метрики rules incident matching |
| ML-T05 category/extraction | Baseline + rules готовы | CPU TF-IDF+LogReg и config-driven extraction адреса/подъезда/этажа/длительности/масштаба/danger/continuation | Обучаемый extraction только после разметки; resolver canonical IDs остаётся ingestion |
| ML-T06 retrieval | Synthetic data готова | 200 incident corpus, 1,100 queries и 1,000 qrels со scenario-safe splits | Backend active-incident snapshot; измерить Recall@K/MRR и добавить frozen review set |
| ML-T07 reranker | Data scaffold готов | 3,000 synthetic pairs, hard negatives, Jev-like NLI adapter stub, Qwen3.5 plan | Human review set, encoder baseline и Qwen LoRA experiment on RTX 3060 |
| ML-T08 decision model | Заглушка | Allowed candidates, allow-list validation, ABSTAIN | Backend actions/organizations, training and benchmark |
| ML-T09 calibration | Частично для category | ECE/Brier/risk-coverage; ABSTAIN threshold выбран только на validation | ECE выше цели; сравнить Platt/isotonic на расширенном frozen Gold |
| ML-T10 feedback loop | Контракт | Feedback/event schemas | Backend persistence and producer; privacy/redaction policy |
| ML-T11 inference service | Контракт | Request/response/batch/error/health schemas, sync application service | Async transport/queue integration with backend, timeout and batching |
| ML-T12 vision P1 | Не начат | Явно не блокирует MVP | Только после text pipeline |
| ML-T13 stress/failure | Частично | 10k linked dataset, contract/unit tests, локальный category p50/p95 | Реальный service benchmark, queue drain, RAM/GPU |

## Результат первого честного baseline-прогона

Локальный прогон 2026-09-21 на Gold v2 дал validation Macro F1 `0.8015` и test Macro F1 `0.9872`.
Ориентир ТЗ `Macro F1 ≥ 0.80` формально достигнут, но test слишком синтетический для продуктового
вывода. Validation/test gap подтверждает необходимость независимого real/OOD holdout.

Это не официальный benchmark до human sign-off/freeze. Test не использовался для выбора модели
или threshold; ABSTAIN threshold выбран на validation. Следующий корректный шаг — увеличить
редкие классы и добавить независимые человеческие формулировки, затем пересобрать split и только
после этого сравнивать калибровку/архитектуры.

### На чём основаны текущие метрики

- Полный Gold: 522 текста / 261 сценарий; category baseline использует 482 `ACCEPT` текста.
- Category validation: 66 текстов; category test: 58 текстов.
- В каждом сценарии ровно два связанных текста: deterministic template и LLM-парафраз.
- Все 522 текста имеют источник `SYNTHETIC_TEMPLATE` или `LLM_ASSISTED`; реальных либо независимо
  написанных человеком сообщений в v2 пока нет.
- Split выполняется по `scenario_spec_id`, поэтому два текста одного сценария не расходятся между
  train/validation/test.
- Test support: water 8, electricity 4, building 12, road_and_yard 6, waste 12, emergency 2,
  city_infrastructure 8, other 6. Routing labels оцениваются отдельно и не смешиваются с category.
- Macro F1 усредняет F1 восьми primary category с одинаковым весом.
- Weighted F1 взвешивает классы по support и потому заметно выше: частые категории распознаются
  хорошо, но эта цифра скрывает провал редких и критических labels.
- Top-1 accuracy считает ответ правильным, если label с максимальным score входит в набор истинных
  labels. Она не штрафует пропущенный второй label так же строго, как multi-label F1.
- ECE считается по максимальному score и корректности top-1; Brier — как средняя квадратичная
  ошибка всех one-vs-rest probabilities.
- Coverage/Selective accuracy считаются после `ABSTAIN`. Эффективный abstain threshold не может
  быть ниже label threshold, иначе запрос считался бы принятым без выданной категории.

### Ограничения доказательной силы

29 category test-сценариев — слишком мало для устойчивого вывода, особенно когда каждый сценарий
имеет две близкие формулировки. Текущие числа являются pipeline smoke benchmark,
а не оценкой качества на сообщениях жителей. Нельзя повышать метрику подбором параметров по этому
test; после human-authored дополнения нужен новый frozen test и отдельный OOD split.

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

Сверка выполнена read-only с `origin/main` (`70afe51`, включая backend commit `f762db3`), без merge
веток.

- Backend передаёт UUID как строки и формирует allow-listed incidents/organizations/actions.
- Основная привязка местоположения — canonical `house_id`; `fias_guid` остаётся fallback/provenance.
- ML возвращает category code, а backend разрешает `ProblemCategory.code` в свой UUID.
- В backend `Report.category_id` имеет кардинальность zero-or-one, `NEEDS_CLARIFICATION` является
  статусом, а `danger_flags`, `extracted_features` и `problem_continues` хранятся отдельно. Поэтому
  Gold v1 нельзя замораживать без миграции на taxonomy/annotation v2.
- ML не импортирует SQLAlchemy domain backend и не изменяет backend state.
- Типы организаций совпадают со словарём backend: `ADMINISTRATION`, `POWER_GRID`,
  `WATER_UTILITY`, `EMERGENCY`.

Ожидаемые от backend части: transport adapter/DTO, список allowed actions, выборка кандидатов,
хранение Decision/feedback и async delivery policy. От ingestion ожидаются versioned canonical
addresses, organizations и external events.
