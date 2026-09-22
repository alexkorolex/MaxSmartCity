"""Best-effort registration of the MAX webhook during application startup."""

import logging
import os

from src.max_bot.cli import DEFAULT_UPDATE_TYPES
from src.max_bot.client import MaxClient
from src.max_bot.settings import MaxBotSettings

logger = logging.getLogger(__name__)


async def auto_subscribe_max_webhook() -> None:
    """Register the configured public webhook without blocking backend startup."""
    if not os.environ.get("MAX_WEBHOOK_PUBLIC_URL"):
        return

    try:
        settings = MaxBotSettings.from_environment()
        await MaxClient(settings).subscribe(
            url=settings.webhook_public_url or "",
            update_types=list(DEFAULT_UPDATE_TYPES),
            secret=settings.webhook_secret,
        )
    except Exception:
        logger.exception("Failed to register the MAX webhook during startup")
