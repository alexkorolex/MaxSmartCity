from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.common.enums import Priority
from src.common.models import Record, VersionedEntity
from src.domains.collaboration.enums import WorkItemStatus


class WorkItem(VersionedEntity):
    __tablename__ = "work_item"
    __table_args__ = (
        ForeignKeyConstraint(
            ["assignment_id", "incident_id", "organization_id"],
            [
                "collaboration.assignment.id",
                "collaboration.assignment.incident_id",
                "collaboration.assignment.organization_id",
            ],
            name="fk_work_item_assignment_context",
        ),
        ForeignKeyConstraint(
            ["assignee_member_id", "organization_id"],
            ["identity.organization_member.id", "identity.organization_member.organization_id"],
            name="fk_work_item_assignee_organization",
        ),
        {"schema": "collaboration"},
    )

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.incident.id"), index=True)
    assignment_id: Mapped[UUID | None] = mapped_column(index=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("identity.organization.id"), index=True)
    assignee_member_id: Mapped[UUID | None] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[WorkItemStatus] = mapped_column(
        Enum(WorkItemStatus, native_enum=False, create_constraint=True, name="work_item_status"),
        default=WorkItemStatus.TODO,
        server_default=WorkItemStatus.TODO.value,
    )
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority, native_enum=False, create_constraint=True, name="work_item_priority"),
        default=Priority.NORMAL,
        server_default=Priority.NORMAL.value,
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID] = mapped_column(ForeignKey("identity.operator_user.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkItemBlocker(Record):
    __tablename__ = "work_item_blocker"
    __table_args__ = ({"schema": "collaboration"},)

    work_item_id: Mapped[UUID] = mapped_column(ForeignKey("collaboration.work_item.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    created_by: Mapped[UUID] = mapped_column(ForeignKey("identity.operator_user.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkItemAttachment(Record):
    __tablename__ = "work_item_attachment"
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="work_item_attachment_size_nonnegative"),
        {"schema": "collaboration"},
    )

    work_item_id: Mapped[UUID] = mapped_column(ForeignKey("collaboration.work_item.id"), index=True)
    storage_key: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    checksum: Mapped[str] = mapped_column(String(128))
