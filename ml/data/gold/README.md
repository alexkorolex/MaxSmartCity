# Manual Gold dataset

Работа начинается в `drafts/reports.seed.jsonl`. Сейчас там 20 стартовых кандидатов для
обсуждения taxonomy и правил разметки. Они имеют статус `DRAFT`, созданы как заготовки и
не являются Gold до проверки человеком.

Порядок работы:

1. Прочитать [`ANNOTATION_GUIDE.md`](ANNOTATION_GUIDE.md).
2. Исправить category/multi-label решения и notes.
3. Разметить entity spans по точным индексам строки.
4. Указать реального `annotator`.
5. Другой участник проверяет запись и ставит `REVIEWED` + `reviewer`.
6. После набора достаточного объёма сформировать immutable validation/test release.
7. Только release получает статус `FROZEN` и отдельный manifest/hash.

Целевой объём:

- 300–500 отдельных Reports;
- 50–100 multi-report scenarios;
- отдельные `validation_gold`, `test_gold` и `test_ood`.

Synthetic и автоматически подготовленные draft-кандидаты нельзя включать в frozen Gold
без человеческой проверки. Персональные данные удаляются или псевдонимизируются.
