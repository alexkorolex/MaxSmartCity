# Материалы для технической проверки

Каталог содержит несекретную часть комплекта собственного API:

- `openapi.json` — OpenAPI 3.1 Backend, сгенерированный из приложения;
- `DATA-API.yaml` — последовательность обязательных проверок и ожидаемые ответы;
- `test-data.json` — два минимальных сценария без заранее заданных UUID локальной БД.

Перед сдачей замените переменные `${...}` фактическими значениями либо передайте значения
организаторам согласованным защищённым способом. Рабочие токены и пароли в Git не
добавляются.

## Откуда берутся значения на проде

| Переменная | Значение |
|---|---|
| `PUBLIC_API_BASE_URL` | `https://backend.<DOMAIN>`, `DOMAIN` — Variable окружения `main` в GitHub |
| `TEST_ADMIN_USERNAME` | Variable `STAFF_ADMIN_LOGIN`: CI/CD создаёт этого администратора (роль `admin`) при деплое |
| `TEST_ADMIN_PASSWORD` | Secret `STAFF_ADMIN_PASSWORD` |
| `TEST_RESIDENT_BEARER_TOKEN` | JWT жителя из `POST /auth/residents/token` (заголовок `X-Bot-Secret`) |
| `STAFF_BEARER_TOKEN`, `TEST_HOUSE_ID`, `REPORT_ID`, `INCIDENT_ID` | сохраняются из ответов предыдущих проверок (`save` в `DATA-API.yaml`) |
| `RUN_ID`, `REQUEST_UUID`, `DECISION_REQUEST_UUID` | генерируются один раз на прогон |

Тестовый дом «Евдокимова 8» есть и в пилотных данных (`ingestion/data/bryansk.json`), и в
датасете ГИС ЖКХ, который CI/CD загружает в БД после деплоя.

## Пересборка OpenAPI

Из корня репозитория (нужен локальный `.env`, создаётся из `.env.example`):

```bash
uv run --locked litestar --app src.main:create_app schema openapi --output submission/openapi.json
```

Команда не подключается к БД и использует значения окружения только для построения
приложения; секреты в схему не попадают. Перед release нужно проверить, что OpenAPI,
`DATA-API.yaml`, публичный API и commit относятся к одной версии, затем пройти проверки по
порядку и записать фактические ответы в runbook сдачи.
