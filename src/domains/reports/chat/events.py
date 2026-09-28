"""Live chat updates across app workers (Redis pub/sub): whoever changes a report's chat -
a new message, or messages marked read - publishes to its channel, and a client waiting on
``GET /reports/{id}/messages/updates`` is answered at once instead of on its next poll."""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from uuid import UUID

from litestar import Litestar
from litestar.datastructures import State
from redis.asyncio import Redis
from redis.asyncio.client import PubSub
from redis.exceptions import RedisError

from src.database.cache import CacheSettings

logger = logging.getLogger(__name__)

MAX_WAIT_SECONDS = 25.0
"""Well below proxies' read timeouts (nginx: 60s), so a waiting request is never cut off."""

CHAT_EVENTS_STATE_KEY = "chat_events"

_REDIS_FAILURES = (RedisError, OSError)


def _channel(report_id: UUID) -> str:
    return f"report_chat:{report_id}"


class ChatSubscription:
    """Subscribe *before* checking the database for changes, then wait - so a message
    arriving in between is never missed."""

    def __init__(self, redis: Redis, report_id: UUID) -> None:
        self._redis = redis
        self._report_id = report_id
        self._pubsub: PubSub | None = None

    async def __aenter__(self) -> "ChatSubscription":
        try:
            self._pubsub = self._redis.pubsub()
            await self._pubsub.subscribe(_channel(self._report_id))
        except _REDIS_FAILURES:
            logger.warning(
                "Chat updates unavailable, falling back to polling",
                extra={"report_id": str(self._report_id)},
                exc_info=True,
            )
            self._pubsub = None
        return self

    async def wait(self, max_seconds: float) -> bool:
        """``True`` as soon as the chat changes, ``False`` after ``max_seconds``."""
        if self._pubsub is None:
            await asyncio.sleep(min(max_seconds, 5.0))
            return False
        deadline = asyncio.get_running_loop().time() + max_seconds
        while (remaining := deadline - asyncio.get_running_loop().time()) > 0:
            try:
                message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=remaining)
            except _REDIS_FAILURES:
                logger.warning(
                    "Lost the chat updates subscription, the client will poll again",
                    extra={"report_id": str(self._report_id)},
                    exc_info=True,
                )
                return False
            if message is not None:
                return True
        return False

    async def __aexit__(self, *_exc: object) -> None:
        if self._pubsub is not None:
            try:
                await self._pubsub.unsubscribe()
                await self._pubsub.aclose()
            except _REDIS_FAILURES:
                logger.debug("Chat subscription cleanup failed", exc_info=True)


class ChatEventBus:
    """The application's connection to the chat channels - created with the app (see
    ``chat_events_lifespan``) and closed with it; an asyncio Redis pool belongs to the
    event loop it was created in, which is exactly the app's one."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @classmethod
    def from_url(cls, url: str) -> "ChatEventBus":
        return cls(Redis.from_url(url))

    async def publish(self, report_id: UUID) -> None:
        """Best effort: without Redis, clients still catch up on their fallback poll."""
        try:
            await self._redis.publish(_channel(report_id), "1")
        except _REDIS_FAILURES:
            logger.warning(
                "Could not publish a chat update", extra={"report_id": str(report_id)}, exc_info=True
            )

    def subscribe(self, report_id: UUID) -> ChatSubscription:
        return ChatSubscription(self._redis, report_id)

    async def aclose(self) -> None:
        await self._redis.aclose()


def chat_events_lifespan(
    cache_settings: CacheSettings,
) -> Callable[[Litestar], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: Litestar) -> AsyncIterator[None]:
        bus = ChatEventBus.from_url(cache_settings.url)
        app.state[CHAT_EVENTS_STATE_KEY] = bus
        try:
            yield
        finally:
            await bus.aclose()

    return lifespan


def provide_chat_events(state: State) -> ChatEventBus:
    return state[CHAT_EVENTS_STATE_KEY]
