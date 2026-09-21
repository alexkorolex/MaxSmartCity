from datetime import UTC, datetime
from typing import Any

from advanced_alchemy.base import AdvancedDeclarativeBase, UUIDAuditBase, UUIDBase
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Entity(UUIDAuditBase):
    """Mutable entity with an identity and timezone-aware audit timestamps."""

    __abstract__ = True


class Record(UUIDBase):
    """Historical record: creation time without a mutable update timestamp."""

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )


class Association(AdvancedDeclarativeBase):
    """Base for tables whose domain key is their composite primary key."""

    __abstract__ = True


class VersionedEntity(Entity):
    """Reject stale ORM updates and deletes using SQLAlchemy version checks."""

    __abstract__ = True

    version: Mapped[int] = mapped_column(default=1, server_default="1", nullable=False)

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {"version_id_col": cls.version}
