"""Duplicating residents' in-app notifications (status changes, "confirm the fix", chat
messages, ...) into MAX - for residents who keep "уведомления в MAX" on. Runs as a
background job (``src.background``), so whoever creates a ``Notification`` doesn't care."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.models import utc_now
from src.domains.identity.models import Resident
from src.domains.notifications.models import Notification
from src.max_bot.notify import max_bot_from_environment, reachable_in_max, send_to_resident

MAX_PUSH_AGE = timedelta(hours=6)
"""Older unsent notifications (the job was off, MAX was down) are no longer news - they
stay in the app only."""


async def push_resident_notifications(session: AsyncSession, *, limit: int = 100) -> int:
    """Each notification is handled once (``pushed_at``), delivered or not - a failed MAX
    call isn't retried. The caller owns the transaction (commits afterwards)."""
    rows = (
        await session.execute(
            select(Notification, Resident)
            .join(Resident, Resident.id == Notification.resident_id)
            .where(Notification.pushed_at.is_(None))
            .order_by(Notification.created_at)
            .limit(limit)
            .with_for_update(of=Notification, skip_locked=True)
        )
    ).all()
    now = utc_now()
    bot = max_bot_from_environment() if rows else None
    for notification, resident in rows:
        notification.pushed_at = now
        if bot and reachable_in_max(resident) and notification.created_at >= now - MAX_PUSH_AGE:
            await send_to_resident(resident, f"{notification.title}\n\n{notification.body}", bot)
    await session.flush()
    return len(rows)
