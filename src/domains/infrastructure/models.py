from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.common.models import Record, utc_now
from src.domains.infrastructure.enums import (
    IdempotencyStatus,
    OutboxStatus,
    WebhookProvider,
    WebhookStatus,
)


class IdempotencyRecord(Record):
    __tablename__ = "idempotency_record"
    __table_args__ = (UniqueConstraint("scope", "key"), {"schema": "infrastructure"})

    scope: Mapped[str] = mapped_column(String(128))
    key: Mapped[str] = mapped_column(String(500))
    status: Mapped[IdempotencyStatus] = mapped_column(
        Enum(IdempotencyStatus, native_enum=False, create_constraint=True, name="idempotency_status"),
        default=IdempotencyStatus.PROCESSING,
        server_default=IdempotencyStatus.PROCESSING.value,
    )
    result_entity_type: Mapped[str | None] = mapped_column(String(128))
    result_entity_id: Mapped[UUID | None] = mapped_column()
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InboundWebhookEvent(Record):
    __tablename__ = "inbound_webhook_event"
    __table_args__ = (
        UniqueConstraint("provider", "idempotency_key"),
        {"schema": "infrastructure"},
    )

    provider: Mapped[WebhookProvider] = mapped_column(
        Enum(WebhookProvider, native_enum=False, create_constraint=True, name="webhook_provider")
    )
    external_event_id: Mapped[str | None] = mapped_column(String(255))
    idempotency_key: Mapped[str] = mapped_column(String(500))
    payload: Mapped[dict[str, object]] = mapped_column(JSONB)
    status: Mapped[WebhookStatus] = mapped_column(
        Enum(WebhookStatus, native_enum=False, create_constraint=True, name="webhook_status"),
        default=WebhookStatus.RECEIVED,
        server_default=WebhookStatus.RECEIVED.value,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)


class OutboxEvent(Record):
    __tablename__ = "outbox_event"
    __table_args__ = (
        CheckConstraint("attempts >= 0", name="outbox_attempts_nonnegative"),
        {"schema": "infrastructure"},
    )

    aggregate_type: Mapped[str] = mapped_column(String(128))
    aggregate_id: Mapped[UUID] = mapped_column(index=True)
    event_type: Mapped[str] = mapped_column(String(255))
    payload: Mapped[dict[str, object]] = mapped_column(JSONB)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(OutboxStatus, native_enum=False, create_constraint=True, name="outbox_status"),
        default=OutboxStatus.PENDING,
        server_default=OutboxStatus.PENDING.value,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
