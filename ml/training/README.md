# Обучение baseline классификации

Первый воспроизводимый эксперимент обучает multi-label классификатор верхнего уровня:
word/character TF-IDF + One-vs-Rest Logistic Regression. Он работает на CPU и не скачивает
модели или датасеты.

## Быстрый запуск после clone/checkout

Windows PowerShell:

```powershell
uv sync --locked --group dev
.\ml\scripts\train_category_baseline.ps1
```

Linux/macOS:

```bash
uv sync --locked --group dev
sh ml/scripts/train_category_baseline.sh
```

Прямая команда:

```bash
uv run --locked python -m maxsmartcity.ml.training.cli \
  --config ml/configs/training/category-tfidf-logreg.v2.json
```

Артефакт создаётся в `ml/artifacts/category-tfidf-logreg-v2/` и не попадает в Git:

- `model.joblib` — checkpoint, загружать только из доверенного локального источника;
- `manifest.json` — dataset/config hashes, taxonomy, seed, commit и версия модели;
- `metrics.json` — validation/test метрики, per-class confusion matrices, calibration,
  risk-coverage и latency;
- `experiment.json` — полный config, версии runtime и ограничения.

Порог `ABSTAIN` выбирается только на validation. Test используется один раз для итоговой оценки.
Перед официальным benchmark статус Gold должен быть переведён из
`REVIEWED_PENDING_TEAM_SIGNOFF` в `FROZEN` участником команды.

Контрольный локальный прогон Gold v2: validation macro-F1 `0.8015`, test macro-F1 `0.9872`,
test top-1 accuracy `0.9828`, test coverage `0.9828`. Разрыв validation/test и высокие значения
объясняются небольшим синтетическим набором и неодинаковой сложностью scenario-splits. Это smoke
baseline, а не доказательство качества на реальных обращениях.

## Границы эксперимента

Baseline обучает только верхнеуровневую `primary_category` на записях с routing=`ACCEPT`.
Подкатегории, extraction, incident retrieval/reranking и Jev-like decision model требуют отдельных
датасетов и не входят в этот checkpoint.
