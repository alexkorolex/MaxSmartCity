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
- Авторизация — Keycloak (штаб/сотрудники, с LDAP-федерацией) + собственный JWT для жителей через бота
- Docker Compose — вся оркестрация (`db`, `redis`, `migrate`, `keycloak`, `backend`, `loki`, `promtail`, `grafana`)

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
| `keycloak` | `KEYCLOAK_PORT` (8080) | IdP для сотрудников, realm `maxsmartcity` импортируется автоматически |

`migrate` — одноразовый сервис без порта, применяет миграции и завершается;
`backend` стартует только после его успешного выполнения.

## ML decision layer

`ml-service` — отдельный stateless Litestar-сервис. Он классифицирует текст обращения,
извлекает наблюдаемые признаки и ранжирует только переданные backend-кандидаты. Результат
остаётся рекомендацией: rule-ranking и неоткалиброванные ответы требуют ручной проверки.

Во время сборки `Dockerfile.ml` воспроизводимо обучает CPU baseline на versioned Gold v2.
Используемые данные являются синтетическими и LLM-assisted; human test пока отсутствует.

Проверочные endpoints:

- `GET http://localhost:${ML_PORT}/health`;
- `GET http://localhost:${ML_PORT}/ready`;
- `GET http://localhost:${ML_PORT}/v1/models`;
- `POST http://localhost:${ML_PORT}/v1/classify`;
- `POST http://localhost:${ML_PORT}/v1/decide`.

Версионированные контракты и OpenAPI находятся в `ml/contracts/backend/v2`.
Backend обращается к сервису через `ML_SERVICE_URL` и предоставляет gateway-методы
`GET /ml/health` и `POST /ml/decide`. При сетевой ошибке gateway возвращает контролируемый
retryable `MODEL_UNAVAILABLE`, не изменяя Report или Incident.

## Авторизация

Два независимых, не пересекающихся способа попасть в систему — под каждый тип
пользователя из задачи:

**Сотрудники** (админ / жилищник / управа, у последних двух — департаменты
со своими сотрудниками через `OrganizationMember.department_id`) хранятся и
аутентифицируются в **Keycloak** (realm `maxsmartcity`, конфиг —
[keycloak/realm-export.json](keycloak/realm-export.json), импортируется
автоматически при первом старте контейнера), но с нашим API работают только
через `src/domains/auth/controllers.py` (`StaffAuthController`, `/auth/staff/*`)
— напрямую к Keycloak никто не ходит:

1. `POST /auth/staff/login` — логин/пароль проксируются в Keycloak
   (`src/security/keycloak.py:login_staff_with_password`), обратно отдаётся
   `{token, refresh_token, expires_in}`. Пароль проходит через бэкенд
   транзитом и нигде не сохраняется.
2. `POST /auth/staff/register` — доступно только с ролью `admin`
   (`require_roles("admin")`). Создаёт пользователя сразу в двух местах: в
   Keycloak через Admin REST API (`src/security/keycloak_admin.py`, логин +
   пароль + realm-роль) и локально в `identity.operator_user`. Организация/
   департамент сюда не входят — привязывайте существующими ручками
   `OrganizationMember` отдельно.
3. `POST /auth/staff/max-id` — любой залогиненный сотрудник (`require_staff()`,
   не только admin) может сам привязать свой MAX-аккаунт для уведомлений.
   Необязательно и никак не участвует в самой авторизации — в отличие от
   жителей, для которых `max_user_id` обязателен и есть основной идентификатор.

Роли `admin`, `housing_worker`, `district_admin` — это realm-роли Keycloak, а
не что-то захардкоженное в коде: `src/security/guards.py` читает их прямо из
`realm_access.roles` в JWT. При первом успешном логине сотрудника (например,
пришедшего через LDAP, а не через `/register`) его локальная запись
`identity.operator_user` создаётся автоматически (`src/security/dependency.py`).

Три тестовых пользователя уже в realm-конфиге (`admin_test`/`housing_test`/
`uprava_test`, пароль = логин) — для локальной проверки без реального LDAP:

```bash
curl -X POST http://localhost:${APP_PORT}/auth/staff/login \
  -d '{"username": "admin_test", "password": "admin_test"}'
```

**LDAP** подключается к Keycloak как User Federation (Keycloak сам ходит в LDAP;
в приложении нет ни строчки LDAP-кода) — настраивается один раз вручную в
Admin Console (`http://localhost:${KEYCLOAK_PORT}/admin`, логин из
`KEYCLOAK_ADMIN`/`KEYCLOAK_ADMIN_PASSWORD`): **User Federation → Add provider →
ldap**, заполнить адрес/bind DN/base DN вашего каталога, затем в **Mappers**
смэппить LDAP-группы на realm-роли `admin`/`housing_worker`/`district_admin`.
Реальных connection-данных LDAP тут нет — заводить свой LDAP-сервер в этой
итерации не входило в задачу.

**Жители** приходят только через бота и никогда не вводят логин/пароль.
Бот — единственный клиент этих ручек, аутентифицируется отдельным
shared-секретом (`BOT_SHARED_SECRET`, заголовок `X-Bot-Secret`), а не сам
житель. Домен `auth` (`src/domains/auth/`) — это две отдельные ручки:

1. `POST /auth/residents/authenticate` — регистрирует/обновляет жителя по
   его `max_user_id` (без выдачи токена);
2. `POST /auth/residents/token` — выдаёт короткоживущий JWT
   (`litestar[jwt]`, `src/security/resident.py`) уже зарегистрированному
   жителю; 404, если `authenticate` для него ещё не вызывался. Разделение
   на два шага позволяет боту перевыпускать токен без повторной регистрации.

```bash
curl -X POST http://localhost:${APP_PORT}/auth/residents/authenticate \
  -H "X-Bot-Secret: ${BOT_SHARED_SECRET}" \
  -d '{"max_user_id": 123456, "username": "ivan", "display_name": "Иван Петров"}'

curl -X POST http://localhost:${APP_PORT}/auth/residents/token \
  -H "X-Bot-Secret: ${BOT_SHARED_SECRET}" \
  -d '{"max_user_id": 123456}'
```

Кто угодно с валидным токеном (сотрудник или житель) может спросить, кто он:
`GET /identity/me`. Роутов, защищённых `require_roles("admin")`, пока немного
(мутации `/identity/departments`) — это демонстрационный охват, остальные
существующие эндпоинты (reports/incidents/geo/...) не тронуты, чтобы не
сломать уже написанные тесты; расширять список защищённых роутов — отдельная
следующая итерация.

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
