import logging
from typing import Any

from litestar import Controller, Router, post
from litestar.di import NamedDependency, Provide
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.identity.services import ResidentService
from src.max_bot.dedup import is_duplicate_event, mark_event_processed
from src.max_bot.guards import require_max_webhook_secret
from src.max_bot.handlers import handle_bot_started, handle_bot_stopped, handle_message_created
from src.max_bot.settings import MaxBotSettings

logger = logging.getLogger(__name__)


def provide_resident_service(db_session: NamedDependency[AsyncSession]) -> ResidentService:
    return ResidentService(session=db_session, auto_commit=True)


def _delivery_key(update: dict[str, Any]) -> str | None:
    update_type = update.get("update_type")
    if update_type == "message_created":
        mid = update.get("message", {}).get("body", {}).get("mid")
        return f"message_created:{mid}" if mid else None
    if update_type == "bot_started":
        user_id = update.get("user", {}).get("user_id")
        return f"bot_started:{user_id}:{update.get('timestamp')}"
    if update_type == "message_callback":
        callback = update.get("callback", {})
        return (
            f"message_callback:{callback.get('user', {}).get('user_id')}:"
            f"{callback.get('callback_id')}:{callback.get('timestamp')}"
        )
    return None


class MaxWebhookController(Controller):
    path = "/webhook/max"
    tags = ("max-bot",)
    include_in_schema = False
    guards = (require_max_webhook_secret(),)

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"resident_service": Provide(provide_resident_service, sync_to_thread=False)}

    @post("/", name="max:webhook", status_code=200)
    async def receive(self, data: dict[str, Any], resident_service: NamedDependency[ResidentService]) -> None:
        settings = MaxBotSettings.from_environment()
        update_type = data.get("update_type")
        delivery_key = _delivery_key(data)

        if delivery_key and await is_duplicate_event(delivery_key):
            return

        try:
            match update_type:
                case "bot_started":
                    await handle_bot_started(data, resident_service, settings)
                case "message_created":
                    await handle_message_created(data, resident_service, settings)
                case "bot_stopped":
                    await handle_bot_stopped(data, resident_service)
                case _:
                    logger.info("Unhandled MAX update type", extra={"update_type": update_type})
        # The webhook's boundary, so deliberately broad. MAX redelivers an update until it
        # gets a 200: re-raising would turn one update we can't handle (malformed payload,
        # MAX/Redis/database down, a bug) into an endless retry loop. It is logged with its
        # traceback and left unmarked in the dedup store instead.
        except Exception:
            logger.exception(
                "Failed to process MAX update",
                extra={"update_type": update_type, "delivery_key": delivery_key},
            )
            return

        if delivery_key:
            await mark_event_processed(delivery_key)
