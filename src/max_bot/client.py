import ssl
from functools import lru_cache
from typing import Any

import aiohttp

from src.max_bot.certs import CERTS_DIR
from src.max_bot.settings import MaxBotSettings


class MaxApiError(RuntimeError):
    """Raised when the MAX Bot API responds with an error status."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"MAX API error {status}: {message}")
        self.status = status


@lru_cache(maxsize=1)
def _ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    for cert_path in sorted(CERTS_DIR.glob("*.crt")):
        context.load_verify_locations(cafile=str(cert_path))
    return context


class MaxClient:
    def __init__(self, settings: MaxBotSettings) -> None:
        self._settings = settings

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
        connector = aiohttp.TCPConnector(ssl=_ssl_context())
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
        # A known dialog wins: it is exactly where the user talks to the bot.
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
