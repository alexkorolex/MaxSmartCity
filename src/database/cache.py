import os
from dataclasses import dataclass

from litestar.stores.redis import RedisStore


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
