# MAX Webhook implementation guide

Проверено по официальной документации MAX и OpenAPI-схеме 22.09.2026.

Источники:
- https://dev.max.ru/docs-api/methods/POST/subscriptions
- https://dev.max.ru/docs-api/use-cases/event-notifications
- https://dev.max.ru/docs-api/objects/Update
- https://dev.max.ru/docs-api/objects/Message
- https://dev.max.ru/docs-api/methods/POST/messages
- https://github.com/max-messenger/api-schema

## Цель

Реализовать цикл:

```text
MAX -> HTTPS Webhook -> verify secret -> parse Update
    -> dedup/persist -> 200
    -> application handler -> POST /messages
```

## Какие события нужны чат-боту

Базово:

```json
[
  "message_created",
  "message_callback",
  "bot_started",
  "bot_stopped"
]
```

## Поля входящего сообщения

Для `message_created`:

```text
update.message.sender.user_id
update.message.sender.is_bot
update.message.recipient.chat_type
update.message.recipient.chat_id
update.message.body.mid
update.message.body.text
update.message.body.attachments
```

### Target ответа

```text
chat_type == dialog:
    POST /messages?user_id=<message.sender.user_id>

chat_type == chat:
    POST /messages?chat_id=<message.recipient.chat_id>

chat_type == channel:
    POST /messages?chat_id=<message.recipient.chat_id>
```

## Critical production rules

1. Проверять `X-Max-Bot-Api-Secret`.
2. Не логировать bot token или webhook secret.
3. Endpoint публично доступен по HTTPS/443.
4. Не использовать self-signed TLS.
5. Вернуть HTTP 200 не позднее 30 секунд.
6. Иметь dedup/idempotency.
7. Не обрабатывать собственные bot messages как пользовательские.
8. Для тяжёлой логики сохранять событие в durable queue и подтверждать после успешного enqueue.
9. MAX API base URL: `https://platform-api2.max.ru`.
10. Заголовок API: `Authorization: <token>` — без автоматического `Bearer`.
11. `POST /messages`: не более 2 сообщений/сек на один target.
12. Общая рекомендуемая нагрузка API: до 30 rps.

## Reverse proxy

Допустимая схема:

```text
Internet
  -> bot.example.com:443
  -> Traefik/Nginx
  -> app:8000
```

MAX видит только `https://bot.example.com/webhook/max`; внутренний порт приложения значения не имеет.

## Delivery flow

```text
POST /webhook/max
    |
    +-- secret valid? -- no --> 401
    |
    +-- JSON valid? --- no --> 400
    |
    +-- supported Update?
    |
    +-- build delivery key
    |
    +-- already processed? -- yes --> 200
    |
    +-- persist/enqueue failed? --> 503
    |
    +-- success --> 200
```

Worker:

```text
load event
  -> subtype handler
  -> business use case
  -> MAX API call
  -> mark processed
```

## Testing

Подписать Webhook, затем руками:

1. `/start`
2. отправить `ping`
3. проверить `message_created`
4. ответить `pong`
5. повторно POST того же тестового payload в endpoint
6. убедиться, что второй ответ не создан
7. нажать callback-кнопку
8. проверить `message_callback`


## Button event matrix

```text
callback             -> message_callback -> POST /answers
message              -> message_created
request_contact      -> message_created + contact attachment
request_geo_location -> message_created + location attachment
link                 -> client-side navigation
clipboard            -> client-side clipboard
open_app             -> Mini App / MAX Bridge
```

MAX Bot API currently documents inline keyboards. Do not invent Telegram
ReplyKeyboardMarkup/ReplyKeyboardRemove equivalents unless MAX adds them to
the official schema in a future version.

For callback business actions always:
- authorize using callback.user.user_id;
- treat payload only as routing/input data;
- deduplicate retries;
- make state-changing commands idempotent.
