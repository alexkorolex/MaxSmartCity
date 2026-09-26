from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.common.models import Entity, Record


class Conversation(Entity):
    __tablename__ = "conversation"
    __table_args__ = (
        CheckConstraint(
            "counterpart_organization_id IS NULL OR counterpart_organization_id <> organization_id",
            name="distinct_sides",
        ),
        Index("ix_conversation_organization_last_message", "organization_id", "last_message_at"),
        Index("ix_conversation_counterpart_last_message", "counterpart_organization_id", "last_message_at"),
        {"schema": "correspondence"},
    )

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("identity.organization.id"))
    counterpart_organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.organization.id"))
    subject: Mapped[str] = mapped_column(String(255))
    created_by: Mapped[UUID] = mapped_column(ForeignKey("identity.operator_user.id"))
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    organization_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    counterpart_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ConversationMessage(Record):
    __tablename__ = "message"
    __table_args__ = (
        Index("ix_message_conversation_created", "conversation_id", "created_at"),
        {"schema": "correspondence"},
    )

    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("correspondence.conversation.id"))
    author_operator_id: Mapped[UUID] = mapped_column(ForeignKey("identity.operator_user.id"))
    author_organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.organization.id"))
    text: Mapped[str] = mapped_column(Text)
