from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text, false, text, true
from sqlalchemy.orm import Mapped, mapped_column

from src.common.models import Entity
from src.domains.notifications.enums import NotificationType, OrganizationChannelType


class Notification(Entity):
    __tablename__ = "notification"
    __table_args__ = (
        Index("ix_notification_pending_push", "created_at", postgresql_where=text("pushed_at IS NULL")),
        {"schema": "notifications"},
    )

    resident_id: Mapped[UUID] = mapped_column(ForeignKey("identity.resident.id"), index=True)
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, native_enum=False, create_constraint=True, name="notification_type")
    )
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    incident_id: Mapped[UUID | None] = mapped_column(ForeignKey("incidents.incident.id"))
    report_id: Mapped[UUID | None] = mapped_column(ForeignKey("reports.report.id"))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """When the push job (``src.domains.notifications.resident_push``) handled it - sent to
    MAX, or skipped because the resident turned MAX notifications off."""


class OrganizationChannel(Entity):
    """One delivery channel an organization chose for residents' requests. An organization
    may configure several (e.g. a MAX chat for the dispatcher plus a webhook into its CRM);
    with none configured, delivery falls back to ``MAX_MEMBERS``."""

    __tablename__ = "organization_channel"
    __table_args__ = ({"schema": "notifications"},)

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("identity.organization.id"), index=True)
    type: Mapped[OrganizationChannelType] = mapped_column(
        Enum(
            OrganizationChannelType,
            native_enum=False,
            create_constraint=True,
            name="organization_channel_type",
        )
    )
    target: Mapped[str | None] = mapped_column(Text)
    """Channel-specific address - see ``OrganizationChannelType`` for each type's format."""
    secret: Mapped[str | None] = mapped_column(String(255))
    """``WEBHOOK`` only: HMAC-SHA256 signing key. Write-only - never returned by the API."""
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
