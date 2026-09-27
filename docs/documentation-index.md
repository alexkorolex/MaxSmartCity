# Карта документации

Файл помогает отличать актуальные инструкции, контракты, данные экспериментов и справочные
материалы. Документация frontend здесь только перечислена и не меняется в рамках Backend/ML.

## Проект и сдача

| Файл | Назначение | Статус |
|---|---|---|
| `README.md` | Запуск, архитектура, Backend, ingestion, Incident Core, ML и эксплуатация | Основная актуальная инструкция |
| `docs/presentation-outline.md` | Послайдовая схема презентации по критериям организаторов | Заполнить ссылками и фактами финального release |
| `docs/data-readiness.md` | Тестовые, обучающие и картографические данные | Актуально; ждёт источник координат |
| `docs/organizer-readiness-2026-09-26.md` | Аудит готовности конкретного среза | Исторический снимок, не финальная оценка |
| `docs/documentation-index.md` | Навигация и жизненный цикл Markdown-файлов | Актуально |
| `submission/README.md` | Пересборка OpenAPI и подготовка DATA-API | Заполнить release-значениями перед сдачей |

## Контракты Backend и Incident Core

| Файл | Назначение | Статус |
|---|---|---|
| `docs/frontend-incident-contract.md` | Команды основного жизненного цикла | Актуальный интеграционный контракт |
| `docs/frontend-map-contract.md` | GeoJSON домов и слои карты | Актуально; допускает дома без координат |
| `docs/ml-other-mvp-handoff.md` | Сценарий рекомендаций для «Другого» | Актуально; ML остаётся advisory |
| `ingestion/data/gis_zkh_discrepancies.md` | Сверка пилота с публичной выгрузкой | Аудит данных, не инструкция запуска |

## ML-контур

| Файл | Назначение | Статус |
|---|---|---|
| `ml/README.md` | Точки входа и обзор ML | Основная ML-инструкция |
| `ml/DEPENDENCIES.md` | Инварианты и границы ответственности | Актуально |
| `ml/docs/architecture.md` | Разделение runtime, Backend gateway и ресурсов | Актуально |
| `ml/inference/README.md` | Локальный и HTTP inference | Актуально |
| `ml/training/README.md` | Обучение CPU baseline | Актуально |
| `ml/evaluation/README.md` | Метрики и benchmark-команды | Актуально |
| `ml/docs/gold-v2-plan.md` | Происхождение и приёмка Gold v2 | План и журнал решения; не production Gold |
| `ml/docs/jev-qwen35-plan.md` | Необязательный GPU-эксперимент | Roadmap после MVP, не реализованная функция |

## Наборы данных ML

| Файл | Назначение | Статус |
|---|---|---|
| `ml/data/gold/README.md` | Общие правила Gold | Актуально |
| `ml/data/gold/ANNOTATION_GUIDE.md` | Руководство разметчика | Актуально |
| `ml/data/gold/v1/README.md` | Предыдущая версия Gold | Историческая версия |
| `ml/data/gold/v2/README.md` | Текущий LLM-assisted набор | Не заморожен как human-reviewed test |
| `ml/data/matching/README.md` | Общий retrieval/reranking corpus | Synthetic benchmark |
| `ml/data/matching/other-v1/README.md` | Benchmark рекомендаций «Другое» | Текущий synthetic benchmark |
| `ml/data/synthetic/README.md` | Детерминированные нагрузочные наборы | Только тесты и benchmark |
| `ml/data/external/README.md` | Подготовка внешних сценариев | Актуально; старый AI Tunnel flow помечен устаревшим |
| `ml/data/external/review/canonical-v1.review.md` | Результат ревизии внешних сценариев | Аудит конкретной версии |

## Справочные материалы MAX

| Файл | Назначение | Статус |
|---|---|---|
| `etc/max_api/MAX_API_AGENT_CONTEXT.md` | Локальная выдержка контракта MAX API | Справочник; сверять с первичным OpenAPI |
| `etc/max_api/MAX_WEBHOOK_IMPLEMENTATION.md` | Правила webhook и тестовая матрица | Справочник реализации |
| `etc/max_ui/MAX_UI_GUIDE_FSD.md` | Руководство UI-компонентов | Зона frontend; в этом аудите не изменялась |

В отслеживаемых Markdown-файлах не найдено скрытых HTML-комментариев, `TODO` или `FIXME`,
которые стоило бы удалять. Комментарии внутри примеров кода и справочников MAX оставлены,
поскольку объясняют команды или ограничения протокола.
