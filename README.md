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
- Docker Compose — вся оркестрация Backend, ML, resident/admin web, хранилищ, миграций,
  seed-данных, авторизации и наблюдаемости

## Архитектура

```text
MAX Bot ─┐
Mini App ├─> Backend (`src/domains`) ─> PostgreSQL/PostGIS, Redis, MinIO
Admin UI ┘             │
                      ├─HTTP─> ML service (`src/ml`)
                      └─> MAX API / Keycloak

Ingestion (`src/domains/ingestion`) ─> общие geo/ingestion-таблицы
Prometheus + Tempo + Loki ─> Grafana
```

`src/ml` — изолированный runtime ML-сервиса. `src/domains/ml` — только Backend gateway
и преобразование доменных данных в HTTP-контракт; смешивать эти слои нельзя.

## Быстрый старт

Нужны Docker и [uv](https://docs.astral.sh/uv/).

```bash
uv sync --locked
uv run litestar up
```

Зависимости разделены на группы в `pyproject.toml`, чтобы каждый образ получал только своё:

| Группа | Кому нужна | Где ставится |
|---|---|---|
| `backend` | API, миграции, импорт данных, фоновые задачи | образ `Dockerfile` (`backend`, `migrate`, `ingest`) |
| `ml` | ML-сервис: инференс, обучение baseline, FastEmbed | образ `Dockerfile.ml` |
| `ml-data` | генераторы синтетических данных (`src/ml/data`) | только локально |
| `dev` | тесты и линтеры | только локально |

Локально `uv sync` ставит все группы. Новую зависимость добавляйте в группу того контейнера, который её
импортирует, например `uv add --group backend <пакет>`.

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
| `ml-service` | `ML_PORT` (8001) | ML HTTP API, `/health`, `/ready`, `/v1/*` |
| `frontend` | `FRONTEND_PORT` (8082) | Mini App жителя |
| `admin` | `ADMIN_PORT` (8083) | Рабочее место сотрудников |
| `db` | `DB_PORT` (5432) | PostgreSQL + PostGIS |
| `redis` | `REDIS_PORT` (6379) | кеш ответов |
| `minio` | `MINIO_PORT` (9000) | S3-совместимое хранилище вложений |
| `grafana` | `GRAFANA_PORT` (3000) | UI, логин из `GRAFANA_USER`/`GRAFANA_PASSWORD` |
| `loki` | `LOKI_PORT` (3100) | хранилище логов (datasource уже прописан в Grafana) |
| `prometheus` | `PROMETHEUS_PORT` (9090) | сбор метрик |
| `tempo` | `TEMPO_PORT` (3200) | хранилище трассировок |
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
`ingestion/data/bryansk.json`, `ingestion/data/bryansk_cian.json`,
`ingestion/data/bakhchysarai.json` и `ingestion/data/gis_zkh_pilot.json`. Вручную после
запуска БД и миграций:

```bash
uv run --locked python -m src.domains.ingestion ingestion/data/bryansk.json
uv run --locked python -m src.domains.ingestion ingestion/data/bryansk_cian.json
uv run --locked python -m src.domains.ingestion ingestion/data/bakhchysarai.json
uv run --locked python -m src.domains.ingestion ingestion/data/gis_zkh_pilot.json
```

Команда использует `DATABASE_URL` из окружения или `.env` и печатает ID запуска,
число созданных/обновлённых записей и ошибок. Повторить импорт внутри Docker:

```bash
docker compose run --rm ingest
```

Формат файла — объект JSON версии `1` с `source` (`code`, `data_kind`: `REAL` или
`DEMO`, `retrieved_at` с часовым поясом, опционально `url`) и массивами `houses`,
`organizations`, `links`. Дом: `key`, `city`, `street`, `house_number`, опционально
`formatted`, `external_id`, пара `latitude`/`longitude`, `district` (район) и `okrug`
(административный округ — для городов вроде Москвы). По `city` дом попадает в
территорию-город, по `okrug`/`district` — во вложенные деления; недостающие деления
создаются автоматически. Без `district` дом остаётся на уровне города, а уже сделанная в
панели разметка не сбрасывается. Организация: `key`, `name`,
`type`, опционально `external_id`, `inn`, `ogrn`, массив `phones`, `email`,
`website` и объект `provenance`. Телефоны приводятся к международному формату,
email — к нижнему регистру. Связь: `house_key`, `organization_key`,
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

### Пилот ГИС ЖКХ

Для четырёх адресов пилота есть отдельный источник `gis-zkh-public-pilot`.
Его данные взяты из ручной выгрузки публичного реестра объектов жилищного фонда
ГИС ЖКХ. Система не подключается к ГИС ЖКХ во время работы: в репозитории лежат
только итоговый JSON, небольшой обезличенный CSV-образец и манифест архива;
исходный ZIP в Git не добавляется.

Порядок обновления снимка:

1. Откройте публичный [реестр объектов жилищного фонда](https://dom.gosuslugi.ru/#!/houses),
   нажмите «Скачать» и дождитесь архива (`tar.gz` на дату этого снимка). При необходимости проверьте реквизиты УК
   в [реестре управляющих организаций и решений](https://cdn.dom.gosuslugi.ru/webhelp/new/topics/public_part/management_company_and_solution_list_och/t_navigate-och.html).
2. Сохраните архив вне рабочей копии и зафиксируйте его имя, дату получения,
   размер и SHA-256. Не добавляйте полный архив в Git.
3. Постройте снимок и манифест, указав фактическое время получения архива:

   ```bash
   uv run --locked python -m src.domains.ingestion.gis_zkh \
     --archive C:/Downloads/gis-zkh-houses.tar.gz \
     --retrieved-at 2026-09-22T20:35:00+03:00 \
     --output ingestion/data/gis_zkh_pilot.json \
     --manifest ingestion/data/gis_zkh_manifest.json
   ```

4. Просмотрите `not_found` и таблицу расхождений в `ingestion/data/`. Статус
   `NOT_FOUND` означает, что запись не попала в выгрузку; импорт не изменяет
   ранее загруженный дом. Не сопоставляйте УК по похожему названию.
5. Импортируйте итоговый JSON обычной командой:

   ```bash
   uv run --locked python -m src.domains.ingestion ingestion/data/gis_zkh_pilot.json
   ```

### Полная выгрузка ГИС ЖКХ (десятки тысяч домов)

Большие файлы в том же формате — например, `var/gis_zkh_bryansk_bakhchysarai.json`
(все дома Брянска и Бахчисарая, ~34 тыс.; каталог `var/` не хранится в Git) —
загружаются пакетным импортёром. Обычная команда их не примет: у неё лимит 5 МиБ.

```bash
# проверить все строки и посмотреть разбиение на пачки, ничего не записывая
uv run --locked python -m src.domains.ingestion.bulk var/gis_zkh_bryansk_bakhchysarai.json --dry-run
# загрузить (DATABASE_URL берётся из .env; миграции должны быть применены)
uv run --locked python -m src.domains.ingestion.bulk var/gis_zkh_bryansk_bakhchysarai.json
```

Правила валидации, сопоставления адресов и provenance те же, что у обычного
импорта; файл лишь делится на пачки (`--batch-size`, по умолчанию 2000 строк) —
каждая в своей транзакции и со своей записью `ingestion.run`: сначала организации,
потом дома, потом связи. Все записи — идемпотентные upsert-ы, поэтому прерванную
загрузку достаточно запустить заново. Между этапами выполняется `ANALYZE`, иначе
повторный прогон по «свежим» таблицам шёл в разы медленнее. `--only-linked`
загружает только дома, у которых в файле есть управляющая организация (в выгрузке
ГИС ЖКХ у большинства домов способ управления «Не выбран»). Полная загрузка ~34 тыс.
домов занимает около полутора минут. Отклонённые строки — в `ingestion.error`
(номер строки считается внутри пачки, сама строка лежит в `payload`).

Одна и та же УК из разных источников (cian с контактами, ГИС ЖКХ с ОГРН)
показывается жителю одной карточкой: совпадение по ОГРН/ИНН, а без реквизитов —
по названию без организационно-правовой формы и кавычек.

Адаптер читает CSV внутри ZIP потоково и выбирает только Брянск, ул. Евдокимова,
дома 8 и 10, а также Бахчисарай, ул. Мира, дома 9 и 3. Он приводит `ул.` к
`улица` и варианты корпуса к одной записи, не объединяя разные номера домов.
Для найденных домов сохраняются идентификаторы ГИС ЖКХ и ФИАС, канонический
адрес, состояние, способ управления и член архива. Для УК сохраняются только
явно указанные в выгрузке ID, ИНН и ОГРН; для связи — основание и период, если
они присутствуют. Поля находятся в provenance-таблицах `ingestion.house_source`,
`ingestion.organization_source` и `ingestion.house_organization`; `house_id`
остаётся прежним при повторной загрузке.

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
       os.phones, os.email, os.website,
       s.code AS source, s.data_kind, ho.retrieved_at
FROM ingestion.house_organization ho
JOIN ingestion.organization o ON o.id = ho.organization_id
JOIN ingestion.source s ON s.id = ho.source_id
JOIN ingestion.organization_source os
  ON os.source_id = ho.source_id AND os.organization_id = ho.organization_id
WHERE ho.house_id = :house_id;
```

Для карты фронтенд получает готовый GeoJSON без зависимости от Python-библиотек:

```http
GET /geo/houses/geojson?city=Брянск&limit=1000&offset=0
```

В ответе есть адреса, доступные реальные координаты, число активных обращений и число
активных инцидентов. Дом без координаты остаётся в выдаче с `geometry=null`. Контуры и
площади не подменяются прямоугольниками: пока источник
их не предоставляет, соответствующие поля равны `null`, а
`footprint_area_available=false`. Подробный контракт и правила слоёв описаны в
`docs/frontend-map-contract.md`.

Пилотный набор содержит четыре реальных адреса и три УК по открытым справочным
страницам: [Брянск, Евдокимова 8](https://nashdom.info/building/d-288432),
[Брянск, Евдокимова 10](https://www.cian.ru/dom/bryanskaya-oblast-bryansk-ulica-evdokimova-dom-10-1754812/),
[Бахчисарай, Мира 9](https://www.cian.ru/dom/krym-bahchisaray-ulica-mira-dom-9-3958404/),
[Бахчисарай, Мира 3](https://krym.cian.ru/dom/krym-bahchisaray-ulica-mira-dom-3-2733559/).
Связи с УК указаны на этих же страницах. `REAL` означает полученные из
опубликованных справочников сведения, не живое подключение к официальной системе.
Данные просмотрены 22 сентября 2026 года; текущее обслуживание домов следует
уточнять у первичного источника. Координаты и ФИАС в этом наборе отсутствуют.

## Incident Core: основной MVP-сценарий

Incident Core проводит обращение от регистрации до подтверждения результата. В
миграции заведён фиксированный каталог, совпадающий с ML taxonomy: водоснабжение,
электроснабжение, дом, дороги и дворы, отходы, аварийная ситуация, городская
инфраструктура и «Другое». Клиент передаёт выбранную категорию и
`house_id` в `POST /reports/intake`; операция атомарно создаёт `Report`, ищет похожий
активный `Incident` в том же доме и категории и либо связывает обращение, либо создаёт
новый инцидент. Для статических категорий решение принимает детерминированная политика
по числу активных кандидатов. Для «Другое» автоматическая привязка запрещена:
обращение переводится в `NEEDS_CLARIFICATION`, после чего пользователь подтверждает
семантическую рекомендацию ML или создаёт отдельный инцидент. Incident Core не анализирует
свободный текст регулярными выражениями или n-граммами.

Основные ручки:

- `GET /reports/categories` — каталог проблем;
- `POST /reports/intake`, `GET /reports/mine` — приём и история обращений жителя;
- `POST /reports/{id}/grouping-decision` — подтверждение предложенного инцидента или
  создание отдельного при неоднозначности;
- `GET /incidents/{id}/card` — операторская карточка с домами, обращениями,
  назначениями, спорами и историей;
- `POST /incidents/{id}/status` — переход Incident по машине состояний;
- `POST /collaboration/assignments` и
  `POST /collaboration/assignments/{id}/status` — назначение организации и ход работ;
- `POST /incidents/{id}/resolution-feedback` — подтверждение устранения или сообщение,
  что проблема сохраняется.

Повторный `source_external_id` с тем же payload идемпотентен, а с изменённым payload
отклоняется. Один Report не может иметь две активные связи с Incident; одно активное
назначение организации в одной роли защищено уникальным индексом. Переход в
`RESOLVED` запрещён, пока не завершены все обязательные назначения. Отрицательный
ответ создаёт `ResolutionDispute`; три уникальных жителя за 30 минут переводят Incident
в `RESOLUTION_DISPUTED`. Все ключевые изменения записывают outbox-события в той же
транзакции.

Текущие ограничения MVP: справочные ingestion-организации не назначаются автоматически,
потому что они намеренно отделены от операторских `identity.organization`; доставка
уведомлений требует настроенного MAX-бота или канала организации; классификация ML не
является обязательной зависимостью intake — категорию подтверждает пользователь.

## ML decision layer

Реализация ML-сервиса находится в отдельном верхнеуровневом слое `src/ml`.
Backend-интеграция с ним изолирована в `src/domains/ml`: доменный backend не импортирует
runtime модели и общается с сервисом только по версионированному HTTP-контракту.

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
- `POST http://localhost:${ML_PORT}/v1/decide`;
- `POST http://localhost:${ML_PORT}/v1/grouping:recommend`.

Версионированные контракты и OpenAPI находятся в `ml/contracts/backend/v2`.
Backend обращается к сервису через `ML_SERVICE_URL` и предоставляет gateway-методы
`GET /ml/health`, `POST /ml/decide` и `POST /ml/grouping/recommend`. Семантическая
рекомендация используется только для категории «Другое» и не меняет Incident Core.
При сетевой ошибке gateway возвращает контролируемый retryable `MODEL_UNAVAILABLE`,
не изменяя Report или Incident.

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
   `{token, refresh_token, expires_in, refresh_expires_in}`. Пароль проходит
   через бэкенд транзитом и нигде не сохраняется.
   `POST /auth/staff/refresh` `{refresh_token}` выдаёт новую пару токенов без
   пароля, `POST /auth/staff/logout` `{refresh_token}` закрывает сессию в
   Keycloak. Access token живёт 5 минут, сессия (и refresh token) — 24 часа
   (`accessTokenLifespan`, `ssoSessionIdleTimeout`, `ssoSessionMaxLifespan` в
   realm-конфиге); админка сама обновляет токен при 401, так что заново входить
   нужно раз в сутки. Realm импортируется только при первом старте Keycloak — в
   уже существующем realm эти сроки меняются в Admin Console (**Realm settings →
   Sessions / Tokens**) или через Admin REST API.
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
# После деплоя задайте публичный HTTPS URL в MAX_WEBHOOK_PUBLIC_URL. Backend
# попробует зарегистрировать его при запуске; эти команды позволяют сделать то же вручную:
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

## Продакшн и CI/CD

Прод поднимается из [docker-compose.prod.yml](docker-compose.prod.yml): наружу открыт только
Traefik (80/443, сертификаты Let's Encrypt, редирект HTTP → HTTPS). Поддомен сервиса совпадает
с именем контейнера:

| Адрес | Сервис |
|---|---|
| `https://frontend.<DOMAIN>` | приложение жителя (+ `/webhook/max`, файлы MinIO) |
| `https://admin.<DOMAIN>` | админ-панель |
| `https://backend.<DOMAIN>` | API |
| `https://keycloak.<DOMAIN>` | Keycloak |
| `https://monitoring.<DOMAIN>` | Grafana |

`db`, `redis`, `minio`, `ml-service`, `prometheus`, `loki`, `tempo` доступны только внутри
docker-сети. Для каждого поддомена нужна A-запись (или `*.<DOMAIN>`) на IP сервера.

Пайплайн [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml) выполняется на
self-hosted runner, установленном на прод-сервере:

1. на PR и push в `main` — ruff, ty, pytest, ESLint/stylelint, `tsc`, тесты frontend и admin
   (кеш uv и npm через GitHub Actions cache);
2. на push в `main` — сборка образов `maxsmartcity/<сервис>:<sha>` (слои кешируются BuildKit
   на runner'е, старые образы и кеш старше `BUILD_CACHE_TTL` чистятся после успешного деплоя),
   генерация `$DEPLOY_DIR/.env` из Variables и Secrets окружения `main`,
   `docker compose up` и ожидание healthcheck'ов всех сервисов;
3. после успешного деплоя — создание главного администратора (`STAFF_ADMIN_LOGIN`,
   роль `admin`) через `POST /auth/staff/register` с `X-Bootstrap-Secret`: пользователь
   заводится в Keycloak и в `identity.operator_user`. Если он уже есть (HTTP 409), шаг
   ничего не делает; пароль существующего админа не меняется;
4. затем — загрузка домов Брянска и Бахчисарая в БД: JSON скачивается по
   `HOUSES_DATASET_URL` и импортируется пакетным импортёром `src.domains.ingestion.bulk`
   (одноразовый сервис `houses-import`, профиль `import`). Если файл не изменился с прошлого
   импорта (сравнивается SHA-256), шаг пропускается; принудительно — ручной запуск workflow
   с галочкой `force_houses_import`. Импорт идемпотентен, упавший можно просто перезапустить;
5. если деплой не поднялся — логи контейнеров, сборки и проверок (секреты вырезаются)
   сохраняются артефактом запуска и кратко выводятся в summary, затем стек откатывается
   на предыдущий тег. Упавшие проверки тоже сохраняют свои логи артефактом.

Variables и Secrets заводятся в GitHub: Settings → Environments → `main`. Любая Variable или
Secret окружения попадает в `.env` на сервере, так что новую переменную достаточно завести
в GitHub и сослаться на неё в `docker-compose.prod.yml`. Шаблон со значениями по умолчанию —
[.env.prod.example](.env.prod.example).

**Variables** (`vars`) — несекретные настройки:

| Переменная | Обязательна | По умолчанию | Назначение |
|---|---|---|---|
| `DOMAIN` | да | — | общий домен, сервисы доступны на `<контейнер>.<DOMAIN>` |
| `ACME_EMAIL` | да | — | e-mail для Let's Encrypt |
| `DB_USER` | да | — | пользователь PostgreSQL |
| `DB_NAME` | да | — | база приложения |
| `MINIO_ROOT_USER` | да | — | пользователь MinIO |
| `KEYCLOAK_ADMIN` | да | — | администратор Keycloak |
| `GRAFANA_USER` | да | — | администратор Grafana |
| `KEYCLOAK_REALM` | нет | `maxsmartcity` | realm Keycloak |
| `KEYCLOAK_CLIENT_ID` | нет | `maxsmartcity-backend` | клиент backend в Keycloak |
| `KEYCLOAK_AUDIENCE` | нет | `maxsmartcity-backend` | `aud` в токенах |
| `KEYCLOAK_DB_NAME` | нет | `keycloak` | база Keycloak |
| `WEB_CONCURRENCY` | нет | `2` | воркеры backend |
| `ML_REQUEST_TIMEOUT_SECONDS` | нет | `5` | таймаут запросов к ML |
| `ML_MAX_INPUT_CHARACTERS` | нет | `4000` | лимит текста для ML |
| `BACKGROUND_JOBS_INTERVAL_SECONDS` | нет | `30` | период фоновых задач, `0` — выключить |
| `MAX_API_BASE_URL` | нет | `https://platform-api2.max.ru` | MAX API |
| `MAX_WEBHOOK_PUBLIC_URL` | нет | `https://frontend.<DOMAIN>/webhook/max` | webhook бота |
| `WEB_APP_LOGIN_URL` | нет | `https://frontend.<DOMAIN>/auth/max` | страница входа жителя |
| `ADMIN_PANEL_URL` | нет | `https://admin.<DOMAIN>` | ссылка в письмах сотрудникам |
| `CORS_ALLOWED_ORIGINS` | нет | — | доп. origin'ы для API |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_STARTTLS`, `SMTP_SSL` | нет | `SMTP_PORT=587`, `SMTP_STARTTLS=true` | почта |
| `PROMETHEUS_RETENTION` | нет | `15d` | срок хранения метрик |
| `TRAEFIK_LOG_LEVEL` | нет | `INFO` | уровень логов Traefik |
| `ACME_CA_SERVER` | нет | боевой Let's Encrypt | staging CA для отладки сертификатов |
| `DEPLOY_DIR` | нет | `/opt/maxsmartcity` | каталог деплоя на сервере |
| `COMPOSE_PROJECT_NAME` | нет | `maxsmartcity` | имя compose-проекта |
| `IMAGE_PREFIX` | нет | `maxsmartcity` | префикс имён образов |
| `DEPLOY_WAIT_TIMEOUT` | нет | `900` | сколько секунд ждать healthcheck'и |
| `BUILD_CACHE_TTL` | нет | `336h` | возраст кеша BuildKit для очистки |
| `LOG_RETENTION_DAYS` | нет | `30` | срок хранения артефактов с логами |
| `HOUSES_DATASET_URL` | нет | `https://storage.yandexcloud.net/massivehousesbryansk/gis_zkh_bryansk_bakhchysarai.json` | откуда скачивать JSON с домами |
| `STAFF_ADMIN_LOGIN` | нет | — | логин главного администратора, без него шаг пропускается |
| `STAFF_ADMIN_DISPLAY_NAME` | нет | `Главный администратор` | отображаемое имя администратора |
| `STAFF_ADMIN_EMAIL` | нет | — | e-mail администратора |
| `HOUSES_IMPORT_ENABLED` | нет | `true` | `false` — не импортировать дома при деплое |
| `HOUSES_IMPORT_BATCH_SIZE` | нет | `2000` | размер пакета импорта |

**Secrets** (`secrets`) — пароли, токены и ключи:

| Секрет | Обязателен | Назначение |
|---|---|---|
| `DB_PASSWORD` | да | пароль PostgreSQL (hex, чтобы не ломать `DATABASE_URL`) |
| `MINIO_ROOT_PASSWORD` | да | пароль MinIO |
| `KEYCLOAK_ADMIN_PASSWORD` | да | пароль администратора Keycloak |
| `KEYCLOAK_CLIENT_SECRET` | да | секрет клиента backend, подставляется и в realm при импорте |
| `RESIDENT_JWT_SECRET` | да | подпись JWT жителей |
| `BOT_SHARED_SECRET` | да | секрет бота для выпуска токенов жителей |
| `MAX_BOT_TOKEN` | да | токен бота MAX |
| `MAX_WEBHOOK_SECRET` | да | секрет webhook MAX |
| `GRAFANA_PASSWORD` | да | пароль администратора Grafana |
| `STAFF_BOOTSTRAP_SECRET` | для создания админа | секрет `X-Bootstrap-Secret` для создания первого администратора |
| `STAFF_ADMIN_PASSWORD` | для создания админа | пароль главного администратора при первом создании |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | нет | авторизация на SMTP |

Секреты генерируются командой `openssl rand -hex 32`. Значения Variables и Secrets не должны
содержать одинарных кавычек и переводов строк.

Требования к серверу: Docker Engine с Compose v2, `jq`, `rsync`, `git`, runner с метками
`self-hosted, Linux`, пользователь runner'а в группе `docker`. Миграции применяются при
каждом деплое, поэтому откат возвращает только код — схема БД остаётся новой.
