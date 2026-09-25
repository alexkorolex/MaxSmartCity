import logging

from src.max_bot.client import MaxApiError, MaxClient
from src.max_bot.settings import MaxBotSettings

logger = logging.getLogger(__name__)

_cached_username: str | None = None


async def get_bot_username(settings: MaxBotSettings) -> str | None:
    global _cached_username
    if _cached_username is not None:
        return _cached_username

    client = MaxClient(settings)
    try:
        me = await client.get_me()
    except MaxApiError:
        logger.exception("Could not fetch bot info from MAX to resolve its username")
        return None

    username = me.get("username") if me else None
    if username:
        _cached_username = username
    return username
