import logging
import ssl
from typing import Any

import aiohttp

from src.max_bot.certs import CERTS_DIR
from src.max_bot.settings import MaxBotSettings

logger = logging.getLogger(__name__)


class MaxApiError(RuntimeError):
    """Raised when the MAX Bot API responds with an error status."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"MAX API error {status}: {message}")
        self.status = status


def _ssl_context() -> ssl.SSLContext:
    """System CAs plus the Russian root certificates MAX's API is signed with."""
    context = ssl.create_default_context()
    for cert_path in sorted(CERTS_DIR.glob("*.crt")):
        context.load_verify_locations(cafile=str(cert_path))
    return context


class MaxClient:
    """MAX Bot API client. Create one per unit of work (a webhook update, a notification
    batch) and reuse it within it: it builds its TLS context and looks the bot's username up
    once, not on every call."""

    def __init__(self, settings: MaxBotSettings) -> None:
        self._settings = settings
        self._ssl: ssl.SSLContext | None = None
        self._username: str | None = None

    def _ssl_context(self) -> ssl.SSLContext:
        if self._ssl is None:
            self._ssl = _ssl_context()
        return self._ssl

    async def bot_username(self) -> str | None:
        """The bot's @username (for "open in MAX" buttons); ``None`` if MAX can't tell -
        the caller then simply leaves that button out."""
        if self._username is None:
            try:
                me = await self.get_me()
            except (MaxApiError, OSError):
                logger.warning("Could not fetch the bot's username from MAX", exc_info=True)
                return None
            self._username = (me or {}).get("username")
        return self._username

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        url = f"{self._settings.api_base_url}{path}"
        headers = {"Authorization": self._settings.bot_token}
        timeout = aiohttp.ClientTimeout(total=10)
        connector = aiohttp.TCPConnector(ssl=self._ssl_context())
        async with (
            aiohttp.ClientSession(timeout=timeout, connector=connector) as session,
            session.request(method, url, headers=headers, params=params, json=json) as response,
        ):
            payload = await response.json(content_type=None) if response.content_length else None
            if response.status >= 400:
                message = payload.get("message", str(payload)) if isinstance(payload, dict) else str(payload)
                raise MaxApiError(response.status, message)
            return payload

    async def get_me(self) -> dict[str, Any] | None:
        return await self._request("GET", "/me")

    async def set_commands(self, commands: list[dict[str, str]]) -> dict[str, Any] | None:
        return await self._request("PATCH", "/me/commands", json={"commands": commands})

    async def send_message(
        self,
        *,
        text: str,
        user_id: int | None = None,
        chat_id: int | None = None,
        link: dict[str, Any] | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        if not user_id and not chat_id:
            raise ValueError("Either user_id or chat_id is required")
        params = {"chat_id": chat_id} if chat_id else {"user_id": user_id}
        body: dict[str, Any] = {"text": text}
        if link:
            body["link"] = link
        if attachments:
            body["attachments"] = attachments
        return await self._request("POST", "/messages", params=params, json=body)

    async def subscribe(self, *, url: str, update_types: list[str], secret: str) -> dict[str, Any] | None:
        return await self._request(
            "POST", "/subscriptions", json={"url": url, "update_types": update_types, "secret": secret}
        )

    async def list_subscriptions(self) -> dict[str, Any] | None:
        return await self._request("GET", "/subscriptions")

    async def unsubscribe(self, *, url: str) -> dict[str, Any] | None:
        return await self._request("DELETE", "/subscriptions", params={"url": url})

    async def answer_callback(
        self, *, callback_id: str, notification: str | None = None, message: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        body: dict[str, Any] = {}
        if notification:
            body["notification"] = notification
        if message:
            body["message"] = message
        return await self._request("POST", "/answers", params={"callback_id": callback_id}, json=body)
