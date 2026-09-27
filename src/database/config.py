import logging
import os
from dataclasses import dataclass

from advanced_alchemy.extensions.litestar import AsyncSessionConfig, EngineConfig, SQLAlchemyAsyncConfig
from sqlalchemy.engine import make_url

from src.database.registry import ModelRegistry


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    url: str

    def __post_init__(self) -> None:
        if make_url(self.url).drivername != "postgresql+asyncpg":
            raise ValueError("DATABASE_URL must use postgresql+asyncpg://")

    @classmethod
    def from_environment(cls) -> "DatabaseSettings":
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL is required; see .env.example")
        return cls(url=url)

    def plugin_config(self, *, pool_size: int | None = None) -> SQLAlchemyAsyncConfig:
        metadata = ModelRegistry.load()
        logging.getLogger(__name__).info(
            "Configuring domain database", extra={"schemas": ModelRegistry.schemas()}
        )
        return SQLAlchemyAsyncConfig(
            connection_string=self.url,
            metadata=metadata,
            create_all=False,
            session_config=AsyncSessionConfig(expire_on_commit=False),
            engine_config=EngineConfig(pool_size=pool_size, max_overflow=pool_size)
            if pool_size
            else EngineConfig(),
        )
