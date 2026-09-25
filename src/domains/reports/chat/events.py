"""Live chat updates across app workers (Redis pub/sub): whoever changes a report's chat -
a new message, or messages marked read - publishes to its channel, and a client waiting on
``GET /reports/{id}/messages/updates`` is answered at once instead of on its next poll."""

import asyncio
import logging
import weakref
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.database.cache import CacheSettings

logger = logging.getLogger(__name__)

MAX_WAIT_SECONDS = 25.0
"""Well below proxies' read timeouts (nginx: 60s), so a waiting request is never cut off."""


_clients: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, Redis]" = weakref.WeakKeyDictionary()


def _redis(url: str) -> Redis:
    """One client per event loop: an asyncio Redis connection pool is bound to the loop it
    was created in, and reusing it from another one (a new worker loop, a test client) fails."""
    loop = asyncio.get_running_loop()
    client = _clients.get(loop)
    if client is None:
        client = _clients[loop] = Redis.from_url(url)
    return client


def _channel(report_id: UUID) -> str:
    return f"report_chat:{report_id}"


async def publish_chat_event(report_id: UUID) -> None:
    """Best effort: without Redis, clients still catch up on their fallback poll."""
    try:
        await _redis(CacheSettings.from_environment().url).publish(_channel(report_id), "1")
    except (RedisError, OSError, ValueError):
        logger.warning("Could not publish a chat update", extra={"report_id": str(report_id)}, exc_info=True)


class ChatSubscription:
    """Subscribe *before* checking the database for changes, then wait - so a message
    arriving in between is never missed."""

    def __init__(self, report_id: UUID) -> None:
        self._report_id = report_id
        self._pubsub = None

    async def __aenter__(self) -> "ChatSubscription":
        try:
            self._pubsub = _redis(CacheSettings.from_environment().url).pubsub()
            await self._pubsub.subscribe(_channel(self._report_id))
        except (RedisError, OSError, ValueError):
            logger.warning("Chat updates unavailable, falling back to polling", exc_info=True)
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
            except (RedisError, OSError):
                return False
            if message is not None:
                return True
        return False

    async def __aexit__(self, *_exc: object) -> None:
        if self._pubsub is not None:
            try:
                await self._pubsub.unsubscribe()
                await self._pubsub.aclose()
            except (RedisError, OSError):
                logger.debug("Chat subscription cleanup failed", exc_info=True)
