import logging
import os
from dataclasses import dataclass

from advanced_alchemy.extensions.litestar import AsyncSessionConfig, SQLAlchemyAsyncConfig
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

    def plugin_config(self) -> SQLAlchemyAsyncConfig:
        metadata = ModelRegistry.load()
        logging.getLogger(__name__).info(
            "Configuring domain database", extra={"schemas": ModelRegistry.schemas()}
        )
        return SQLAlchemyAsyncConfig(
            connection_string=self.url,
            metadata=metadata,
            create_all=False,
            session_config=AsyncSessionConfig(expire_on_commit=False),
        )
