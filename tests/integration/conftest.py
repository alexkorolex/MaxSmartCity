import os
from collections.abc import AsyncIterator, Iterator

import pytest
from alembic import command
from alembic.config import Config
from litestar.testing import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src.main import create_app


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a disposable PostgreSQL/PostGIS database")
    with pytest.MonkeyPatch.context() as environment:
        environment.setenv("DATABASE_URL", url)
        command.upgrade(Config("alembic.ini"), "head")
    return url


_OFFLINE_ENVIRONMENT = {
    "BACKGROUND_JOBS_INTERVAL_SECONDS": "0",
    "MAX_WEBHOOK_PUBLIC_URL": "",
    "MAX_BOT_TOKEN": "",
    "SMTP_HOST": "",
}


@pytest.fixture(autouse=True)
def offline_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in _OFFLINE_ENVIRONMENT.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def api_client(database_url: str, offline_environment: None) -> Iterator[TestClient]:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    with TestClient(create_app(database_url, redis_url)) as client:
        yield client


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def db_session(database_url: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            async with AsyncSession(bind=connection, expire_on_commit=False) as session:
                yield session
            if transaction.is_active:
                await transaction.rollback()
    finally:
        await engine.dispose()
