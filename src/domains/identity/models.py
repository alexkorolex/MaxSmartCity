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
    false,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.common.models import Association, Entity
from src.domains.identity.enums import BotStatus, OrganizationRegistrationStatus, OrganizationType


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
    house_id: Mapped[UUID | None] = mapped_column(ForeignKey("geo.house.id"))
    """The resident's own selected home - set during onboarding or any time afterwards
    from their profile; independent of any ``Report.house_id`` (which just records where
    a given report happened, not who lives there)."""


class OperatorUser(Entity):
    __tablename__ = "operator_user"
    __table_args__ = ({"schema": "identity"},)

    login: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    keycloak_subject: Mapped[str | None] = mapped_column(String(64), unique=True)
    max_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)


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
    city: Mapped[str | None] = mapped_column(String(255))
    """Free-text city name (same convention as ``Address.city``, not a relational
    ``AdministrativeArea`` FK) - what city this organization operates in/from."""
    inn: Mapped[str | None] = mapped_column(String(12))
    """Russian tax ID (10 digits for a legal entity, 12 for a sole proprietor)."""
    ogrn: Mapped[str | None] = mapped_column(String(15))
    """Russian state registration number (13 digits, or 15 for a sole proprietor)."""
    license_number: Mapped[str | None] = mapped_column(String(255))
    """Required for ``MANAGEMENT_COMPANY`` (Постановление №1616) - not applicable to
    ``HOA``, which is resident self-management rather than a licensed commercial entity.
    Enforced in the registration handler, not the database."""
    registration_status: Mapped[OrganizationRegistrationStatus] = mapped_column(
        Enum(
            OrganizationRegistrationStatus,
            native_enum=False,
            create_constraint=True,
            name="organization_registration_status",
        ),
        default=OrganizationRegistrationStatus.APPROVED,
        server_default=OrganizationRegistrationStatus.APPROVED.value,
    )
    """Defaults to APPROVED so existing rows and admin-direct-CRUD-created orgs are
    unaffected; the self-registration endpoint overrides this to PENDING."""
    in_reserve_registry: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    """Included in the government's Перечень (list) of organizations eligible to be
    assigned as a fallback manager for a house whose residents haven't chosen one -
    distinct from ``registration_status``: an org can be a fully approved, legitimate
    management company without being on this reserve list."""


class Department(Entity):
    __tablename__ = "department"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_department_organization_code"),
        {"schema": "identity"},
    )

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("identity.organization.id"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


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
    department_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.department.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("identity.operator_user.id"), index=True)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("identity.role.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
