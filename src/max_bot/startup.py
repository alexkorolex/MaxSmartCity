import logging

from src.max_bot.cli import DEFAULT_UPDATE_TYPES
from src.max_bot.client import MaxApiError, MaxClient
from src.max_bot.settings import MaxBotSettings

logger = logging.getLogger(__name__)


async def auto_subscribe_max_webhook() -> None:
    try:
        settings = MaxBotSettings.from_environment()
    except ValueError:
        return
    if not settings.webhook_public_url:
        return

    client = MaxClient(settings)
    try:
        await client.subscribe(
            url=settings.webhook_public_url,
            update_types=list(DEFAULT_UPDATE_TYPES),
            secret=settings.webhook_secret,
        )
    except (MaxApiError, OSError):
        logger.exception("Could not auto-register the MAX webhook subscription on startup")
    else:
        logger.info("MAX webhook subscription registered", extra={"url": settings.webhook_public_url})
