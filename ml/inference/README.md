# Inference

Транспорт пока не реализован. Контракты лежат в `contracts/backend/v2`.

Планируемый runtime:

- async Litestar HTTP boundary;
- bounded queue и micro-batching;
- synchronous model adapters;
- per-item batch errors;
- timeout и graceful fallback;
- `/health`, `/ready`, `/v1/models`;
- метрики latency, batch size, errors и abstain ratio.
