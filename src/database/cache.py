import os
from dataclasses import dataclass
from typing import cast

from litestar.stores.redis import RedisStore


class ConsumableRedisStore(RedisStore):
    async def consume(self, key: str) -> bytes | None:
        return await self._redis.getdel(self._make_key(key))


@dataclass(frozen=True, slots=True)
class CacheSettings:
    url: str

    @classmethod
    def from_environment(cls) -> "CacheSettings":
        url = os.environ.get("REDIS_URL")
        if not url:
            raise ValueError("REDIS_URL is required; see .env.example")
        return cls(url=url)

    def response_cache_store(self) -> RedisStore:
        return RedisStore.with_client(self.url, namespace="response_cache")

    def max_webhook_dedup_store(self) -> RedisStore:
        return RedisStore.with_client(self.url, namespace="max_webhook_dedup")

    def max_login_code_store(self) -> ConsumableRedisStore:
        return cast(
            ConsumableRedisStore, ConsumableRedisStore.with_client(self.url, namespace="max_login_code")
        )
