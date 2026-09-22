from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from src.common.models import Entity
from src.domains.notifications.enums import NotificationType


class Notification(Entity):
    __tablename__ = "notification"
    __table_args__ = ({"schema": "notifications"},)

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
