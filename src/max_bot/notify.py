"""Out-of-app messages from the bot to a resident (e.g. a new chat message), with a button
that logs them straight into the web app."""

import logging
from dataclasses import dataclass

from redis.exceptions import RedisError

from src.domains.identity.enums import BotStatus
from src.domains.identity.models import Resident
from src.max_bot.client import MaxApiError, MaxClient
from src.max_bot.dedup import create_login_code
from src.max_bot.handlers import login_button
from src.max_bot.settings import MaxBotSettings

logger = logging.getLogger(__name__)

RELOGIN_HINT = "\n\nЕсли кнопка уже не работает, напишите боту /login."


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


async def send_to_resident(resident: Resident, text: str, bot: MaxBot) -> bool:
    try:
        attachments = await login_button(await create_login_code(resident.id), bot.settings, bot.client)
        await bot.client.send_message(
            chat_id=resident.max_chat_id,
            user_id=resident.max_user_id,
            text=text + RELOGIN_HINT,
            attachments=attachments,
        )
    except (MaxApiError, OSError, RedisError):
        logger.warning(
            "Could not message a resident in MAX", extra={"resident_id": str(resident.id)}, exc_info=True
        )
        return False
    return True
