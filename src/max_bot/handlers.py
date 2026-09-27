import logging
from typing import Any

from src.database.logging import database_action
from src.domains.identity.services import ResidentService
from src.max_bot.client import MaxClient
from src.max_bot.dedup import create_login_code
from src.max_bot.settings import MaxBotSettings

logger = logging.getLogger(__name__)

START_COMMANDS = frozenset({"/start", "старт", "начать"})
LOGIN_COMMANDS = frozenset({"/login", "войти", "вход"})
CHAT_ID_COMMANDS = frozenset({"/chatid", "/chat_id"})
MY_ID_COMMANDS = frozenset({"/id", "/myid", "/my_id"})

BOT_COMMANDS: tuple[tuple[str, str], ...] = (
    ("start", "Начать и получить ссылку для входа"),
    ("login", "Войти в приложение Smart City"),
    ("myid", "Узнать свой MAX ID"),
    ("chatid", "Узнать ID группового чата"),
)

WELCOME_TEXT = (
    "Добро пожаловать в бот, связанный с развитием умного города Smart City!\n\n"
    "Здесь вы можете:\n"
    "- войти в веб-приложение Smart City одной кнопкой;\n"
    "- в приложении сообщать о городских проблемах (аварии, отключения света и воды, "
    "повреждения инфраструктуры и т.п.);\n"
    "- отслеживать статус поданных обращений и получать по ним уведомления.\n\n"
    "Нажмите кнопку ниже, чтобы войти."
)

LOGIN_TEXT = "Вот ваша ссылка для входа в приложение. Она одноразовая и действует 5 минут."

LOGIN_PROMPT_TEXT = (
    "Напишите /login, чтобы получить ссылку для входа, либо /start, чтобы узнать, что умеет бот."
)


CHAT_ID_TEXT = (
    "ID этого чата: {chat_id}\n\n"
    "Чтобы получать сюда уведомления о заявках жителей, укажите его в панели Smart City: "
    "«Моя организация» → «Уведомления о заявках» → «Чат MAX»."
)

MY_ID_TEXT = (
    "Ваш MAX ID: {user_id}\n\n"
    "Сотрудникам управляющих организаций: укажите его в панели Smart City "
    "(«Моя организация» → «Уведомления о заявках»), чтобы получать уведомления о заявках лично."
)


def _display_name(first_name: str | None, last_name: str | None) -> str | None:
    return " ".join(part for part in (first_name, last_name) if part) or None


async def login_button(code: str, settings: MaxBotSettings, client: MaxClient) -> list[dict[str, Any]]:
    login_url = f"{settings.web_app_login_url}?code={code}"
    row: list[dict[str, Any]] = []

    bot_username = await client.bot_username()
    if bot_username:
        row.append({"type": "open_app", "text": "Открыть в MAX", "web_app": bot_username, "payload": code})

    row.append({"type": "link", "text": "Открыть в браузере", "url": login_url})

    return [{"type": "inline_keyboard", "payload": {"buttons": [row]}}]


async def _issue_login_button(
    *,
    max_user_id: int,
    username: str | None,
    display_name: str | None,
    resident_service: ResidentService,
    client: MaxClient,
    settings: MaxBotSettings,
    text: str,
    chat_id: int | None,
) -> None:
    with database_action("upsert", "identity.Resident"):
        resident = await resident_service.upsert_by_max_user_id(
            max_user_id=max_user_id, username=username, display_name=display_name, chat_id=chat_id
        )

    code = await create_login_code(resident.id)
    await client.send_message(
        user_id=max_user_id,
        chat_id=chat_id,
        text=text,
        attachments=await login_button(code, settings, client),
    )


async def handle_bot_started(
    update: dict[str, Any], resident_service: ResidentService, settings: MaxBotSettings
) -> None:
    user = update["user"]
    client = MaxClient(settings)
    await _issue_login_button(
        max_user_id=user["user_id"],
        username=user.get("username"),
        display_name=_display_name(user.get("first_name"), user.get("last_name")),
        resident_service=resident_service,
        client=client,
        settings=settings,
        text=WELCOME_TEXT,
        chat_id=update.get("chat_id"),
    )


async def handle_bot_stopped(update: dict[str, Any], resident_service: ResidentService) -> None:
    with database_action("update", "identity.Resident"):
        await resident_service.mark_bot_stopped(max_user_id=update["user"]["user_id"])


async def handle_message_created(
    update: dict[str, Any], resident_service: ResidentService, settings: MaxBotSettings
) -> None:
    message = update["message"]
    sender = message.get("sender")
    if sender is None or sender.get("is_bot"):
        return

    recipient = message["recipient"]
    body = message["body"]
    text = (body.get("text") or "").strip().lower()
    command = text.split("@", 1)[0]
    client = MaxClient(settings)

    if recipient.get("chat_type") != "dialog":
        if command in CHAT_ID_COMMANDS and recipient.get("chat_id"):
            chat_id = recipient["chat_id"]
            await client.send_message(chat_id=chat_id, text=CHAT_ID_TEXT.format(chat_id=chat_id))
        return

    if command in MY_ID_COMMANDS:
        user_id = sender["user_id"]
        await client.send_message(user_id=user_id, text=MY_ID_TEXT.format(user_id=user_id))
        return

    chat_id = recipient.get("chat_id")
    if text in START_COMMANDS or text in LOGIN_COMMANDS:
        await _issue_login_button(
            max_user_id=sender["user_id"],
            username=sender.get("username"),
            display_name=_display_name(sender.get("first_name"), sender.get("last_name")),
            resident_service=resident_service,
            client=client,
            settings=settings,
            text=WELCOME_TEXT if text in START_COMMANDS else LOGIN_TEXT,
            chat_id=chat_id,
        )
        return

    if chat_id:
        with database_action("update", "identity.Resident"):
            await resident_service.remember_chat(max_user_id=sender["user_id"], chat_id=chat_id)

    await client.send_message(user_id=sender["user_id"], text=LOGIN_PROMPT_TEXT)
