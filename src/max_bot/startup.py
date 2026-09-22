import logging

from src.max_bot.cli import DEFAULT_UPDATE_TYPES
from src.max_bot.client import MaxApiError, MaxClient
from src.max_bot.settings import MaxBotSettings

logger = logging.getLogger(__name__)


async def auto_subscribe_max_webhook() -> None:
    """Register this backend's webhook with MAX on startup, so the bot is wired up without
    a manual ``litestar max-subscribe`` step.

    Best-effort and never fatal: silently does nothing if MAX isn't configured at all, or
    if ``MAX_WEBHOOK_PUBLIC_URL`` isn't set (e.g. local dev with no public HTTPS endpoint
    to register), and only logs (never raises) if MAX itself is unreachable.
    """
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
