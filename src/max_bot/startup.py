import logging

from src.max_bot.cli import DEFAULT_UPDATE_TYPES
from src.max_bot.client import MaxApiError, MaxClient
from src.max_bot.handlers import BOT_COMMANDS
from src.max_bot.settings import MaxBotSettings

logger = logging.getLogger(__name__)


async def auto_subscribe_max_webhook() -> None:
    try:
        settings = MaxBotSettings.from_environment()
    except ValueError as exc:
        logger.info("MAX bot is not configured, webhook subscription skipped", extra={"reason": str(exc)})
        return
    if not settings.webhook_public_url:
        logger.info("MAX_WEBHOOK_PUBLIC_URL is not set, webhook subscription skipped")
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


async def auto_register_max_commands() -> None:
    try:
        settings = MaxBotSettings.from_environment()
    except ValueError as exc:
        logger.info(
            "MAX bot is not configured, bot commands registration skipped", extra={"reason": str(exc)}
        )
        return

    commands = [{"name": name, "description": description} for name, description in BOT_COMMANDS]
    try:
        await MaxClient(settings).set_commands(commands)
    except (MaxApiError, OSError):
        logger.exception("Could not register the MAX bot commands on startup")
    else:
        logger.info("MAX bot commands registered", extra={"commands": [name for name, _ in BOT_COMMANDS]})
