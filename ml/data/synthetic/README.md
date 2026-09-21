# Generated synthetic datasets

## `dev-v2`

- 200 связанных incident Scenario/House/ExternalEvent/Incident и 100 noise Scenario;
- 1 000 incident Reports и 100 noise Reports;
- 1 100 decision examples;
- 200 address counterfactuals;
- hard negatives выбираются среди Incident той же категории, когда это возможно.

## `stress-mass-outage-v2`

- 1 официальный synthetic external event;
- 1 Incident;
- 100 домов;
- 10 000 Reports;
- генерируется в памяти для HTTP batch benchmark, не используется как quality benchmark.

Оба набора полностью воспроизводятся из config + seed. Источником истины для их версии
является `manifest.json` внутри каждой директории.

Фактический прогон и команда воспроизведения находятся в
[`../../evaluation/README.md`](../../evaluation/README.md).
