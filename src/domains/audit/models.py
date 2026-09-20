from uuid import UUID

from sqlalchemy import Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.common.enums import ActorType
from src.common.models import Record


class AuditLog(Record):
    __tablename__ = "audit_log"
    __table_args__ = ({"schema": "audit"},)

    entity_type: Mapped[str] = mapped_column(String(128), index=True)
    entity_id: Mapped[UUID] = mapped_column(index=True)
    action: Mapped[str] = mapped_column(String(128))
    old_values: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    new_values: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    actor_type: Mapped[ActorType] = mapped_column(
        Enum(ActorType, native_enum=False, create_constraint=True, name="audit_actor_type")
    )
    actor_id: Mapped[UUID | None] = mapped_column()
    request_id: Mapped[UUID | None] = mapped_column(index=True)
    entity_version: Mapped[int | None] = mapped_column()
    reason: Mapped[str | None] = mapped_column(Text)
    technical_source: Mapped[str | None] = mapped_column(String(255))
