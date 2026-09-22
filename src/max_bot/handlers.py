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

WELCOME_TEXT = (
    "Добро пожаловать в бот, связанный с развитием умного города Max Smart City!\n\n"
    "Здесь вы можете:\n"
    "- войти в веб-приложение Max Smart City одной кнопкой;\n"
    "- в приложении сообщать о городских проблемах (аварии, отключения света и воды, "
    "повреждения инфраструктуры и т.п.);\n"
    "- отслеживать статус поданных обращений и получать по ним уведомления.\n\n"
    "Нажмите кнопку ниже, чтобы войти."
)

LOGIN_TEXT = "Вот ваша ссылка для входа в приложение. Она одноразовая и действует 5 минут."

LOGIN_PROMPT_TEXT = (
    "Напишите /login, чтобы получить ссылку для входа, либо /start, чтобы узнать, что умеет бот."
)


def _display_name(first_name: str | None, last_name: str | None) -> str | None:
    return " ".join(part for part in (first_name, last_name) if part) or None


def _login_button(code: str, settings: MaxBotSettings) -> list[dict[str, Any]]:
    """Inline-keyboard attachment with a single ``link`` button to the (separate) web app.

    The web app reads ``code`` from the query string and calls
    ``POST /auth/residents/login`` itself to finish the login - this backend never
    redirects or serves that page.
    """
    login_url = f"{settings.web_app_login_url}?code={code}"
    return [
        {
            "type": "inline_keyboard",
            "payload": {"buttons": [[{"type": "link", "text": "Войти в приложение", "url": login_url}]]},
        }
    ]


async def _issue_login_button(
    *,
    max_user_id: int,
    username: str | None,
    display_name: str | None,
    resident_service: ResidentService,
    client: MaxClient,
    settings: MaxBotSettings,
    text: str,
) -> None:
    with database_action("upsert", "identity.Resident"):
        resident = await resident_service.upsert_by_max_user_id(
            max_user_id=max_user_id, username=username, display_name=display_name
        )

    code = await create_login_code(resident.id)
    await client.send_message(
        user_id=max_user_id,
        text=text,
        attachments=_login_button(code, settings),
    )


async def handle_bot_started(
    update: dict[str, Any], resident_service: ResidentService, settings: MaxBotSettings
) -> None:
    """User pressed Start - register them as a resident, greet them, and hand out a
    button that logs them into the web app (no code to type in by hand)."""
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
    )


async def handle_message_created(
    update: dict[str, Any], resident_service: ResidentService, settings: MaxBotSettings
) -> None:
    message = update["message"]
    sender = message.get("sender")
    if sender is None or sender.get("is_bot"):
        return

    recipient = message["recipient"]
    if recipient.get("chat_type") != "dialog":
        return

    body = message["body"]
    text = (body.get("text") or "").strip().lower()
    client = MaxClient(settings)

    if text in START_COMMANDS or text in LOGIN_COMMANDS:
        await _issue_login_button(
            max_user_id=sender["user_id"],
            username=sender.get("username"),
            display_name=_display_name(sender.get("first_name"), sender.get("last_name")),
            resident_service=resident_service,
            client=client,
            settings=settings,
            text=WELCOME_TEXT if text in START_COMMANDS else LOGIN_TEXT,
        )
        return

    await client.send_message(user_id=sender["user_id"], text=LOGIN_PROMPT_TEXT)
