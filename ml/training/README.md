# Training

`TODO[model]`: training-код добавляется после приёмки synthetic и Gold datasets.

Обязательные входы будущей команды обучения:

- immutable dataset manifest/hash;
- taxonomy version;
- experiment config;
- random seed;
- выбранная base model revision.

Результат должен соответствовать `contracts/artifacts/v1/model-manifest.schema.json`.
