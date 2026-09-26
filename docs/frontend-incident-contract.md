# Контракт фронтенда с Incident Core

Этот документ фиксирует MVP-сценарий жителя. Источником истины для форматов полей остаётся OpenAPI бэкенда.

## Создание обращения

Фронтенд получает категории через `GET /reports/categories/`, а дома — через
`GET /geo/houses/?q=<часть адреса>`. Для справочника домов нужен resident bearer token.

Обращение создаётся только командой `POST /reports/intake`:

```json
{
  "source_external_id": "устойчивый UUID запроса",
  "house_id": "UUID выбранного дома",
  "category_code": "WATER_SUPPLY",
  "text": "Нет холодной воды во всём подъезде",
  "urgency": "HIGH",
  "problem_continues": true,
  "occurred_at": "2026-09-22T09:30:00+03:00",
  "request_id": "UUID попытки"
}
```

`source_external_id` нужно сгенерировать один раз и повторно использовать при сетевом
ретрае. Ответ содержит `report_id` и результат группировки: `CREATED`, `ATTACHED` либо
`NEEDS_CLARIFICATION`. Прямой `POST /reports/` намеренно отсутствует: он обходил бы
идемпотентность и Incident Core.

Если получен `NEEDS_CLARIFICATION`, пользователь выбирает предложенный инцидент или
вариант «создать новый», после чего фронтенд вызывает
`POST /reports/{report_id}/grouping-decision` с одним из вариантов:

```json
{"mode": "CONFIRM_INCIDENT", "confirmed_incident_id": "UUID"}
```

```json
{"mode": "FORCE_NEW"}
```

## Чтение

- `GET /reports/mine` — обращения текущего жителя.
- `GET /reports/{report_id}` — собственное обращение жителя либо доступ сотрудника.
- `GET /incidents/my-house` — активные инциденты дома из последнего обращения жителя.
- `GET /incidents/{incident_id}` — связанный с жителем инцидент либо доступ сотрудника.
- `GET /incidents/{incident_id}/card` — расширенная операторская карточка; жителю недоступна.

Общие списки `GET /reports/` и `GET /incidents/` доступны только сотрудникам. Это важно:
данные других жителей и домов не должны попадать в клиентское приложение.

## Подтверждение решения

Фронтенд отправляет `POST /incidents/{incident_id}/resolution-feedback`:

```json
{
  "report_id": "UUID собственного обращения",
  "feedback": "CONFIRMED",
  "comment": null
}
```

Если проблема сохраняется, используется `feedback: "PROBLEM_CONTINUES"` и комментарий.
Инцидент переводится в спорный статус после сигналов трёх разных жителей за 30 минут;
одиночный ответ не должен мгновенно переоткрывать общедомовой инцидент.

## Интеграция фронтенда

Форма передаёт UUID выбранного дома и код категории в `POST /reports/intake`.
`source_external_id` сохраняется при повторной отправке тех же данных. После создания
открывается карточка обращения. Если её статус `NEEDS_CLARIFICATION`, карточка читает
последнее решение через `GET /reports/{report_id}/grouping` и предлагает выбрать
кандидата либо создать отдельную проблему. Выбор отправляется в
`POST /reports/{report_id}/grouping-decision`.

Экран подтверждения получает ID связанного обращения через
`GET /incidents/{incident_id}/my-report` и отправляет ответ в
`POST /incidents/{incident_id}/resolution-feedback`. Переходы состояния, уведомления
и история выполняются Incident Core.
