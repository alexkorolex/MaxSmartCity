import logging
from typing import Any

from src.database.logging import database_action
from src.domains.identity.services import ResidentService
from src.max_bot.client import MaxClient
from src.max_bot.dedup import create_login_code
from src.max_bot.settings import MaxBotSettings

logger = logging.getLogger(__name__)

LOGIN_COMMANDS = frozenset({"/login", "/start", "войти", "вход"})


def _display_name(first_name: str | None, last_name: str | None) -> str | None:
    return " ".join(part for part in (first_name, last_name) if part) or None


async def _issue_login_code_and_reply(
    *,
    max_user_id: int,
    username: str | None,
    display_name: str | None,
    resident_service: ResidentService,
    client: MaxClient,
) -> None:
    with database_action("upsert", "identity.Resident"):
        resident = await resident_service.upsert_by_max_user_id(
            max_user_id=max_user_id, username=username, display_name=display_name
        )

    code = await create_login_code(resident.id)
    await client.send_message(
        user_id=max_user_id,
        text=(
            f"Код для входа в приложение: {code}\n"
            "Введите его на странице входа. Код действителен 5 минут и одноразовый."
        ),
    )


async def handle_bot_started(
    update: dict[str, Any], resident_service: ResidentService, settings: MaxBotSettings
) -> None:
    """User pressed Start - register/refresh them as a resident and hand out a login code."""
    user = update["user"]
    client = MaxClient(settings)
    await _issue_login_code_and_reply(
        max_user_id=user["user_id"],
        username=user.get("username"),
        display_name=_display_name(user.get("first_name"), user.get("last_name")),
        resident_service=resident_service,
        client=client,
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

    if text in LOGIN_COMMANDS:
        await _issue_login_code_and_reply(
            max_user_id=sender["user_id"],
            username=sender.get("username"),
            display_name=_display_name(sender.get("first_name"), sender.get("last_name")),
            resident_service=resident_service,
            client=client,
        )
        return

    await client.send_message(
        user_id=sender["user_id"], text="Напишите /login, чтобы получить код для входа."
    )
