# Подготовка внешних сценариев

Этот слой преобразует записи из внешних источников в детерминированные факты русскоязычных
сценариев. Он не создаёт Gold-примеры и не вызывает LLM. Позже LLM может сформулировать
утверждённый факт естественным языком, но не имеет права придумывать метки.

## Поток данных

1. Хранить скачанные CSV-файлы в `raw/`, который исключён из Git.
2. Фиксировать источник, лицензию, снимок, размер и SHA-256 в `manifests/`.
3. Потоково обрабатывать строки адаптером конкретного источника.
4. Сопоставлять понятия источника через версионированные правила из `mappings/`.
5. Объединять одинаковые семантические комбинации и выбирать сбалансированную по категориям
   выборку.
6. Заменять все исходные адреса детерминированными адресами демонстрационного города.
7. Добавлять вручную спроектированные пограничные случаи из
   `ml/configs/external-scenarios.v1.json`.
8. Записывать `canonical/v1/scenarios.jsonl`, проверять его и проводить ревизию до обогащения LLM.

Канонический файл в репозитории содержит 181 факт до обработки LLM: 100 из словаря SF311,
60 из выборки синтетических комбинаций BMC и 21 вручную подготовленный факт по безопасности и
OOD. Исходные и промежуточные файлы остаются локальными.

## Пересборка

```powershell
uv run --locked python -m src.ml.data.external.cli `
  --config ml/configs/external-scenarios.v1.json `
  --taxonomy ml/configs/taxonomy.v1.json `
  --sf311-mapping ml/data/external/mappings/sf311-taxonomy.v1.json `
  --bmc-mapping ml/data/external/mappings/bmc-taxonomy.v1.json `
  --sf311-csv ml/data/external/raw/sf311/SF311_-_Recent_Cases_20260921.csv `
  --bmc-csv ml/data/external/raw/bmc/bmc_train.csv `
  --output-dir ml/data/external/canonical/v1
```

## Зоны ответственности и следующие шаги

- **ML сейчас:** адаптеры источников, правила сопоставления, канонические факты, ревизия и позднее
  отслеживание версий промптов.
- **ML позже:** перефразировки LLM после ручного утверждения фактов, Gold-разметка и разбиение по
  сценариям.
- **Data ingestion:** версионированные производственные выгрузки по контракту ingestion.
- **Backend:** использование контракта Decision API без зависимости от файлов подготовки данных.

Нельзя добавлять в Git ключи API, `.env.local`, скачанные исходные файлы и непроверенные ответы LLM.

## Генерация кандидатов от шаблонов

Предпочтительный пайплайн сначала создаёт два детерминированных русскоязычных исходных текста для
каждого канонического факта. Faker/pymorphy3 используется только в небольшом локальном превью;
канонический пакет строится по версионированным шаблонам и явным исключениям для всех вручную
подготовленных пограничных случаев. Augmentex не используется.

Сборка 362 текущих локальных исходных текстов без вызова API:

```powershell
uv run --locked python -m src.ml.data.template_generation.canonical_cli `
  --config ml/configs/canonical-template-seeds.v1.json `
  --canonical ml/data/external/canonical/v1/scenarios.jsonl `
  --output-dir ml/data/external/interim/canonical-template-seeds-v1
```

Перед выполнением проверьте бесплатный план. Текущий канонический набор создаёт 181 запрос и
запрашивает 362 варианта:

```powershell
uv run --locked python -m src.ml.data.template_generation.paraphrase_cli `
  --seeds-file ml/data/external/interim/canonical-template-seeds-v1/examples.jsonl `
  --llm-config ml/configs/template-paraphrase.full-v1.json `
  --output-dir ml/data/external/interim/template-paraphrase-full-v1
```

Добавляйте `--env-file .env.local --execute` только после проверки исходных текстов и пилота на
20 примерах. Исторический полный запуск v1 выполнил 180 запросов и создал 360 перефразировок за
4,0278 ₽: 353 прошли детерминированную проверку, 7 попали в карантин. Более поздний отрицательный
сценарий `thanks-only` создан локально и не потребовал нового вызова API. Точные дубликаты и
обнаруженные при ревизии смысловые сдвиги исправляются в `ml/configs/gold-mvp.v1.json`.

## Устаревший пайплайн лексикализации через AI Tunnel

Старый многоэтапный генератор сохранён для воспроизводимости отклонённых запусков. LLM выступает
лексикализатором текста, а не разметчиком: категория, подкатегория, организация, серьёзность,
необходимость уточнения и признаки опасности остаются зафиксированными каноническими фактами.
Каждая сгенерированная запись остаётся кандидатом, пока человек не примет её в Gold.

Скопируйте `.env.ml.example` в `.env.local` и добавьте туда ключ API. Локальный файл исключён из
Git. Сначала проверьте бесплатный план:

```powershell
uv run --locked python -m src.ml.data.llm.cli `
  --config ml/configs/llm-augmentation.v2.json `
  --input ml/data/external/canonical/v1/scenarios.jsonl `
  --output-dir ml/data/external/interim/llm-pilot-v1
```

Выполнение одного подготовленного сценария — три вызова API и десять запрошенных вариантов:

```powershell
uv run --locked python -m src.ml.data.llm.cli `
  --config ml/configs/llm-augmentation.v2.json `
  --input ml/data/external/canonical/v1/scenarios.jsonl `
  --output-dir ml/data/external/interim/llm-pilot-v1 `
  --scenario-id CURATED-water-near-electric-panel `
  --execute
```

Запуск можно продолжить после остановки. В исключённом из Git каталоге `interim/` сохраняются
ответы провайдера, результаты детерминированной проверки, расход токенов и оценка стоимости.
Проверьте `candidates.jsonl` и `quarantine.jsonl`: ни один из этих файлов ещё не считается
обучающими данными. Используйте `--full` только после проверки пилота и утверждения канонических
фактов.

Основной пакет v1 — детерминированная выборка из 60 сценариев: все 20 пограничных случаев,
20 фактов BMC и 20 фактов SF311. Внешние факты сбалансированы квотами по основной категории и
циклически выбираются по подкатегориям. Перед генерацией пересоберите манифест:

```powershell
uv run --locked python -m src.ml.data.llm.selection_cli `
  --config ml/configs/llm-selection.v1.json `
  --input ml/data/external/canonical/v1/scenarios.jsonl `
  --output ml/data/external/selections/llm-batch-v1.json
```

Затем передайте `--selection-file ml/data/external/selections/llm-batch-v1.json` в CLI
лексикализации. Текущая трёхэтапная конфигурация запрашивает 440 кандидатов за 140 возобновляемых
вызовов API. Не используйте `--full` без проверки плана: этот флаг запрашивает кандидатов для
всего текущего канонического набора.

После генерации создайте локальную очередь ручной проверки из автоматически принятых кандидатов:

```powershell
uv run --locked python -m src.ml.data.llm.review_cli `
  --candidates ml/data/external/interim/llm-main-v2/candidates.jsonl `
  --canonical ml/data/external/canonical/v1/scenarios.jsonl `
  --output ml/data/external/interim/llm-main-v2/review.csv
```

Заполните `review_decision` значением `ACCEPT`, `REJECT` или `EDIT`. Автоматическая приёмка не
делает запись Gold: проверяющий должен сопоставить каждый текст с `locked_problem`, адресом,
контекстом и признаками опасности.
