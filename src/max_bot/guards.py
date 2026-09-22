import hmac

from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.handlers.base import BaseRouteHandler
from litestar.types import Guard

from src.max_bot.settings import MaxBotSettings


def require_max_webhook_secret() -> Guard:
    """Guard factory: only MAX itself, presenting the configured webhook secret, may pass.

    Runs before the body is even parsed, matching the documented dispatch order
    (secret check first, JSON validity second).
    """

    def guard(connection: ASGIConnection, _route_handler: BaseRouteHandler) -> None:
        settings = MaxBotSettings.from_environment()
        provided = connection.headers.get("X-Max-Bot-Api-Secret", "")
        if not hmac.compare_digest(provided, settings.webhook_secret):
            raise NotAuthorizedException("Invalid MAX webhook secret")

    return guard
