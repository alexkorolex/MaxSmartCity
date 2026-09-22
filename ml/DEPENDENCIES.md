# Зависимости ML и зоны ответственности

Этот файл фиксирует, какие пробелы являются заглушками, кто предоставляет данные и что
можно разрабатывать независимо. Заглушка не означает, что задача забыта.

| Возможность | Текущий статус | Владелец / ожидание |
|---|---|---|
| Report/Incident contract | Backend adapter и HTTP gateway реализованы, UUID передаются строками | **Backend:** подключить gateway к application workflow создания/связывания Incident |
| Allowed actions | Пустой task-level `ABSTAIN` | **Ждём backend:** Policy Engine и список действий |
| Organization candidates | Пустой task-level `ABSTAIN` | **Ждём backend:** допустимые организации для состояния |
| Decision persistence | Response/feedback/event schemas готовы | **Ждём backend:** storage и producer событий |
| Canonical address | `address_id`/`house_id` принимаются от backend; `fias_guid` — fallback provenance | **Ждём ingestion:** resolver/export; ML не создаёт ID |
| External events | `external_context` fixture | **Ждём ingestion:** versioned snapshot/API/Parquet |
| Organization registry | Demo IDs в synthetic config | **Ждём ingestion:** canonical organization export |
| Taxonomy | Versioned draft JSON | **Совместно:** product/backend/ML утверждают stable IDs |
| Gold dataset | Backend-aligned v2: 522 текста / 261 сценарий, leakage-safe splits | **Нужен human sign-off:** затем независимый human/OOD freeze |
| Multi-report / reranker Gold | Synthetic v1: 1,100 queries, 1,000 qrels, 3,000 pairs; human Gold отсутствует | **Наша ответственность:** 50–100 reviewed scenarios; **backend:** active incident snapshot |
| Synthetic world | Linked world + noise/counterfactual/mass generators | **Наша ответственность:** расширять стили и OOD |
| LLM synthetic | Full v1 выполнен: 353 auto-pass, 7 quarantine, стоимость 4.0278 ₽ | **Наша ответственность:** human review, deduplication и freeze |
| Category model | CPU TF-IDF+LogReg baseline подключён к DecisionService и Docker inference | **Наша ответственность:** расширить/freeze Gold перед автоматизацией |
| Extraction model | Config-driven MVP rules извлекают raw address, entrance/floor, duration, scale, danger и continuation; canonical IDs не выдумываются | **Наша ответственность:** расширять правила/датасет; модель только при достаточной разметке |
| Retrieval/reranker | Rule benchmark, synthetic retrieval/reranking corpus, Jev scaffold и Qwen3.5-4B LoRA plan | **Наша ответственность:** benchmark/train на RTX 3060; **backend:** выдавать active candidates |
| Calibration | ECE/Brier/risk-coverage считаются; ABSTAIN threshold выбирается на validation; сами probabilities ещё не calibrated | **Наша ответственность:** Platt/isotonic после расширения Gold, automation пока выключена |
| Inference API | HTTP classify/batch/decide, health/readiness, Docker и backend gateway готовы | **Backend:** orchestration и persistence; bounded queue — после появления реальной нагрузки |
| Vision/OCR | Не реализовано | **Наша ответственность, P1:** не блокирует MVP |
| Stress benchmark | 10 000 mass-outage Reports проходят реальный HTTP batch endpoint без ошибок | **Наша ответственность:** следить за throughput/abstain regression; RAM/queue benchmark после появления worker queue |

## Принцип работы заглушек

- Нет данных — компонент возвращает `ABSTAIN` или контролируемую
  `ComponentUnavailableError`.
- Заглушка не генерирует доменные ID и не подменяет backend/ingestion своей логикой.
- Hard safety policy остаётся в backend. ML позже вернёт только извлечённые сигналы.
- До калибровки никакой heuristic/model score не разрешает автоматическое действие.

## Сверка с `dev/backend_api`

- Backend UUID передаются через JSON как строки; ML не импортирует ORM-модели backend.
- Каноническая география backend — `address_id` и `house_id`; FIAS остаётся внешним идентификатором.
- Типы организаций согласованы с backend: `ADMINISTRATION`, `POWER_GRID`, `WATER_UTILITY`,
  `EMERGENCY`.
- Backend хранит `ProblemCategory.id` как UUID и `ProblemCategory.code` как стабильный код. ML
  возвращает именно taxonomy code; backend adapter разрешает его в UUID.
- `maxsmartcity/ml` остаётся отдельным пакетом: перенос под backend `src/` не нужен для merge и
  не должен связывать ML domain с SQLAlchemy.
