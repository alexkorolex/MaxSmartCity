from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, UniqueConstraint, text, true
from sqlalchemy.orm import Mapped, mapped_column

from src.common.models import Record, VersionedEntity
from src.domains.collaboration.enums import AssignmentRole, AssignmentStatus


class Assignment(VersionedEntity):
    __tablename__ = "assignment"
    __table_args__ = (
        UniqueConstraint("id", "incident_id", "organization_id", name="uq_assignment_context"),
        Index(
            "uq_assignment_active_role",
            "incident_id",
            "organization_id",
            "role",
            unique=True,
            postgresql_where=text("status IN ('PROPOSED','ACCEPTED','IN_PROGRESS','BLOCKED','MONITORING')"),
        ),
        {"schema": "collaboration"},
    )

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.incident.id"), index=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("identity.organization.id"), index=True)
    role: Mapped[AssignmentRole] = mapped_column(
        Enum(AssignmentRole, native_enum=False, create_constraint=True, name="assignment_role")
    )
    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, native_enum=False, create_constraint=True, name="assignment_status"),
        default=AssignmentStatus.PROPOSED,
        server_default=AssignmentStatus.PROPOSED.value,
    )
    required: Mapped[bool] = mapped_column(default=True, server_default=true())
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssignmentStatusHistory(Record):
    __tablename__ = "assignment_status_history"
    __table_args__ = ({"schema": "collaboration"},)

    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("collaboration.assignment.id"), index=True)
    from_status: Mapped[AssignmentStatus | None] = mapped_column(
        Enum(
            AssignmentStatus,
            native_enum=False,
            create_constraint=True,
            name="assignment_from_status",
        )
    )
    to_status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, native_enum=False, create_constraint=True, name="assignment_to_status")
    )
    changed_by: Mapped[UUID] = mapped_column(ForeignKey("identity.operator_user.id"))
    reason: Mapped[str | None] = mapped_column(Text)
