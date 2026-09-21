# ML dependencies and ownership

Этот файл фиксирует, какие пробелы являются заглушками, кто предоставляет данные и что
можно разрабатывать независимо. Заглушка не означает, что задача забыта.

| Возможность | Текущий статус | Владелец / ожидание |
|---|---|---|
| Report/Incident contract | Сверен с `dev/backend_api` от 2026-09-21; transport DTO ещё draft | **Совместно:** backend добавляет ML-specific DTO/adapter |
| Allowed actions | Пустой task-level `ABSTAIN` | **Ждём backend:** Policy Engine и список действий |
| Organization candidates | Пустой task-level `ABSTAIN` | **Ждём backend:** допустимые организации для состояния |
| Decision persistence | Response/feedback/event schemas готовы | **Ждём backend:** storage и producer событий |
| Canonical address | `address_id`/`house_id` принимаются от backend; `fias_guid` — fallback provenance | **Ждём ingestion:** resolver/export; ML не создаёт ID |
| External events | `external_context` fixture | **Ждём ingestion:** versioned snapshot/API/Parquet |
| Organization registry | Demo IDs в synthetic config | **Ждём ingestion:** canonical organization export |
| Taxonomy | Versioned draft JSON | **Совместно:** product/backend/ML утверждают stable IDs |
| Gold dataset | Reviewed MVP v1: 362 уникальных текста / 181 сценарий, leakage-safe splits | **Нужен human sign-off:** затем сменить статус `REVIEWED` на `FROZEN` |
| Multi-report / reranker Gold | Пока отсутствует; сознательно исключён из text Gold v1 | **Наша ответственность позже:** отдельные positive/hard-negative/NEW_INCIDENT пары и новый API-run |
| Synthetic world | Linked world + noise/counterfactual/mass generators | **Наша ответственность:** расширять стили и OOD |
| LLM synthetic | Full v1 выполнен: 353 auto-pass, 7 quarantine, стоимость 4.0278 ₽ | **Наша ответственность:** human review, deduplication и freeze |
| Category/extraction model | Явный TODO | **Наша ответственность:** после проверки dataset |
| Retrieval/reranker | Rule benchmark + Jev scaffold | **Наша ответственность:** обучить на машине с RTX 3060 |
| Calibration | Отсутствует, automation выключена | **Наша ответственность:** после validation predictions |
| Inference API | Wire schemas готовы, transport отсутствует | **Совместно с backend:** async HTTP/queue; sync model adapter остаётся внутри worker |
| Vision/OCR | Не реализовано | **Наша ответственность, P1:** не блокирует MVP |

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
