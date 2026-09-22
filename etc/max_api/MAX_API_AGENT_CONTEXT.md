# MAX Bot API — контекст для coding agent

> Проверено по официальной документации и официальной OpenAPI-схеме MAX: **22 сентября 2026**.  
> OpenAPI: **Max Bot API 0.0.33**, лицензия схемы **Apache 2.0**.  
> Этот файл — компактный инженерный контекст. Для точных типов, enum, nullable/required и ограничений источником истины должна быть официальная `schema.yaml`.

## 1. Источники истины

1. Документация API: https://dev.max.ru/docs-api
2. Официальный OpenAPI-репозиторий: https://github.com/max-messenger/api-schema
3. Raw OpenAPI schema: https://raw.githubusercontent.com/max-messenger/api-schema/refs/heads/main/schema.yaml
4. Changelog API: https://dev.max.ru/docs-api/changelog-api

При расхождении примера из статьи с OpenAPI:
- сначала сверить отдельную страницу метода;
- затем сверить актуальную `schema.yaml`;
- не переносить старый пример в код автоматически.

## 2. Критически важные правила

- Базовый API-домен: `https://platform-api2.max.ru`.
- Старый `platform-api.max.ru` использовать нельзя для новых интеграций.
- Авторизация передаётся как **чистый токен** в заголовке:
  `Authorization: <access_token>`.
- Не добавлять `Bearer`, если используем HTTP напрямую.
- Передача токена через query-параметр больше не поддерживается.
- Официальная документация требует добавить сертификат Минцифры в доверенные сертификаты клиента/окружения.
- `GET /chats` с июня 2026 не поддерживается.
- API не даёт готового списка всех чатов/каналов бота; `chat_id` нужно получать из событий.
- `POST /chats/{chatId}/members` ограничен с 9 сентября 2026 и заявлен к удалению 30 сентября 2026. Не строить новую функциональность на этом методе.
- Для production использовать Webhook. Long Polling документация считает вариантом для разработки/тестирования.
- Webhook и Long Polling одновременно использовать нельзя.

## 3. Базовый HTTP-клиент

```text
BASE_URL = https://platform-api2.max.ru
Authorization = <access_token>
Content-Type = application/json  # для JSON POST/PUT/PATCH
```

Пример:

```bash
curl -X GET "https://platform-api2.max.ru/me" \
  -H "Authorization: $MAX_ACCESS_TOKEN"
```

Не отключать TLS-проверку в production. Если клиент не доверяет цепочке, добавить требуемый CA/сертификат в trust store.

## 4. Общие форматы

- Запросы/ответы с телом: JSON, UTF-8.
- Временные поля: Unix timestamp в **миллисекундах**, UTC.
- Ошибка API обычно содержит:
  - `code` — строковый ключ ошибки;
  - `message` — описание.
- Типичные HTTP-коды: `200`, `400`, `401`, `403`, `404`, `405`, `429`, `503`.

## 5. Лимиты, которые надо учитывать в коде

- Рекомендованный максимум запросов к `platform-api2.max.ru`: **30 rps**.
- `POST /messages`: не более **2 сообщений/сек** в один диалог, чат или канал.
- `POST /answers`: не более **2 callback-ответов/сек** в один диалог, чат или канал.
- Текст сообщения: до **4000** символов.
- Команд бота: до **32**.
- Имя команды: 1–64 символа.
- Описание команды: 1–128 символов.
- Deep-link payload: до **128** символов.

В клиенте стоит иметь очередь/ограничитель для отправки сообщений по конкретному target ID.

## 6. Каталог endpoint'ов

| Method | Path | operationId | Назначение |
|---|---|---|---|
| `GET` | `/me` | `getMyInfo` | Информация о текущем боте |
| `PATCH` | `/me/commands` | `editMyCommands` | Изменить список команд бота |
| `GET` | `/chats/{chatId}` | `getChat` | Получить чат/канал |
| `PATCH` | `/chats/{chatId}` | `editChat` | Изменить чат/канал |
| `POST` | `/chats/{chatId}/actions` | `sendAction` | Отправить действие бота |
| `GET` | `/chats/{chatId}/pin` | `getPinnedMessage` | Получить закреплённое сообщение |
| `PUT` | `/chats/{chatId}/pin` | `pinMessage` | Закрепить сообщение |
| `DELETE` | `/chats/{chatId}/pin` | `unpinMessage` | Открепить сообщение |
| `GET` | `/chats/{chatId}/members/me` | `getMembership` | Членство текущего бота |
| `DELETE` | `/chats/{chatId}/members/me` | `leaveChat` | Удалить бота из чата/канала |
| `GET` | `/chats/{chatId}/members/admins` | `getAdmins` | Получить администраторов |
| `POST` | `/chats/{chatId}/members/admins` | `postAdmins` | Назначить/изменить администраторов |
| `DELETE` | `/chats/{chatId}/members/admins/{userId}` | `deleteAdmins` | Снять права администратора |
| `GET` | `/chats/{chatId}/members` | `getMembers` | Получить участников |
| `POST` | `/chats/{chatId}/members` | `addMembers` | Добавить участников; метод ограничивается/выводится из эксплуатации |
| `DELETE` | `/chats/{chatId}/members` | `removeMember` | Удалить участника |
| `GET` | `/subscriptions` | `getSubscriptions` | Получить Webhook-подписки |
| `POST` | `/subscriptions` | `subscribe` | Создать Webhook-подписку |
| `DELETE` | `/subscriptions` | `unsubscribe` | Удалить Webhook-подписку |
| `POST` | `/uploads` | `getUploadUrl` | Получить URL загрузки медиа |
| `GET` | `/messages` | `getMessages` | Получить сообщения |
| `POST` | `/messages` | `sendMessage` | Отправить сообщение/пост |
| `PUT` | `/messages` | `editMessage` | Редактировать сообщение |
| `DELETE` | `/messages` | `deleteMessage` | Удалить сообщение |
| `GET` | `/messages/{messageId}` | `getMessageById` | Получить сообщение по ID |
| `GET` | `/messages/{messageId}/comments` | `getComments` | Получить комментарии к посту |
| `POST` | `/messages/{messageId}/comments` | `sendComment` | Отправить комментарий |
| `PUT` | `/messages/{messageId}/comments` | `editComment` | Редактировать комментарий |
| `DELETE` | `/messages/{messageId}/comments` | `deleteComment` | Удалить комментарий |
| `GET` | `/messages/{messageId}/comments/{commentId}` | `getCommentById` | Получить комментарий по ID |
| `GET` | `/videos/{videoToken}` | `getVideoAttachmentDetails` | Получить сведения о видео |
| `POST` | `/answers` | `answerOnCallback` | Ответить на callback |
| `GET` | `/updates` | `getUpdates` | Long Polling обновления |

### Удалённый endpoint

`GET /chats` — больше не поддерживается. Не генерировать для него клиентский код вручную и не пытаться использовать старые примеры.

## 7. Получение `chat_id`

Для группового чата/канала API не предоставляет отдельный актуальный метод «получить все чаты бота».

Получать `chat_id` нужно из `Update`, например из событий:
- `bot_added`;
- `bot_started`;
- других событий, в которых присутствует контекст чата.

Механизм получения:
- Webhook: `POST /subscriptions`;
- для dev/test: `GET /updates`.

## 8. Webhook

Создание:

```http
POST /subscriptions
Authorization: <access_token>
Content-Type: application/json
```

Тело:

```json
{
  "url": "https://example.com/webhook",
  "update_types": ["message_created", "message_callback", "bot_started"],
  "secret": "replace_with_secret"
}
```

### Требования к endpoint

- Только HTTPS.
- Только порт **443**.
- Порт в URL не указывать.
- Сертификат должен быть выдан доверенным CA или соответствовать требованиям MAX.
- Self-signed сертификаты не поддерживаются.
- Имя домена должно совпадать с CN/SAN.
- Сервер должен отдавать полную цепочку сертификатов.
- Webhook должен вернуть **HTTP 200 за 30 секунд**.

### Secret

Если при создании подписки задан `secret`, MAX передаёт его в:

```text
X-Max-Bot-Api-Secret
```

Ограничения `secret`:
- 5–256 символов;
- допустимы буквы, цифры, `_`, `-`.

Всегда сравнивать полученный заголовок с настроенным секретом до обработки события.

### Retry

При неуспешной доставке MAX выполняет до 10 повторов с растущим интервалом. Документация приводит стартовые интервалы 60 сек → 150 сек → 375 сек. Если примерно в течение 8 часов endpoint так и не отвечает успешно, подписка может быть удалена автоматически.

### Типы Update

`update_type` является discriminator'ом OpenAPI:

```text
- `message_created`
- `message_callback`
- `message_edited`
- `message_removed`
- `comment_created`
- `comment_edited`
- `comment_removed`
- `bot_added`
- `bot_removed`
- `user_added`
- `user_removed`
- `bot_started`
- `bot_stopped`
- `dialog_cleared`
- `dialog_removed`
- `dialog_muted`
- `dialog_unmuted`
- `chat_title_changed`
- `bot_admin_permissions_changed`
```

Для `message_created`, `message_edited` и событий пользователей в группах могут требоваться административные права, в частности `read_all_messages`.

## 9. Long Polling

Endpoint: `GET /updates`.

Использовать для разработки/тестирования, если Webhook ещё не поднят. Одновременное использование с активной Webhook-подпиской не допускается.

Минимальный polling interval, указанный OpenAPI: **300 мс**.

Для production проектировать обработчик через Webhook.

## 10. Отправка сообщений

```http
POST /messages?user_id=<id>
POST /messages?chat_id=<id>
```

Параметры:
- `user_id` — отправить пользователю;
- `chat_id` — отправить в чат/канал;
- `disable_link_preview=true` — отключить preview ссылок.

`NewMessageBody`:

```json
{
  "text": "до 4000 символов",
  "attachments": [],
  "link": null,
  "notify": true,
  "format": "markdown"
}
```

`format`:
- `markdown`;
- `html`.

`link` (`NewMessageLink`) используется для reply/forward:

```json
{
  "type": "reply",
  "mid": "<message_id>"
}
```

`type`: `reply` или `forward`.

Для канала `notify=false` использовать нельзя: документация указывает, что посты в канал должны отправляться с `notify=true` или без поля.

## 11. Форматирование текста

MAX поддерживает ограниченное Markdown/HTML-форматирование.

Markdown, среди прочего:
- italic;
- bold;
- strikethrough;
- underline;
- inline/code block;
- highlight;
- quote;
- link;
- user mention через `max://user/<user_id>`;
- заголовок.

HTML поддерживает ограниченный whitelist тегов, включая:
`i/em`, `b/strong`, `del/s`, `ins/u`, `a`, `pre/code`, `mark`, `blockquote`, `h1`.

Не предполагать поддержку произвольного Markdown/HTML. Сервер/клиент MAX поддерживает только описанный поднабор.

В комментариях документация отдельно указывает ограничения на ссылки и упоминания.

## 12. Вложения

Актуальные типы:

- `image`
- `video`
- `audio`
- `file`
- `sticker`
- `contact`
- `inline_keyboard`
- `share`
- `location`

### Медиа

Перед отправкой `video`, `audio`, `file` и обычно `image`:
1. `POST /uploads?type=...`;
2. загрузить бинарный файл на возвращённый upload URL;
3. использовать полученный token в `attachments[].payload.token`.

Для изображения также можно передать внешний `url`.

Один upload URL предназначен для одного файла.

Токен загруженного файла можно переиспользовать.

### Ограничения медиа

- image: JPG/JPEG/PNG/GIF/TIFF/BMP/HEIC, до **50 MB** и не более **7680×7680**;
- video: MP4/MOV/MKV/WEBM, до **250 MB**;
- audio: MP3/WAV/M4A и др., до **256 MB** и не более **60 минут**;
- file: распространённые форматы, до **4 GB**;
- `type=photo` устарел — использовать `type=image`.

Для image в одном запросе документация разрешает до **12 изображений**. Для video также указано до **12 видео**.

### Важная особенность после upload

Файл после загрузки обрабатывается не мгновенно. Возможна ошибка:

```json
{
  "code": "attachment.not.ready",
  "message": "Key: errors.process.attachment.file.not.processed"
}
```

При такой ошибке:
- не считать token недействительным сразу;
- повторить отправку позже;
- использовать увеличивающийся интервал повторов;
- часто используемые файлы загружать заранее.

### Multipart и resumable

Multipart:
- `Content-Type: multipart/form-data`;
- проще;
- при обрыве загружается заново.

Resumable:
- Content-Type не `multipart/form-data`;
- поддерживается загрузка частями и продолжение через `Content-Range`.

## 13. Inline keyboard

Вложение:

```json
{
  "type": "inline_keyboard",
  "payload": {
    "buttons": [
      [
        {
          "type": "callback",
          "text": "Нажать",
          "payload": "action:1"
        }
      ]
    ]
  }
}
```

Клавиатура:
- до **210 кнопок**;
- до **30 рядов**;
- обычно до **7 кнопок в ряду**;
- для `link`, `open_app`, `request_geo_location`, `request_contact` — до **3 в ряду**;
- текст кнопки в OpenAPI: 1–128 символов.

Типы кнопок:

- `callback` — callback payload до 1024 символов; генерирует message_callback
- `link` — URL до 2048 символов
- `request_geo_location` — запрашивает геопозицию; quick=false по умолчанию
- `request_contact` — запрашивает контакт текущего пользователя
- `message` — отправляет заранее заданный текст от пользователя
- `open_app` — открывает mini app; web_app обязателен, payload до 512 символов
- `clipboard` — копирует payload; payload до 1024 символов

Если сообщение с клавиатурой переслать в другой чат, кнопки не пересылаются.

### request_contact

Контакт, полученный именно через кнопку `request_contact`, содержит `hash`, позволяющий отличить подтверждённую передачу номера самим пользователем от обычного пересланного контакта.

Не считать любой объект Contact подтверждением владения номером — проверять сценарий получения и наличие соответствующих данных.

## 14. Callback

Нажатие `callback`-кнопки приходит как:

```text
update_type = message_callback
```

Из callback нужно взять `callback_id`, затем:

```http
POST /answers?callback_id=<callback_id>
```

Тело `CallbackAnswer` может содержать:
- `message: NewMessageBody` — обновить текущее сообщение;
- `notification: string` — одноразовое уведомление пользователю.

## 15. Команды бота

Endpoint:

```http
PATCH /me/commands
```

Тело:

```json
{
  "commands": [
    {
      "name": "start",
      "description": "Запуск"
    }
  ]
}
```

Ограничения:
- максимум 32 команды;
- `name`: 1–64;
- `description`: 1–128.

## 16. Чаты, участники и администраторы

Права администратора из OpenAPI:

```text
read_all_messages
add_remove_members
add_admins
change_chat_info
pin_message
edit_link
write
edit
delete
can_call
view_stats
```

Действия бота (`POST /chats/{chatId}/actions`):

```text
typing_on
sending_photo
sending_video
sending_audio
sending_file
mark_seen
```

`PATCH /chats/{chatId}` поддерживает:
- `icon`;
- `title` (1–200);
- `description` (до 16000; пустая строка удаляет описание);
- `pin`;
- `notify`.

## 17. Комментарии к постам

Методы:
- `GET /messages/{messageId}/comments`
- `POST /messages/{messageId}/comments`
- `PUT /messages/{messageId}/comments`
- `DELETE /messages/{messageId}/comments`
- `GET /messages/{messageId}/comments/{commentId}`

`NewCommentBody` похож на `NewMessageBody`, но **attachments не разрешены**.

События:
- `comment_created`;
- `comment_edited`;
- `comment_removed`.

Для полной модерации боту нужны соответствующие административные права канала, в частности чтение всех сообщений и права edit/write/delete в зависимости от операции.

## 18. Deep links

Формат:

```text
https://max.ru/<botName>?start=<payload>
```

`payload` — до 128 символов. Он приходит в `bot_started`.

## 19. Несоответствия в документации, которые агент должен учитывать

На странице сценария модерации комментариев на момент проверки встречается:
- название события `comment_deleted`;
- пример удаления через `/comments/{commentId}`.

При этом:
- актуальный OpenAPI discriminator содержит **`comment_removed`**;
- официальный каталог методов и OpenAPI описывают удаление через **`DELETE /messages/{messageId}/comments`** с идентификатором комментария согласно параметрам метода.

Поэтому в реализации считать OpenAPI + отдельную страницу метода более приоритетными, чем этот пример сценария.

Также не использовать старые материалы с:
- `platform-api.max.ru`;
- token в query;
- `GET /chats`;
- `type=photo`.

## 20. Особенности генерации клиента из OpenAPI

Официальный репозиторий даёт рекомендации:

### Python

Для `openapi-python-client`:
- Python 3.10+;
- генератор по умолчанию может добавлять `Bearer`;
- для MAX токен должен уходить чистой строкой, поэтому в `AuthenticatedClient` нужен `prefix=""`;
- `Update` полиморфен, и автоматическая диспетчеризация webhook-событий может потребовать ручной обработки по `update_type`.

### TypeScript

Для `openapi-generator typescript-fetch`:
- явно задавать `basePath`;
- token передавать как `apiKey` без `Bearer`.

### Java

Официальная рекомендация для openapi-generator: `--library native`, чтобы корректнее работать с discriminator/polymorphism.

### Общая рекомендация

После генерации клиента провести round-trip тест webhook:
1. взять реальный JSON Update;
2. десериализовать в сгенерированную модель;
3. сериализовать обратно;
4. проверить `update_type` и поля конкретного подтипа.

## 21. Рекомендуемая архитектура клиента

Практическая структура:

```text
max_api/
  client
    auth
    request
    error mapping
    rate limiting

  models
    generated from schema.yaml

  webhook
    TLS endpoint
    X-Max-Bot-Api-Secret verification
    Update dispatcher by update_type

  services
    messages
    chats
    subscriptions
    uploads
    comments
    callbacks

  media
    obtain upload URL
    upload
    processing retry
    reusable token cache
```

### Правила для coding agent

При написании кода:

1. Использовать `platform-api2.max.ru`.
2. Не добавлять `Bearer` к token.
3. Не передавать token в query string.
4. Не использовать `GET /chats`.
5. Не проектировать новую логику вокруг `POST /chats/{chatId}/members`.
6. Webhook считать основным transport для production.
7. Проверять `X-Max-Bot-Api-Secret`.
8. Отвечать Webhook HTTP 200 не позднее 30 секунд.
9. Диспетчеризовать `Update` по `update_type`.
10. Соблюдать 30 rps и 2 msg/sec per target.
11. Учитывать `attachment.not.ready`.
12. Для media сохранять и переиспользовать upload token.
13. Для точных моделей сверяться с `schema.yaml`, а не придумывать поля.
14. При конфликте документации не угадывать — сверить OpenAPI и страницу конкретного метода.
15. Не отключать TLS-проверку в production; установить нужные доверенные сертификаты.

## 22. Ссылки на ключевые страницы

- Overview: https://dev.max.ru/docs-api
- Webhook/events: https://dev.max.ru/docs-api/use-cases/event-notifications
- POST /subscriptions: https://dev.max.ru/docs-api/methods/POST/subscriptions
- chat_id: https://dev.max.ru/docs-api/use-cases/getting-chat-id
- POST /messages: https://dev.max.ru/docs-api/methods/POST/messages
- Formatting: https://dev.max.ru/docs-api/use-cases/sending-messages/text-formatting
- Attachments: https://dev.max.ru/docs-api/use-cases/sending-messages/attachment-types
- Keyboard: https://dev.max.ru/docs-api/use-cases/sending-messages/keyboard
- Media: https://dev.max.ru/docs-api/use-cases/sending-messages/media
- POST /uploads: https://dev.max.ru/docs-api/methods/POST/uploads
- POST /answers: https://dev.max.ru/docs-api/methods/POST/answers
- Comments moderation: https://dev.max.ru/docs-api/use-cases/comment-moderation
- API changelog: https://dev.max.ru/docs-api/changelog-api
- OpenAPI repository: https://github.com/max-messenger/api-schema
- Raw schema: https://raw.githubusercontent.com/max-messenger/api-schema/refs/heads/main/schema.yaml


## 23. Webhook: полный цикл приёма и обработки пользовательских сообщений

Этот раздел обязателен для агента, который реализует бота, а не только HTTP-клиент MAX API.

### 23.1. Как MAX соединяется с приложением

Схема взаимодействия:

```text
MAX user
   │
   │ message
   ▼
MAX platform
   │
   │ HTTPS POST /webhook
   │ X-Max-Bot-Api-Secret: <secret>
   │ body = Update
   ▼
Public HTTPS endpoint :443
   │
   │ reverse proxy (Traefik / Nginx / LB), если используется
   ▼
Application webhook handler
   │
   ├── validate secret
   ├── parse Update
   ├── deduplicate
   ├── persist/enqueue
   └── return HTTP 200
            │
            ▼
        async worker / handler
            │
            ├── process message
            └── POST https://platform-api2.max.ru/messages
```

Публичный URL должен выглядеть, например:

```text
https://bot.example.com/webhook/max
```

Для MAX внешний endpoint должен работать через HTTPS на порту 443. Приложение внутри Docker/VM может слушать другой порт, если TLS/443 завершается reverse proxy и запрос затем проксируется в приложение.

### 23.2. Создание подписки

```bash
curl -X POST "https://platform-api2.max.ru/subscriptions" \
  -H "Authorization: ${MAX_BOT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://bot.example.com/webhook/max",
    "update_types": [
      "message_created",
      "message_callback",
      "bot_started",
      "bot_stopped"
    ],
    "secret": "replace_with_secure_secret"
  }'
```

Для обычного пользовательского чат-бота минимально полезный набор:

```json
[
  "message_created",
  "message_callback",
  "bot_started",
  "bot_stopped"
]
```

Если бот должен реагировать на редактирование/удаление:

```json
[
  "message_created",
  "message_edited",
  "message_removed",
  "message_callback",
  "bot_started",
  "bot_stopped"
]
```

Для групповых чатов и каналов добавить события, необходимые конкретному сценарию. Некоторые события сообщений в группах требуют, чтобы бот был администратором с `read_all_messages`.

### 23.3. Проверка подключения

Получить активные подписки:

```bash
curl -X GET "https://platform-api2.max.ru/subscriptions" \
  -H "Authorization: ${MAX_BOT_TOKEN}"
```

Удалить подписку:

```bash
curl -X DELETE \
  "https://platform-api2.max.ru/subscriptions?url=https%3A%2F%2Fbot.example.com%2Fwebhook%2Fmax" \
  -H "Authorization: ${MAX_BOT_TOKEN}"
```

Перед production-пуском проверить:

```text
[ ] домен резолвится публично
[ ] HTTPS работает снаружи
[ ] сертификат доверенный, не self-signed
[ ] CN/SAN соответствует домену
[ ] сервер отдаёт полную certificate chain
[ ] публичный порт = 443
[ ] POST webhook доступен без Basic Auth / browser login
[ ] secret настроен и проверяется
[ ] endpoint отвечает 200 быстрее 30 секунд
[ ] MAX_BOT_TOKEN не логируется
[ ] webhook body можно безопасно залогировать с редактированием персональных данных
```

### 23.4. Заголовок безопасности

Если при `POST /subscriptions` задан `secret`, каждый Webhook-запрос содержит:

```text
X-Max-Bot-Api-Secret: <secret>
```

Обработчик обязан сравнить значение с локальной конфигурацией.

Псевдокод:

```python
received_secret = request.headers.get("X-Max-Bot-Api-Secret")

if not constant_time_compare(received_secret, configured_secret):
    return 401
```

Предпочтительно использовать constant-time comparison (`hmac.compare_digest` в Python).

Не использовать bot token как webhook secret. Это два разных секрета.

### 23.5. Что приходит в Webhook

Тело запроса — **один объект `Update`**.

Базовые поля:

```json
{
  "update_type": "message_created",
  "timestamp": 1780000000000
}
```

Конкретные поля зависят от `update_type`.

Всегда сначала читать:

```python
update_type = payload["update_type"]
```

и только затем разбирать конкретный subtype.

### 23.6. `message_created`: как извлечь сообщение пользователя

Согласно OpenAPI, структура:

```text
MessageCreatedUpdate
 ├── update_type
 ├── timestamp
 ├── user_locale?
 └── message
      ├── sender?        -> User
      ├── recipient      -> Recipient
      ├── timestamp
      └── body
           ├── mid
           ├── seq
           ├── text?
           ├── attachments?
           └── markup?
```

Иллюстративный payload, построенный по официальной схеме:

```json
{
  "update_type": "message_created",
  "timestamp": 1780000000000,
  "user_locale": "ru",
  "message": {
    "sender": {
      "user_id": 123456789,
      "first_name": "Alex",
      "last_name": null,
      "username": "alex",
      "is_bot": false
    },
    "recipient": {
      "chat_type": "dialog",
      "user_id": 987654321,
      "chat_id": null
    },
    "timestamp": 1780000000000,
    "body": {
      "mid": "message-id",
      "seq": 1,
      "text": "Привет",
      "attachments": null,
      "markup": null
    }
  }
}
```

Это пример формы объекта, а не захваченный реальный payload.

Для обработки:

```python
message = update["message"]
sender = message.get("sender")
recipient = message["recipient"]
body = message["body"]

sender_id = sender["user_id"] if sender else None
chat_type = recipient["chat_type"]
chat_id = recipient.get("chat_id")
text = body.get("text")
message_id = body["mid"]
attachments = body.get("attachments") or []
```

`chat_type`:

```text
dialog
chat
channel
```

### 23.7. Куда отправлять ответ

Не брать `recipient.user_id` как ID пользователя, которому нужно отвечать, вслепую: во входящем сообщении это получатель исходного сообщения, то есть им может быть сам бот.

Правило:

```python
if recipient["chat_type"] == "dialog":
    # пользователь написал боту лично
    target = {"user_id": message["sender"]["user_id"]}
else:
    # сообщение пришло из group chat / channel context
    target = {"chat_id": recipient["chat_id"]}
```

Ответ пользователю:

```http
POST /messages?user_id=<sender.user_id>
```

Ответ в групповом чате:

```http
POST /messages?chat_id=<recipient.chat_id>
```

Тело:

```json
{
  "text": "Ответ бота"
}
```

### 23.8. Reply именно на конкретное сообщение

Если нужно ответить цитированием:

```json
{
  "text": "Ответ на ваше сообщение",
  "link": {
    "type": "reply",
    "mid": "<incoming message.body.mid>"
  }
}
```

Отправить этот `NewMessageBody` в тот же dialog/chat target.

### 23.9. Вложения от пользователя

Не предполагать, что `body.text` всегда существует.

Сообщение может содержать:

```text
text only
attachment only
text + attachments
forward/reply context
```

Обработчик должен делать:

```python
text = body.get("text") or ""
attachments = body.get("attachments") or []
```

и отдельно dispatch по:

```python
attachment["type"]
```

Известные типы:

```text
image
video
audio
file
sticker
contact
inline_keyboard
share
location
```

Нельзя падать на неизвестном будущем типе. Логировать неизвестный `type` и пропускать либо отправлять в generic handler.

### 23.10. `bot_started`

Когда пользователь нажимает Start, приходит:

```text
BotStartedUpdate
 ├── chat_id
 ├── user
 ├── payload?
 └── user_locale
```

Типовая логика:

```python
if update_type == "bot_started":
    user_id = update["user"]["user_id"]
    chat_id = update["chat_id"]
    payload = update.get("payload")

    # create/update user
    # process deep-link payload if present
    # send welcome message
```

Для личного приветствия можно отправлять через `user_id`.

### 23.11. Callback кнопки

При нажатии `callback`-кнопки приходит `message_callback`.

Структура:

```text
MessageCallbackUpdate
 ├── callback
 │    ├── timestamp
 │    ├── callback_id
 │    ├── payload
 │    └── user
 ├── message?
 └── user_locale?
```

Обработка:

```python
callback = update["callback"]

callback_id = callback["callback_id"]
payload = callback.get("payload")
user_id = callback["user"]["user_id"]
```

После нажатия можно вызвать:

```http
POST /answers?callback_id=<callback_id>
```

Например:

```json
{
  "notification": "Готово"
}
```

или изменить исходное сообщение через поле `message`.

### 23.12. Handler dispatch

Рекомендуемая структура:

```python
async def process_update(update: dict) -> None:
    match update.get("update_type"):
        case "message_created":
            await handle_message_created(update)

        case "message_callback":
            await handle_callback(update)

        case "bot_started":
            await handle_bot_started(update)

        case "bot_stopped":
            await handle_bot_stopped(update)

        case "message_edited":
            await handle_message_edited(update)

        case "message_removed":
            await handle_message_removed(update)

        case unknown:
            logger.info("Unhandled MAX update type: %s", unknown)
```

Не писать один огромный webhook handler со всей бизнес-логикой.

### 23.13. Webhook должен быть быстрым

MAX считает доставку неуспешной, если endpoint не вернул `200` в течение 30 секунд.

Для простой операции допустимо:

```text
receive -> validate -> process -> 200
```

Для production предпочтительно:

```text
receive
  -> validate secret
  -> parse
  -> idempotency/dedup
  -> durable enqueue/persist
  -> HTTP 200

worker
  -> business logic
  -> call MAX API
```

Если событие не удалось сохранить/поставить в надёжную очередь, не подтверждать его как успешно принятое.

### 23.14. Повторная доставка и идемпотентность

Webhook может быть доставлен повторно после ошибки/таймаута.

Поэтому обработчик должен быть идемпотентным.

У `Update` нет универсального `update_id`, поэтому ключ дедупликации нужно строить по subtype.

Например:

```text
message_created:
    "message_created:" + message.body.mid

message_removed:
    "message_removed:" + chat_id + ":" + message_id + ":" + timestamp

message_callback:
    "message_callback:" + callback.user.user_id + ":" +
    callback.callback_id + ":" + callback.timestamp

bot_started:
    "bot_started:" + user.user_id + ":" + timestamp
```

Это практическая стратегия дедупликации на основе доступных полей схемы; если бизнес-сценарий допускает повторные события с теми же полями, ключ нужно адаптировать.

Хранить ключ с TTL в Redis или в таблице processed_events.

### 23.15. Не отвечать на собственные сообщения

Для `message_created`:

```python
sender = update["message"].get("sender")

if sender is None:
    # например, сообщение от имени канала
    ...

if sender.get("is_bot"):
    return
```

Если бот работает в группах, также полезно сравнивать `sender.user_id` с ID текущего бота, полученным через `GET /me`.

### 23.16. Ошибки

Webhook endpoint:

```text
401/403 -> invalid webhook secret
400     -> invalid JSON / malformed Update
200     -> событие валидно и принято к обработке
5xx     -> временная проблема; MAX должен повторить доставку
```

Не возвращать 5xx из-за ошибки одной вторичной бизнес-операции после того, как событие уже надёжно сохранено в очередь: повтор Webhook может привести к дубликатам.

MAX API client должен отдельно обрабатывать:

```text
401 invalid token
403 insufficient permissions
404 object not found
429 rate limit
5xx MAX temporary error
```

Для `429` и временных `5xx` использовать retry с backoff и ограничением числа попыток.

### 23.17. Логирование

Минимальные structured fields:

```text
provider=max
update_type
event_timestamp
message_id
callback_id
sender_user_id
chat_id
chat_type
delivery_key
```

Не писать в лог:

```text
MAX_BOT_TOKEN
webhook secret
Authorization header
полное содержимое чувствительных contact-вложений без необходимости
```

### 23.18. Production acceptance test

После запуска агент должен провести проверку:

```text
1. GET /me с MAX_BOT_TOKEN работает.
2. POST /subscriptions возвращает success=true.
3. GET /subscriptions показывает нужный URL.
4. Пользователь нажимает Start.
5. Приложение получает bot_started.
6. Пользователь пишет "ping".
7. Приложение получает message_created.
8. sender.user_id извлечён.
9. body.text == "ping".
10. body.mid сохранён как idempotency key.
11. Бот вызывает POST /messages?user_id=<sender_id>.
12. Пользователь получает "pong".
13. Повтор того же webhook payload не создаёт второй ответ.
14. callback-кнопка создаёт message_callback.
15. POST /answers успешно подтверждает callback.
```

## 24. Минимальная бизнес-модель входящего сообщения

Внутри приложения лучше не таскать сырой JSON MAX по всем слоям.

Нормализовать его:

```python
@dataclass(slots=True)
class IncomingMessage:
    provider: Literal["max"]
    message_id: str
    sender_id: int | None
    chat_id: int | None
    chat_type: str
    text: str
    attachments: list[dict]
    timestamp_ms: int
    raw: dict
```

Mapper:

```text
MAX Update -> transport model -> IncomingMessage -> application handler
```

Так бизнес-логика не зависит напрямую от структуры MAX API и её проще тестировать.

## 25. Файлы-примеры в этом пакете

В ZIP добавлены:

```text
MAX_WEBHOOK_IMPLEMENTATION.md
max_api_examples/
  max_webhook_litestar.py
  subscribe_webhook.sh
  sample_message_created.json
  sample_message_callback.json
```

`max_webhook_litestar.py` — референсная реализация транспорта. Это не обязательная библиотека MAX и не официальный SDK; пример нужен агенту как понятный шаблон архитектуры Webhook.


## 26. Кнопки, callback queries и клавиатуры: обязательная модель для агента

### 26.1. В MAX есть inline keyboard

Официальный Bot API описывает клавиатуру как вложение:

```json
{
  "type": "inline_keyboard",
  "payload": {
    "buttons": [
      [
        {
          "type": "callback",
          "text": "Подтвердить",
          "payload": "confirm:42"
        }
      ]
    ]
  }
}
```

Она передаётся в `attachments` сообщения.

### 26.2. Отдельной Reply/Remote Keyboard в актуальном API нет

Не переносить в MAX Telegram-конструкции:

```text
ReplyKeyboardMarkup
ReplyKeyboardRemove
KeyboardButton как отдельную persistent keyboard
one_time_keyboard
resize_keyboard
```

В актуальной официальной MAX API-схеме отдельного типа remote/reply keyboard нет.

Если в задаче пользователя или старом коде написано `remote keyboard`, агент должен:
1. уточнить, что имеется в виду;
2. по умолчанию реализовать это через `inline_keyboard`;
3. для "кнопка отправляет текст как будто его написал пользователь" использовать кнопку типа `message`.

### 26.3. Все актуальные типы кнопок

| type | Что делает | Что получает бот |
|---|---|---|
| `callback` | Отправляет callback payload | `message_callback` |
| `message` | Отправляет заранее заданный текст от пользователя | обычный `message_created` |
| `link` | Открывает URL | webhook-событие на нажатие не требуется |
| `request_contact` | Пользователь отправляет свой контакт | новое сообщение с `contact` attachment |
| `request_geo_location` | Пользователь отправляет геопозицию | новое сообщение с `location` attachment |
| `open_app` | Открывает mini app | дальнейшее взаимодействие идёт через mini app/MAX Bridge |
| `clipboard` | Копирует payload в clipboard | отдельный callback боту не нужен |

Ключевой принцип:

```text
callback button != message button
```

### 26.4. Callback query lifecycle

MAX называет входящее событие:

```text
update_type = message_callback
```

Объект:

```text
update.callback.callback_id
update.callback.payload
update.callback.user.user_id
update.callback.timestamp
update.message?      # исходное сообщение; может быть null
```

Dispatcher:

```python
if update["update_type"] == "message_callback":
    callback = update["callback"]

    callback_id = callback["callback_id"]
    payload = callback.get("payload")
    user_id = callback["user"]["user_id"]

    await dispatch_callback(
        callback_id=callback_id,
        payload=payload,
        user_id=user_id,
        message=update.get("message"),
    )
```

### 26.5. Router callback payload

Не писать:

```python
if payload == "button1":
...
elif payload == "button2":
...
```

для большого проекта.

Рекомендуемый формат:

```text
<namespace>:<action>:<entity-id>
```

Например:

```text
order:confirm:481
order:cancel:481
page:catalog:2
settings:language:ru
```

Парсер обязан:
- проверить длину;
- проверить namespace/action;
- не доверять ID из payload без авторизации;
- не выполнять действие дважды без idempotency.

### 26.6. Ответ на callback

Ответить на нажатие:

```http
POST /answers?callback_id=<callback_id>
```

Показать notification:

```json
{
  "notification": "Заказ подтверждён"
}
```

Обновить текущее сообщение и клавиатуру:

```json
{
  "message": {
    "text": "Заказ №481 подтверждён",
    "attachments": [
      {
        "type": "inline_keyboard",
        "payload": {
          "buttons": [
            [
              {
                "type": "link",
                "text": "Открыть заказ",
                "url": "https://example.com/orders/481"
              }
            ]
          ]
        }
      }
    ]
  }
}
```

Таким образом callback handler может:
- показать toast/notification;
- заменить текст;
- заменить inline keyboard;
- убрать старые action-кнопки, отправив новую версию сообщения;
- переключить экран/страницу меню.

### 26.7. Inline menu state

Для многоуровневого меню рекомендуется:

```text
main
  ├── catalog
  │    ├── category:42
  │    └── page:2
  ├── profile
  └── settings
```

Callback payload:

```text
menu:catalog
category:open:42
catalog:page:2
menu:back:main
```

Handler не должен хранить состояние интерфейса только внутри текста кнопки.

### 26.8. `message` button

Пример:

```json
{
  "type": "message",
  "text": "Каталог"
}
```

Нажатие приводит к отправке сообщения от пользователя с заданным текстом.

Поэтому его обрабатывает стандартный message router:

```python
if update_type == "message_created":
    text = update["message"]["body"].get("text")

    if text == "Каталог":
        ...
```

Это ближайший аналог "reply button", но клавиатура всё равно является inline attachment сообщения.

### 26.9. `request_contact`

Пример:

```json
{
  "type": "request_contact",
  "text": "Поделиться номером"
}
```

После согласия пользователь отправляет новое сообщение с вложением:

```text
attachment.type = contact
```

Для контакта, полученного именно этой кнопкой, MAX добавляет `hash`.

Проверка подтверждённого номера:

```text
expected = HMAC-SHA256(access_token, vcf_info)
expected == attachment.payload.hash
```

Перед HMAC последовательности `\r\n` из `vcf_info` должны быть реальными CRLF-переносами.

Не считать любой пересланный `contact` подтверждённым номером пользователя.

### 26.10. `request_geo_location`

Нажатие вызывает новое пользовательское сообщение с:

```text
attachment.type = location
```

Обрабатывать в `message_created`, а не в `message_callback`.

У кнопки есть параметр `quick`; согласно OpenAPI по умолчанию `false`.

### 26.11. `link`

Пример:

```json
{
  "type": "link",
  "text": "Открыть сайт",
  "url": "https://example.com"
}
```

Это клиентское действие. Не строить бизнес-процесс, который ожидает `message_callback` после обычной link-кнопки.

Если серверу обязательно нужно знать о действии пользователя, использовать `callback` либо серверный redirect/tracking endpoint в зависимости от требований.

### 26.12. `clipboard`

```json
{
  "type": "clipboard",
  "text": "Скопировать",
  "payload": "PROMO2026"
}
```

Payload копируется в буфер обмена пользователя.

Не ждать `message_callback` только из-за нажатия clipboard-кнопки.

### 26.13. `open_app`

Используется для открытия mini app.

Ключевые поля из OpenAPI:

```text
type = open_app
text
web_app        # required
payload?       # optional
contact_id?    # optional
```

`payload` ограничен форматом схемы и длиной до 512 символов.

Для сценариев внутри mini app агент должен отдельно использовать документацию MAX Bridge; это не обычный callback-flow Bot API.

### 26.14. Ограничения inline keyboard

Актуальная документация указывает:

```text
до 210 кнопок
до 30 рядов
до 7 кнопок в ряду
```

Для:

```text
link
open_app
request_geo_location
request_contact
```

— до 3 кнопок в одном ряду.

При пересылке сообщения в другой чат кнопки не пересылаются.

### 26.15. Callback idempotency

Пользователь может нажать кнопку повторно, а webhook может быть повторно доставлен.

Операция:

```text
payment:confirm
order:create
subscription:activate
```

обязана иметь server-side idempotency.

Нельзя считать UI-кнопку механизмом блокировки повторного действия.

Пример:

```python
key = f"max:callback:{callback['user']['user_id']}:{callback['callback_id']}:{callback['timestamp']}"
```

Для критичных бизнес-операций дополнительно использовать бизнес-ключ:

```text
order-confirm:<order_id>:<user_id>
```

### 26.16. Callback authorization

Payload полностью контролируется клиентским событием и не должен считаться доказательством полномочий.

Плохо:

```python
order_id = payload.split(":")[2]
await confirm_order(order_id)
```

Правильно:

```python
order_id = parse_payload(payload).entity_id

order = await repository.get(order_id)

if order.user_id != callback_user_id:
    raise Forbidden

await confirm_order_idempotently(order)
```

### 26.17. Рекомендуемый router

```python
async def handle_update(update: dict) -> None:
    match update.get("update_type"):
        case "message_created":
            await message_router.dispatch(update)

        case "message_callback":
            await callback_router.dispatch(update)

        case "bot_started":
            await lifecycle_router.started(update)

        case "bot_stopped":
            await lifecycle_router.stopped(update)

        case _:
            await other_update_router.dispatch(update)
```

Callback router:

```python
async def dispatch_callback(update: dict) -> None:
    callback = update["callback"]
    payload = callback.get("payload") or ""

    route = parse_callback_payload(payload)

    match (route.namespace, route.action):
        case ("menu", "open"):
            ...
        case ("order", "confirm"):
            ...
        case ("order", "cancel"):
            ...
        case _:
            ...
```

### 26.18. Итоговая карта событий от кнопок

```text
callback
    -> message_callback
    -> POST /answers

message
    -> message_created
    -> обычный message handler

request_contact
    -> message_created
    -> attachment.type == contact

request_geo_location
    -> message_created
    -> attachment.type == location

link
    -> URL открывается на клиенте

clipboard
    -> payload копируется на клиенте

open_app
    -> открывается mini app
```

Эту карту считать основной при проектировании UI-flow бота.
