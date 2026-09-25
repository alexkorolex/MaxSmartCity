"""Transactional delivery of organization notifications.

Domain services never talk to MAX/SMTP/webhooks inside their own transaction - they only
``enqueue_organization_notification`` an ``infrastructure.outbox_event`` row, committed
atomically with the change that caused it. ``OrganizationNotificationDispatcher`` later
picks those rows up (``FOR UPDATE SKIP LOCKED``, so several app workers can run it) and
fans each one out over the organization's channels via their strategies, retrying failed
channels with exponential backoff.
"""

import logging
from datetime import timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.models import utc_now
from src.domains.infrastructure.enums import OutboxStatus
from src.domains.infrastructure.models import OutboxEvent
from src.domains.notifications.channels import (
    CHANNEL_STRATEGIES,
    ChannelDeliveryError,
    ChannelStrategy,
    ChannelTarget,
    OrganizationMessage,
)
from src.domains.notifications.enums import OrganizationChannelType
from src.domains.notifications.models import OrganizationChannel

__all__ = ("OrganizationMessage", "OrganizationNotificationDispatcher", "enqueue_organization_notification")

logger = logging.getLogger(__name__)

ORGANIZATION_NOTIFICATION_EVENT = "ORGANIZATION_NOTIFICATION"
MAX_DELIVERY_ATTEMPTS = 6
RETRY_BASE_DELAY = timedelta(minutes=1)
FALLBACK_CHANNEL = ChannelTarget(key="fallback:MAX_MEMBERS", type=OrganizationChannelType.MAX_MEMBERS)
"""Used when an organization configured no active channel at all, so a freshly registered
УК still hears about requests through whichever members linked their MAX account."""


def enqueue_organization_notification(session: AsyncSession, message: OrganizationMessage) -> None:
    session.add(
        OutboxEvent(
            aggregate_type="ORGANIZATION",
            aggregate_id=message.organization_id,
            event_type=ORGANIZATION_NOTIFICATION_EVENT,
            payload=message.to_payload(),
        )
    )


async def load_channel_targets(session: AsyncSession, organization_id: UUID) -> list[ChannelTarget]:
    channels = (
        await session.scalars(
            select(OrganizationChannel)
            .where(
                OrganizationChannel.organization_id == organization_id,
                OrganizationChannel.is_active.is_(True),
            )
            .order_by(OrganizationChannel.created_at)
        )
    ).all()
    if not channels:
        return [FALLBACK_CHANNEL]
    return [
        ChannelTarget(key=str(channel.id), type=channel.type, target=channel.target, secret=channel.secret)
        for channel in channels
    ]


class OrganizationNotificationDispatcher:
    def __init__(
        self,
        session: AsyncSession,
        strategies: dict[OrganizationChannelType, ChannelStrategy] | None = None,
    ) -> None:
        self.session = session
        self.strategies = strategies or CHANNEL_STRATEGIES

    async def dispatch_pending(self, limit: int = 50) -> int:
        """Deliver up to ``limit`` due notifications; returns how many were processed.
        The caller owns the transaction and commits afterwards."""
        now = utc_now()
        events = (
            await self.session.scalars(
                select(OutboxEvent)
                .where(
                    OutboxEvent.event_type == ORGANIZATION_NOTIFICATION_EVENT,
                    OutboxEvent.status == OutboxStatus.PENDING,
                    or_(OutboxEvent.next_retry_at.is_(None), OutboxEvent.next_retry_at <= now),
                )
                .order_by(OutboxEvent.created_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()
        for event in events:
            await self.deliver(event)
        await self.session.flush()
        return len(events)

    async def deliver(self, event: OutboxEvent) -> None:
        message = OrganizationMessage.from_payload(event.payload)
        delivered = set(cast(list[str], event.payload.get("delivered_channels") or []))
        errors: list[str] = []
        for channel in await load_channel_targets(self.session, message.organization_id):
            if channel.key in delivered:
                continue
            try:
                await self.strategies[channel.type].send(self.session, channel, message)
            except ChannelDeliveryError as exc:
                errors.append(f"{channel.type.value}: {exc}")
                # Per channel, with the traceback: its cause (SMTP, MAX, the CRM's webhook) is
                # chained to ``exc`` - the summary below only has the messages.
                logger.warning(
                    "Organization notification channel failed",
                    extra={
                        "outbox_event_id": str(event.id),
                        "organization_id": str(message.organization_id),
                        "channel": channel.key,
                        "channel_type": channel.type.value,
                        "attempt": event.attempts + 1,
                    },
                    exc_info=True,
                )
            else:
                delivered.add(channel.key)

        now = utc_now()
        event.attempts += 1
        # Reassign (not mutate) so SQLAlchemy notices the JSONB change.
        event.payload = {
            **event.payload,
            "delivered_channels": sorted(delivered),
            "last_error": "; ".join(errors) or None,
        }
        if not errors:
            event.status = OutboxStatus.PUBLISHED
            event.published_at = now
            event.next_retry_at = None
        elif event.attempts >= MAX_DELIVERY_ATTEMPTS:
            event.status = OutboxStatus.FAILED
            logger.error(
                "Organization notification failed permanently",
                extra={"outbox_event_id": str(event.id), "errors": errors},
            )
        else:
            event.next_retry_at = now + RETRY_BASE_DELAY * 2 ** (event.attempts - 1)
            logger.warning(
                "Organization notification delivery failed, will retry",
                extra={"outbox_event_id": str(event.id), "errors": errors},
            )
