"""Out-of-app messages from the bot to a resident (e.g. a new chat message), with a button
that logs them straight into the web app."""

import logging
from dataclasses import dataclass

from redis.exceptions import RedisError

from src.domains.identity.enums import BotStatus
from src.domains.identity.models import Resident
from src.domains.notifications.enums import NotificationType
from src.domains.notifications.models import Notification
from src.max_bot.client import MaxApiError, MaxClient
from src.max_bot.dedup import create_login_code
from src.max_bot.handlers import browser_login_url, keyboard
from src.max_bot.settings import MaxBotSettings

logger = logging.getLogger(__name__)

RELOGIN_HINT = "\n\nЕсли кнопка уже не работает, напишите боту /start."


def reachable_in_max(resident: Resident) -> bool:
    """Wants MAX notifications and can get them: known in MAX, bot not stopped."""
    return (
        resident.notifications_enabled
        and bool(resident.max_chat_id or resident.max_user_id)
        and resident.bot_status is not BotStatus.STOPPED
    )


@dataclass(frozen=True, slots=True)
class MaxBot:
    """The bot's settings and a client to talk to MAX with - one per batch of messages."""

    settings: MaxBotSettings
    client: MaxClient


def max_bot_from_environment() -> MaxBot | None:
    """``None`` when the bot is not configured - then there's simply nothing to send."""
    try:
        settings = MaxBotSettings.from_environment()
    except ValueError as exc:
        logger.debug("MAX bot is not configured, not messaging residents", extra={"reason": str(exc)})
        return None
    return MaxBot(settings=settings, client=MaxClient(settings))


@dataclass(frozen=True, slots=True)
class AppTarget:
    start_param: str
    path: str
    button_text: str


APP_HOME = AppTarget(start_param="", path="/", button_text="Открыть в MAX")


def notification_target(notification: Notification) -> AppTarget:
    report_id, incident_id = notification.report_id, notification.incident_id
    if notification.type == NotificationType.CHAT_MESSAGE and report_id:
        return AppTarget(f"report_{report_id}_chat", f"/reports/{report_id}/chat", "Открыть чат")
    if notification.type == NotificationType.RESOLUTION_REQUESTED and incident_id:
        return AppTarget(
            f"incident_{incident_id}_resolution",
            f"/incidents/{incident_id}/resolution",
            "Подтвердить решение",
        )
    if report_id:
        return AppTarget(f"report_{report_id}", f"/reports/{report_id}", "Открыть обращение")
    if incident_id:
        return AppTarget(f"incident_{incident_id}", f"/incidents/{incident_id}", "Открыть заявку")
    return APP_HOME


async def _app_button(resident: Resident, target: AppTarget, bot: MaxBot) -> tuple[dict[str, str], bool]:
    bot_username = await bot.client.bot_username()
    if bot_username:
        button = {"type": "open_app", "text": target.button_text, "web_app": bot_username}
        if target.start_param:
            button["payload"] = target.start_param
        return button, False
    url = browser_login_url(bot.settings, await create_login_code(resident.id), target.path)
    return {"type": "link", "text": target.button_text, "url": url}, True


async def send_to_resident(resident: Resident, text: str, bot: MaxBot, target: AppTarget = APP_HOME) -> bool:
    try:
        button, expires = await _app_button(resident, target, bot)
        await bot.client.send_message(
            chat_id=resident.max_chat_id,
            user_id=resident.max_user_id,
            text=text + RELOGIN_HINT if expires else text,
            attachments=keyboard([button]),
        )
    except (MaxApiError, OSError, RedisError):
        logger.warning(
            "Could not message a resident in MAX", extra={"resident_id": str(resident.id)}, exc_info=True
        )
        return False
    return True
