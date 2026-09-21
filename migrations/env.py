import asyncio
import logging

from alembic import context
from alembic.runtime.environment import NameFilterParentNames
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from src.database.config import DatabaseSettings
from src.database.registry import ModelRegistry


def include_name(name: str | None, type_: str, parent_names: NameFilterParentNames) -> bool:
    if type_ == "schema":
        return name in ModelRegistry.schemas()
    return True


def configure_migrations(connection: Connection | None = None) -> None:
    context.configure(
        connection=connection,
        url=DatabaseSettings.from_environment().url if connection is None else None,
        target_metadata=ModelRegistry.load(),
        include_schemas=True,
        include_name=include_name,
        compare_type=True,
        literal_binds=connection is None,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_online_migrations() -> None:
    engine = create_async_engine(DatabaseSettings.from_environment().url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(configure_migrations)
    finally:
        await engine.dispose()


def run_migrations() -> None:
    logging.basicConfig(level=logging.INFO)
    if context.is_offline_mode():
        configure_migrations()
    else:
        asyncio.run(run_online_migrations())


run_migrations()
