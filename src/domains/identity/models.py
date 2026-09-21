from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.common.models import Association, Entity
from src.domains.identity.enums import BotStatus, OrganizationType


class Resident(Entity):
    __tablename__ = "resident"
    __table_args__ = ({"schema": "identity"},)

    max_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))
    bot_status: Mapped[BotStatus] = mapped_column(
        Enum(BotStatus, native_enum=False, create_constraint=True, name="resident_bot_status"),
        default=BotStatus.STARTED,
        server_default=BotStatus.STARTED.value,
    )
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OperatorUser(Entity):
    __tablename__ = "operator_user"
    __table_args__ = ({"schema": "identity"},)

    login: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class Organization(Entity):
    __tablename__ = "organization"
    __table_args__ = ({"schema": "identity"},)

    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[OrganizationType] = mapped_column(
        Enum(
            OrganizationType,
            native_enum=False,
            create_constraint=True,
            name="organization_type",
        )
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class Role(Association):
    __tablename__ = "role"
    __table_args__ = ({"schema": "identity"},)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))


class Permission(Association):
    __tablename__ = "permission"
    __table_args__ = ({"schema": "identity"},)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(128), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)


class RolePermission(Association):
    __tablename__ = "role_permission"
    __table_args__ = ({"schema": "identity"},)

    role_id: Mapped[UUID] = mapped_column(ForeignKey("identity.role.id"), primary_key=True)
    permission_id: Mapped[UUID] = mapped_column(ForeignKey("identity.permission.id"), primary_key=True)


class OrganizationMember(Entity):
    __tablename__ = "organization_member"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_organization_member_organization_user"),
        UniqueConstraint("id", "organization_id", name="uq_organization_member_context"),
        {"schema": "identity"},
    )

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("identity.organization.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("identity.operator_user.id"), index=True)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("identity.role.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
