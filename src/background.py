"""Periodic jobs run inside every app worker: deliver queued organization notifications
(see ``src.domains.notifications.dispatcher``), auto-close resolutions residents never
answered (``IncidentCoreService.close_unconfirmed_resolutions``) and announce chat messages
left unread (``src.domains.reports.chat.notifier``), then duplicate residents' notifications
into MAX (``src.domains.notifications.resident_push``). All lock their rows
with ``SKIP LOCKED``, so several workers/replicas can run the loop side by side."""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager, suppress

from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig
from litestar import Litestar
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.incidents.services import IncidentCoreService
from src.domains.notifications.dispatcher import OrganizationNotificationDispatcher
from src.domains.notifications.resident_push import push_resident_notifications
from src.domains.reports.chat import notify_unread_chat_messages
from src.settings import BackgroundJobsSettings

logger = logging.getLogger(__name__)

Job = Callable[[AsyncSession], Awaitable[int]]


async def dispatch_organization_notifications(session: AsyncSession) -> int:
    return await OrganizationNotificationDispatcher(session).dispatch_pending()


async def close_unconfirmed_resolutions(session: AsyncSession) -> int:
    return await IncidentCoreService(session).close_unconfirmed_resolutions()


JOBS: tuple[tuple[str, Job], ...] = (
    ("dispatch_organization_notifications", dispatch_organization_notifications),
    ("close_unconfirmed_resolutions", close_unconfirmed_resolutions),
    ("notify_unread_chat_messages", notify_unread_chat_messages),
    ("push_resident_notifications", push_resident_notifications),
)


async def run_jobs_once(db_config: SQLAlchemyAsyncConfig) -> None:
    for name, job in JOBS:
        async with db_config.get_session() as session:
            try:
                processed = await job(session)
                await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                logger.exception("Background job failed", extra={"job": name})
                continue
        if processed:
            logger.info("Background job processed %s item(s)", processed, extra={"job": name})


async def _loop(db_config: SQLAlchemyAsyncConfig, interval: float) -> None:
    while True:
        await run_jobs_once(db_config)
        await asyncio.sleep(interval)


def background_jobs_lifespan(
    db_config: SQLAlchemyAsyncConfig,
) -> Callable[[Litestar], AbstractAsyncContextManager[None]]:
    settings = BackgroundJobsSettings.from_environment()

    @asynccontextmanager
    async def lifespan(_app: Litestar) -> AsyncIterator[None]:
        if settings.interval_seconds <= 0:
            yield
            return
        task = asyncio.create_task(_loop(db_config, settings.interval_seconds))
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    return lifespan
