from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

import pytest
from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig
from sqlalchemy.ext.asyncio import AsyncSession

from src import background

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class _FakeDbConfig:
    def __init__(self) -> None:
        self.sessions: list[_FakeSession] = []

    @asynccontextmanager
    async def get_session(self) -> AsyncIterator[_FakeSession]:
        session = _FakeSession()
        self.sessions.append(session)
        yield session


async def test_a_failing_job_is_logged_and_does_not_stop_the_others(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    ran: list[str] = []

    async def broken(_session: AsyncSession) -> int:
        ran.append("broken")
        raise ConnectionError("MAX API is unreachable")

    async def healthy(_session: AsyncSession) -> int:
        ran.append("healthy")
        return 1

    monkeypatch.setattr(background, "JOBS", (("broken", broken), ("healthy", healthy)))
    db_config = _FakeDbConfig()

    await background.run_jobs_once(cast(SQLAlchemyAsyncConfig, db_config))

    assert ran == ["broken", "healthy"]
    broken_session, healthy_session = db_config.sessions
    assert broken_session.rolled_back and not broken_session.committed
    assert healthy_session.committed
    [failure] = [record for record in caplog.records if record.levelname == "ERROR"]
    assert failure.getMessage() == "Background job failed"
    assert failure.__dict__["job"] == "broken"
    assert failure.exc_info is not None and isinstance(failure.exc_info[1], ConnectionError)
