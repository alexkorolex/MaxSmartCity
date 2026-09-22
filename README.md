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
- Авторизация — Keycloak (штаб/сотрудники, с LDAP-федерацией) + собственный JWT для жителей через бота MAX
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
   с нуля БД тоже поднимется наполненной, без ручных действий;
3. одноразовый сервис `ingest` загружает пилотный справочник домов и организаций.

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

`migrate` и `ingest` — одноразовые сервисы без портов; `backend` стартует после их
успешного выполнения. Повторный запуск `ingest` не создаёт дубли.

## Ingestion: дома и организации

Ingestion загружает подготовленные JSON-файлы непосредственно в общую PostgreSQL.
Дома сохраняются в `geo.address` и `geo.house`: `geo.house.id` — стабильный
`house_id`, на который уже ссылаются Reports и Incidents. Координаты и
административная область необязательны. Справочные организации хранятся в
`ingestion.organization` отдельно от `identity.organization` (это зарегистрированные
операторские организации). Подтверждённые источником связи находятся в
`ingestion.house_organization`; назначений Incidents импорт не создаёт.

При обычном `docker compose up -d --build` сервис `ingest` после миграции загружает
`ingestion/data/bryansk.json`, `ingestion/data/bryansk_cian.json` и
`ingestion/data/bakhchysarai.json`. Вручную после
запуска БД и миграций:

```bash
uv run --locked python -m src.domains.ingestion ingestion/data/bryansk.json
uv run --locked python -m src.domains.ingestion ingestion/data/bryansk_cian.json
uv run --locked python -m src.domains.ingestion ingestion/data/bakhchysarai.json
```

Команда использует `DATABASE_URL` из окружения или `.env` и печатает ID запуска,
число созданных/обновлённых записей и ошибок. Повторить импорт внутри Docker:

```bash
docker compose run --rm ingest
```

Формат файла — объект JSON версии `1` с `source` (`code`, `data_kind`: `REAL` или
`DEMO`, `retrieved_at` с часовым поясом, опционально `url`) и массивами `houses`,
`organizations`, `links`. Дом: `key`, `city`, `street`, `house_number`, опционально
`formatted`, `external_id`, пара `latitude`/`longitude`. Организация: `key`, `name`,
`type`, опционально `external_id`. Связь: `house_key`, `organization_key`,
`relationship`. Пример — файлы выше. Ключи стабильны **в пределах источника**:
повторный импорт обновляет запись с тем же ключом и сохраняет её UUID. Новый ключ
дома с тем же точным адресом сопоставляется с уже существующим домом только при
однозначном совпадении. Неизвестная УК остаётся отсутствующей; автоматического
назначения по городу нет. Файл ограничен 5 МиБ.

`ingestion.source`, `house_source`, `organization_source` и `house_organization`
хранят происхождение и дату получения. `ingestion.run` и `ingestion.error`
позволяют проверить результат и исправить отдельные ошибочные строки. Импорт
проходит в транзакции с точками сохранения для строк: при сбое всей операции ранее
опубликованные данные остаются доступны; одна неверная строка не блокирует другие.
Более старый `retrieved_at` не перезаписывает новую запись того же источника.
Отсутствие записи в очередном файле не удаляет дом или связь.
Параллельные импорты выполняются последовательно в БД, чтобы два источника не
создали два `house_id` для одного точного адреса. При совпадении адреса с несколькими
домами или попытке перенести уже известный дом на адрес другого запись попадает
в `ingestion.error` и не связывается с чужим домом. При совпадении дома из разных
источников атрибуты `REAL` имеют приоритет над `DEMO`; внутри одного класса более
старая дата получения не перезаписывает более новую.

Интеграционные тесты требуют отдельную пустую PostgreSQL/PostGIS базу. После её
создания задайте `TEST_DATABASE_URL` и запустите:

```bash
uv run --locked pytest -q tests/integration/test_ingestion.py tests/test_ingestion_validation.py
```

Тесты применяют миграции и проверяют повторный и параллельный импорт, UUID дома
и ссылку Report после обновления адреса, старую выгрузку, неоднозначные адреса,
ошибки строк (в том числе недопустимые символы), происхождение данных, приоритет
`REAL` и откат при неожиданном сбое. Используйте только
одноразовую тестовую БД: тесты записывают в неё данные.

Backend может читать справочник обычным SQL:

```sql
SELECT h.id AS house_id, a.formatted, a.city, a.street, a.house_number,
       h.external_id, ST_Y(h.point::geometry) AS latitude,
       ST_X(h.point::geometry) AS longitude
FROM geo.house h JOIN geo.address a ON a.id = h.address_id
WHERE a.city = 'Брянск';

SELECT o.id AS organization_id, o.name, o.type, ho.relationship,
       s.code AS source, s.data_kind, ho.retrieved_at
FROM ingestion.house_organization ho
JOIN ingestion.organization o ON o.id = ho.organization_id
JOIN ingestion.source s ON s.id = ho.source_id
WHERE ho.house_id = :house_id;
```

Пилотный набор содержит четыре реальных адреса и три УК по открытым справочным
страницам: [Брянск, Евдокимова 8](https://nashdom.info/building/d-288432),
[Брянск, Евдокимова 10](https://www.cian.ru/dom/bryanskaya-oblast-bryansk-ulica-evdokimova-dom-10-1754812/),
[Бахчисарай, Мира 9](https://www.cian.ru/dom/krym-bahchisaray-ulica-mira-dom-9-3958404/),
[Бахчисарай, Мира 3](https://krym.cian.ru/dom/krym-bahchisaray-ulica-mira-dom-3-2733559/).
Связи с УК указаны на этих же страницах. `REAL` означает полученные из
опубликованных справочников сведения, не живое подключение к официальной системе.
Данные просмотрены 22 сентября 2026 года; текущее обслуживание домов следует
уточнять у первичного источника. Координаты и ФИАС в этом наборе отсутствуют.

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

**Жители** приходят только через бота MAX и никогда не вводят логин/пароль.
Три ручки в `src/domains/auth/controllers.py` (`ResidentAuthController`,
`/auth/residents/*`):

1. `POST /auth/residents/authenticate` — вызывается ботом (заголовок
   `X-Bot-Secret`), регистрирует/обновляет жителя по его `max_user_id`, без
   выдачи токена;
2. `POST /auth/residents/token` — тоже только бот; выдаёт короткоживущий JWT
   (`litestar[jwt]`, `src/security/resident.py`) уже зарегистрированному
   жителю по `max_user_id`; 404, если `authenticate` ещё не вызывался;
3. `POST /auth/residents/login` — вызывается браузером самого жителя, без
   `X-Bot-Secret`. Принимает одноразовый код, который жителю прислал бот в
   чате (см. ниже), и обменивает его на тот же JWT. Код — сам по себе
   credential, поэтому эта ручка не требует секрета бота.

```bash
curl -X POST http://localhost:${APP_PORT}/auth/residents/authenticate \
  -H "X-Bot-Secret: ${BOT_SHARED_SECRET}" \
  -d '{"max_user_id": 123456, "username": "ivan", "display_name": "Иван Петров"}'

curl -X POST http://localhost:${APP_PORT}/auth/residents/token \
  -H "X-Bot-Secret: ${BOT_SHARED_SECRET}" \
  -d '{"max_user_id": 123456}'

curl -X POST http://localhost:${APP_PORT}/auth/residents/login \
  -d '{"code": "<код из чата с ботом>"}'
```

Кто угодно с валидным токеном (сотрудник или житель) может спросить, кто он:
`GET /identity/me`. Роутов, защищённых `require_roles("admin")`, пока немного
(мутации `/identity/departments`) — это демонстрационный охват, остальные
существующие эндпоинты (reports/incidents/geo/...) не тронуты, чтобы не
сломать уже написанные тесты; расширять список защищённых роутов — отдельная
следующая итерация.

## MAX-бот: вход жителей через мессенджер

Источник правды по MAX Bot API — [etc/max_api/](etc/max_api/)
(`MAX_API_AGENT_CONTEXT.md`, `MAX_WEBHOOK_IMPLEMENTATION.md`, официальная
OpenAPI-схема). Реализация в `src/max_bot/`:

- `client.py` — тонкий `aiohttp`-клиент MAX Bot API (`platform-api2.max.ru`,
  `Authorization: <token>` без `Bearer`, без токена в query — как требует
  документация);
- `controllers.py` — `POST /webhook/max`, единственная публичная ручка,
  закрыта гвардом `require_max_webhook_secret()` (constant-time сравнение
  `X-Max-Bot-Api-Secret`), дедуп по составному ключу события (Redis, TTL 24ч
  — у `Update` нет единого id, ключ собирается из полей конкретного
  сабтайпа) — событие помечается обработанным только при успехе, чтобы MAX
  мог повторить доставку при реальном сбое;
- `handlers.py` — бизнес-логика: `bot_started`/сообщение `/login` находят
  или создают `identity.resident` (`ResidentService.upsert_by_max_user_id`,
  общий код с `/auth/residents/authenticate`) и присылают в чат одноразовый
  код (`dedup.create_login_code`, Redis, TTL 5 мин, одноразовый) —
  который дальше обменивается на JWT через `POST /auth/residents/login`;
- `cli.py` — `litestar max-subscribe` / `max-subscriptions` / `max-unsubscribe`,
  управление Webhook-подпиской в MAX через ту же Litestar CLI-команду,
  что и `litestar up` (`src/cli.py`).

Ключевой сценарий: пользователь жмёт Start (или пишет `/login`) → бот
регистрирует его как `Resident` → присылает код → пользователь вводит код на
сайте → сайт вызывает `POST /auth/residents/login` → получает JWT.

```bash
# Однократно после деплоя (нужен публичный HTTPS URL, см. MAX_WEBHOOK_PUBLIC_URL):
uv run litestar max-subscribe
uv run litestar max-subscriptions
```

**Важный нюанс окружения**, не связанный с самим MAX API: сертификат
`platform-api2.max.ru` выпущен CA Минцифры («Russian Trusted Root/Sub CA»),
которого нет в стандартном trust store большинства базовых образов —
документация прямо требует добавить его вручную. Файлы уже лежат в
[etc/max_api/certs/](etc/max_api/certs/) и подключены в [Dockerfile](Dockerfile)
(`update-ca-certificates` на этапе сборки). Перевыпустить их (например, если
Минцифры однажды ротирует CA) — `uv run litestar max-fetch-certs`, скачивает
актуальные `russian_trusted_{root,sub}_ca.crt` с `gu-st.ru` и перезаписывает
файлы в том же месте; после этого нужно пересобрать образ backend. Проверено
вживую реальным TLS-запросом к `platform-api2.max.ru`. TLS-проверка
никогда не отключается — так и должно оставаться.

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
