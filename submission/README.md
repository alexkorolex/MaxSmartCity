# Материалы для технической проверки

Каталог содержит несекретную часть комплекта собственного API:

- `openapi.json` — OpenAPI 3.1 Backend, сгенерированный из приложения;
- `DATA-API.yaml` — последовательность обязательных проверок и ожидаемые ответы;
- `test-data.json` — два минимальных сценария без заранее заданных UUID локальной БД.

Перед сдачей замените переменные `${...}` фактическими значениями либо передайте значения
организаторам согласованным защищённым способом. Рабочие токены и пароли в Git не
добавляются.

OpenAPI пересобирается из корня репозитория:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://schema:schema@localhost/schema"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:KEYCLOAK_URL = "http://localhost:8080"
$env:KEYCLOAK_REALM = "maxsmartcity"
$env:KEYCLOAK_CLIENT_ID = "maxsmartcity-backend"
$env:KEYCLOAK_CLIENT_SECRET = "schema-only-placeholder"
$env:RESIDENT_JWT_SECRET = "schema-only-placeholder-at-least-32-bytes"
$env:RESIDENT_BOT_SHARED_SECRET = "schema-only-placeholder-at-least-32-bytes"
uv run --no-sync litestar --app src.main:create_app schema openapi --output submission/openapi.json
```

Команда не подключается к БД и использует значения только для построения приложения. Перед
release нужно проверить, что OpenAPI, `DATA-API.yaml`, публичный API и commit относятся к одной
версии, затем пройти проверки по порядку и записать фактические ответы в runbook сдачи.
