# ML dependencies and ownership

Этот файл фиксирует, какие пробелы являются заглушками, кто предоставляет данные и что
можно разрабатывать независимо. Заглушка не означает, что задача забыта.

| Возможность | Текущий статус | Владелец / ожидание |
|---|---|---|
| Report/Incident contract | Draft в `ml/contracts/backend/v2` | **Ждём backend:** review полей и naming |
| Allowed actions | Пустой task-level `ABSTAIN` | **Ждём backend:** Policy Engine и список действий |
| Organization candidates | Пустой task-level `ABSTAIN` | **Ждём backend:** допустимые организации для состояния |
| Decision persistence | Response/feedback/event schemas готовы | **Ждём backend:** storage и producer событий |
| Canonical address | `fias_guid` принимается как вход | **Ждём ingestion:** resolver/export; ML не создаёт GUID |
| External events | `external_context` fixture | **Ждём ingestion:** versioned snapshot/API/Parquet |
| Organization registry | Demo IDs в synthetic config | **Ждём ingestion:** canonical organization export |
| Taxonomy | Versioned draft JSON | **Совместно:** product/backend/ML утверждают stable IDs |
| Gold dataset | 20 draft-кандидатов + guide/validator | **Нужна человеческая разметка:** 300–500 Reports |
| Multi-report Gold | Пока отсутствует | **Наша ответственность:** 50–100 сценариев вручную позже |
| Synthetic world | Linked world + noise/counterfactual/mass generators | **Наша ответственность:** расширять стили и OOD |
| LLM synthetic | Не вызывается | **Наша ответственность:** offline generate/validate/freeze позже |
| Category/extraction model | Явный TODO | **Наша ответственность:** после проверки dataset |
| Retrieval/reranker | Rule benchmark + Jev scaffold | **Наша ответственность:** обучить на машине с RTX 3060 |
| Calibration | Отсутствует, automation выключена | **Наша ответственность:** после validation predictions |
| Inference API | Wire schemas готовы, transport отсутствует | **Совместно с backend:** async HTTP/queue review |
| Vision/OCR | Не реализовано | **Наша ответственность, P1:** не блокирует MVP |

## Принцип работы заглушек

- Нет данных — компонент возвращает `ABSTAIN` или контролируемую
  `ComponentUnavailableError`.
- Заглушка не генерирует доменные ID и не подменяет backend/ingestion своей логикой.
- Hard safety policy остаётся в backend. ML позже вернёт только извлечённые сигналы.
- До калибровки никакой heuristic/model score не разрешает автоматическое действие.
