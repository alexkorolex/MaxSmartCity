from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.common.models import Record
from src.domains.collaboration.enums import CollaborationLinkType, TransferStatus


class TransferRequest(Record):
    __tablename__ = "transfer_request"
    __table_args__ = (
        CheckConstraint("from_organization_id <> to_organization_id", name="transfer_organizations_differ"),
        ForeignKeyConstraint(
            ["assignment_id", "incident_id", "from_organization_id"],
            [
                "collaboration.assignment.id",
                "collaboration.assignment.incident_id",
                "collaboration.assignment.organization_id",
            ],
            name="fk_transfer_assignment_context",
        ),
        {"schema": "collaboration"},
    )

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.incident.id"), index=True)
    assignment_id: Mapped[UUID] = mapped_column(index=True)
    from_organization_id: Mapped[UUID] = mapped_column(ForeignKey("identity.organization.id"))
    to_organization_id: Mapped[UUID] = mapped_column(ForeignKey("identity.organization.id"))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[TransferStatus] = mapped_column(
        Enum(TransferStatus, native_enum=False, create_constraint=True, name="transfer_status"),
        default=TransferStatus.PENDING,
        server_default=TransferStatus.PENDING.value,
    )
    created_by: Mapped[UUID] = mapped_column(ForeignKey("identity.operator_user.id"))
    responded_by: Mapped[UUID | None] = mapped_column(ForeignKey("identity.operator_user.id"))
    response_reason: Mapped[str | None] = mapped_column(Text)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CollaborationLink(Record):
    __tablename__ = "collaboration_link"
    __table_args__ = ({"schema": "collaboration"},)

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.incident.id"), index=True)
    type: Mapped[CollaborationLinkType] = mapped_column(
        Enum(
            CollaborationLinkType,
            native_enum=False,
            create_constraint=True,
            name="collaboration_link_type",
        )
    )
    title: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("identity.operator_user.id"))
