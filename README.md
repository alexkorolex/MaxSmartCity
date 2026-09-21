# MaxSmartCity

Backend на [Litestar](https://litestar.dev/): учёт городских инцидентов и заявок
(identity, geo, reports, incidents, collaboration, audit, infrastructure).

## Стек

- Python 3.12, Litestar + Granian (несколько воркеров в одном контейнере)
- PostgreSQL + PostGIS, SQLAlchemy / Advanced Alchemy, Alembic-миграции
- Redis — нативное кеширование ответов через `litestar.stores`
- Логи — JSON (structlog), пригодны для сбора Loki/Promtail
- Grafana + Loki + Promtail — просмотр логов всех контейнеров
- Prometheus-метрики (`/metrics`)
- Docker Compose — вся оркестрация (`db`, `redis`, `migrate`, `backend`, `loki`, `promtail`, `grafana`)

## Быстрый старт

Нужны Docker и [uv](https://docs.astral.sh/uv/).

```bash
uv sync --locked --group dev
uv run litestar up
```

Команда `litestar up`:

1. создаёт `.env` из `.env.example`, если его ещё нет, либо дописывает в уже
   существующий `.env` переменные, которых там не хватает (ничего не
   перезаписывает и не удаляет);
2. поднимает весь docker-compose стек (`docker compose up -d`), включая
   одноразовый сервис `migrate`, который применяет alembic-миграции —
   с нуля БД тоже поднимется наполненной, без ручных действий.

Полезные флаги: `litestar up --build` (пересобрать образы), `litestar up --no-detach`
(держать процесс на переднем плане). Это обычная Litestar CLI-команда
(`src/cli.py`, регистрируется через `CLIPlugin`), доступна везде, где доступен
сам проект — `litestar --help` покажет её среди остальных.

> `.env` — локальный файл с секретами/портами, в git не попадает
> (см. `.gitignore`). `.env.example` — актуальный список переменных, храните
> его в актуальном состоянии при добавлении новых сервисов.

## Сервисы и порты

По умолчанию (переопределяются через `.env`):

| Сервис | Порт | Назначение |
|---|---|---|
| `backend` | `APP_PORT` (8000) | API, `/schema` — Swagger, `/metrics` — Prometheus |
| `db` | `DB_PORT` (5432) | PostgreSQL + PostGIS |
| `redis` | `REDIS_PORT` (6379) | кеш ответов |
| `grafana` | `GRAFANA_PORT` (3000) | UI, логин из `GRAFANA_USER`/`GRAFANA_PASSWORD` |
| `loki` | `LOKI_PORT` (3100) | хранилище логов (datasource уже прописан в Grafana) |

`migrate` — одноразовый сервис без порта, применяет миграции и завершается;
`backend` стартует только после его успешного выполнения.

## Разработка без Docker

Нужны локальные Postgres+PostGIS и Redis (или те же `db`/`redis` из
docker-compose, поднятые отдельно):

```bash
uv run litestar run
```

Настройки берутся из `.env` (см. `.env.example`) — `DATABASE_URL`, `REDIS_URL`,
`LITESTAR_APP` и т.д. Приложение подхватывает `.env` автоматически.

## Миграции

```bash
uv run alembic upgrade head
uv run alembic revision -m "..."
```

В docker-compose это делает сервис `migrate` при каждом `docker compose up`
(идемпотентно, no-op если БД уже на актуальной версии).

## Проверки и pre-commit

После клонирования установите зависимости и Git-хук:

```bash
uv sync --locked --group dev
uv run --locked pre-commit install
```

[pre-commit](https://pre-commit.com/) перед каждым коммитом запускает проверки
всего проекта: `ruff check .`, `ruff format --check .`, `ty check` и `pytest`.
Ошибка любой проверки блокирует коммит. Версии инструментов берутся из `uv.lock`;
хуки не исправляют код автоматически.

Запуск всех проверок вручную:

```bash
uv run --locked pre-commit run --all-files
```

Запуск только тестов:

```bash
uv run --locked pytest
```

Исправление замечаний Ruff и форматирование:

```bash
uv run --locked ruff check --fix .
uv run --locked ruff format .
```
