from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    false,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.common.enums import ActorType, Priority
from src.common.models import Entity, Record, utc_now
from src.database.spatial import GeographyText
from src.domains.reports.enums import AttachmentType, ReportSourceType, ReportStatus


class ProblemCategory(Entity):
    __tablename__ = "problem_category"
    __table_args__ = ({"schema": "reports"},)

    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class Report(Entity):
    __tablename__ = "report"
    __table_args__ = (
        Index(
            "uq_report_source_external_id",
            "source_type",
            "source_external_id",
            unique=True,
            postgresql_where=text("source_external_id IS NOT NULL"),
        ),
        Index("ix_report_grouping_candidates", "house_id", "category_id", "status", "received_at"),
        {"schema": "reports"},
    )

    resident_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.resident.id"))
    source_type: Mapped[ReportSourceType] = mapped_column(
        Enum(ReportSourceType, native_enum=False, create_constraint=True, name="report_source_type")
    )
    source_external_id: Mapped[str | None] = mapped_column(String(255))
    text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, native_enum=False, create_constraint=True, name="report_status"),
        default=ReportStatus.RECEIVED,
        server_default=ReportStatus.RECEIVED.value,
    )
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("reports.problem_category.id"))
    urgency: Mapped[Priority] = mapped_column(
        Enum(Priority, native_enum=False, create_constraint=True, name="report_urgency"),
        default=Priority.NORMAL,
        server_default=Priority.NORMAL.value,
    )
    location: Mapped[str | None] = mapped_column(GeographyText("POINT", srid=4326))
    address_id: Mapped[UUID | None] = mapped_column(ForeignKey("geo.address.id"))
    house_id: Mapped[UUID | None] = mapped_column(ForeignKey("geo.house.id"))
    affected_object_id: Mapped[UUID | None] = mapped_column(ForeignKey("geo.affected_object.id"))
    danger_flags: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, server_default="{}")
    extracted_features: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, server_default="{}")
    problem_continues: Mapped[bool | None] = mapped_column(Boolean)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )


class ReportAttachment(Record):
    __tablename__ = "report_attachment"
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="report_attachment_size_nonnegative"),
        {"schema": "reports"},
    )

    report_id: Mapped[UUID] = mapped_column(ForeignKey("reports.report.id"), index=True)
    type: Mapped[AttachmentType] = mapped_column(
        Enum(AttachmentType, native_enum=False, create_constraint=True, name="report_attachment_type")
    )
    storage_key: Mapped[str] = mapped_column(Text)
    original_name: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    checksum: Mapped[str] = mapped_column(String(128))


class ReportStatusHistory(Record):
    __tablename__ = "report_status_history"
    __table_args__ = ({"schema": "reports"},)

    report_id: Mapped[UUID] = mapped_column(ForeignKey("reports.report.id"), index=True)
    from_status: Mapped[ReportStatus | None] = mapped_column(
        Enum(ReportStatus, native_enum=False, create_constraint=True, name="report_previous_status")
    )
    to_status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, native_enum=False, create_constraint=True, name="report_next_status")
    )
    changed_by_type: Mapped[ActorType] = mapped_column(
        Enum(ActorType, native_enum=False, create_constraint=True, name="report_changed_by_type")
    )
    changed_by_id: Mapped[UUID | None] = mapped_column()
    reason: Mapped[str | None] = mapped_column(Text)


class ReportMessage(Record):
    """A message in the chat between the resident who filed a report and the organization
    working on it (its house's УК/ТСЖ or an assigned one). ``read_at`` is set when the other
    side opens the chat; a message left unread is announced to them out of the app
    (``notified_at``) - see ``src.domains.reports.chat``."""

    __tablename__ = "report_message"
    __table_args__ = (
        CheckConstraint(
            "(author_type = 'RESIDENT' AND author_resident_id IS NOT NULL) "
            "OR (author_type = 'OPERATOR' AND author_operator_id IS NOT NULL)",
            name="author_present",
        ),
        Index("ix_report_message_report_created", "report_id", "created_at"),
        Index(
            "ix_report_message_pending_notification",
            "created_at",
            postgresql_where=text("read_at IS NULL AND notified_at IS NULL"),
        ),
        {"schema": "reports"},
    )

    report_id: Mapped[UUID] = mapped_column(ForeignKey("reports.report.id"))
    author_type: Mapped[ActorType] = mapped_column(
        Enum(ActorType, native_enum=False, create_constraint=True, name="report_message_author_type")
    )
    author_resident_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.resident.id"))
    author_operator_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.operator_user.id"))
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.organization.id"))
    """The organization a staff member wrote on behalf of (``None`` for the platform admin)."""
    text: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
