from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.common.models import Association, Entity
from src.domains.collaboration.enums import CommentVisibility


class IncidentComment(Entity):
    __tablename__ = "incident_comment"
    __table_args__ = ({"schema": "collaboration"},)

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.incident.id"), index=True)
    assignment_id: Mapped[UUID | None] = mapped_column(ForeignKey("collaboration.assignment.id"))
    work_item_id: Mapped[UUID | None] = mapped_column(ForeignKey("collaboration.work_item.id"))
    author_user_id: Mapped[UUID] = mapped_column(ForeignKey("identity.operator_user.id"))
    visibility: Mapped[CommentVisibility] = mapped_column(
        Enum(CommentVisibility, native_enum=False, create_constraint=True, name="comment_visibility"),
        default=CommentVisibility.INTERNAL,
        server_default=CommentVisibility.INTERNAL.value,
    )
    text: Mapped[str] = mapped_column(Text)


class CommentMention(Association):
    __tablename__ = "comment_mention"
    __table_args__ = ({"schema": "collaboration"},)

    comment_id: Mapped[UUID] = mapped_column(
        ForeignKey("collaboration.incident_comment.id"), primary_key=True
    )
    organization_member_id: Mapped[UUID] = mapped_column(
        ForeignKey("identity.organization_member.id"), primary_key=True
    )
