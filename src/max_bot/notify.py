"""Out-of-app messages from the bot to a resident (e.g. a new chat message), with a button
that logs them straight into the web app."""

import logging

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


async def send_to_resident(resident: Resident, text: str) -> bool:
    """Into the resident's dialog with the bot (``max_chat_id``, saved on /start), by
    ``max_user_id`` while that isn't known yet. Best effort - ``False`` (logged, never
    raised) when MAX isn't configured or the message couldn't be delivered. The login
    button's code lives 5 minutes, hence the hint."""
    try:
        settings = MaxBotSettings.from_environment()
    except ValueError:
        return False
    try:
        attachments = await login_button(await create_login_code(resident.id), settings)
        await MaxClient(settings).send_message(
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
