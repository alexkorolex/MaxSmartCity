# ML architecture

```text
domain       — stable snapshots, task results, feedback and async event types
application  — use cases, fallback orchestration and input policy
ports        — interfaces for models, backend and ingestion
adapters     — rule baseline, model adapters and dependency stubs
data         — configs, split logic and synthetic world generation
```

Зависимости направлены внутрь: `domain` не импортирует adapters, application работает
через ports, а модели и integrations заменяются без изменения доменных контрактов.

Async находится на границах системы:

```text
backend queue / async HTTP
→ bounded inference queue
→ batcher
→ synchronous model adapter
→ idempotent result event
```

Чистые преобразования, генераторы datasets, metrics и model forward не становятся async.
Настоящий transport и очередь добавляются после согласования с backend.
