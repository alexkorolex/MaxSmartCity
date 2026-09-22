import os
from dataclasses import dataclass

DEFAULT_API_BASE_URL = "https://platform-api2.max.ru"


@dataclass(frozen=True, slots=True)
class MaxBotSettings:
    bot_token: str
    """Sent as a bare ``Authorization: <token>`` header - MAX does not use the Bearer scheme."""
    webhook_secret: str
    """Compared against the ``X-Max-Bot-Api-Secret`` header on every inbound webhook call."""
    api_base_url: str
    webhook_public_url: str | None
    """The HTTPS URL MAX should POST updates to; only needed to (re-)register the
    subscription via the ``litestar max-subscribe`` command, not by the webhook itself."""
    web_app_login_url: str
    """Base URL of the (separate) web app's login page. The bot appends ``?code=<code>``
    and sends it as a ``link`` button; the frontend reads the code and calls
    ``POST /auth/residents/login`` itself to finish the login."""

    @classmethod
    def from_environment(cls) -> "MaxBotSettings":
        bot_token = os.environ.get("MAX_BOT_TOKEN")
        if not bot_token:
            raise ValueError("MAX_BOT_TOKEN is required; see .env.example")
        webhook_secret = os.environ.get("MAX_WEBHOOK_SECRET")
        if not webhook_secret:
            raise ValueError("MAX_WEBHOOK_SECRET is required; see .env.example")
        web_app_login_url = os.environ.get("WEB_APP_LOGIN_URL")
        if not web_app_login_url:
            raise ValueError("WEB_APP_LOGIN_URL is required; see .env.example")
        return cls(
            bot_token=bot_token,
            webhook_secret=webhook_secret,
            api_base_url=os.environ.get("MAX_API_BASE_URL") or DEFAULT_API_BASE_URL,
            webhook_public_url=os.environ.get("MAX_WEBHOOK_PUBLIC_URL"),
            web_app_login_url=web_app_login_url,
        )
