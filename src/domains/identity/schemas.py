from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar
from uuid import UUID

from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig

from src.domains.identity.credentials import CredentialsEmailResult
from src.domains.identity.enums import AuthorityKind, OrganizationType
from src.domains.identity.models import Department, Organization, Resident


class OrganizationCreateDTO(SQLAlchemyDTO[Organization]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"id", "created_at", "updated_at"}, forbid_unknown_fields=True
    )


class OrganizationUpdateDTO(SQLAlchemyDTO[Organization]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"id", "created_at", "updated_at"}, partial=True, forbid_unknown_fields=True
    )


class OrganizationReadDTO(SQLAlchemyDTO[Organization]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig()


class DepartmentCreateDTO(SQLAlchemyDTO[Department]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"id", "created_at", "updated_at"}, forbid_unknown_fields=True
    )


class DepartmentUpdateDTO(SQLAlchemyDTO[Department]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"id", "created_at", "updated_at"}, partial=True, forbid_unknown_fields=True
    )


class DepartmentReadDTO(SQLAlchemyDTO[Department]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig()


@dataclass
class PrincipalRead:
    actor_type: str
    actor_id: str
    roles: list[str]
    organization_id: str | None
    department_id: str | None


class ResidentCreateDTO(SQLAlchemyDTO[Resident]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"id", "created_at", "updated_at", "last_seen_at"}, forbid_unknown_fields=True
    )


class ResidentUpdateDTO(SQLAlchemyDTO[Resident]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"id", "created_at", "updated_at", "last_seen_at"},
        partial=True,
        forbid_unknown_fields=True,
    )


class ResidentReadDTO(SQLAlchemyDTO[Resident]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig()


@dataclass
class ResidentSelfUpdateRequest:
    """Self-service profile edits only - ``max_user_id``/``username``/``bot_status`` are
    bot-owned and never editable here."""

    notifications_enabled: bool | None = None
    display_name: str | None = None
    house_id: UUID | None = None
    """Set or change the resident's own home. Validated against ``geo.house`` server-side
    (not just an FK constraint) so an unknown id comes back as a clean 404, not a 500."""


@dataclass(slots=True)
class OperatorUserSummary:
    """Flat, frontend-friendly staff summary for the admin panel's roster listing -
    joined through the operator's *active* ``OrganizationMember`` row (all the
    organization/department/role fields are ``None`` for staff with no active
    membership)."""

    id: UUID
    login: str
    display_name: str
    email: str | None
    is_active: bool
    organization_id: UUID | None
    organization_name: str | None
    organization_city: str | None
    department_id: UUID | None
    department_name: str | None
    role_code: str | None


@dataclass(slots=True)
class ResidentSummary:
    """Flat resident summary for the admin panel's resident listing, with the resident's
    own house/address flattened in and a report count - avoids extra round trips."""

    id: UUID
    display_name: str | None
    username: str | None
    max_user_id: int | None
    house_id: UUID | None
    house_city: str | None
    house_formatted: str | None
    reports_count: int
    created_at: datetime


@dataclass
class StaffAccountRequest:
    """A new staff login created by an admin on someone's behalf - a Keycloak account
    (realm role ``housing_worker``) plus its local ``OperatorUser``."""

    login: str
    password: str
    display_name: str
    email: str | None = None


@dataclass
class OrganizationRegistrationRequest:
    """An admin registers a housing organization (УК/ТСЖ) together with its first
    employee in one step - the organization is active right away and the employee can
    sign in and receive its residents' requests immediately."""

    code: str
    name: str
    type: OrganizationType
    inn: str
    ogrn: str
    employee: StaffAccountRequest
    city: str | None = None
    license_number: str | None = None
    """Required for ``MANAGEMENT_COMPANY``, forbidden for ``HOA``."""
    in_reserve_registry: bool = False
    """Included in the Перечень (ГИС ЖКХ) - checked by the admin against the registry."""


@dataclass
class AuthorityRegistrationRequest:
    name: str
    authority_kind: AuthorityKind
    territory_id: UUID
    employee: StaffAccountRequest
    inn: str | None = None
    ogrn: str | None = None


@dataclass
class OrganizationMemberCreateRequest:
    user_id: UUID
    role_code: str = "housing_worker"
    department_id: UUID | None = None


@dataclass(slots=True)
class OrganizationMemberSummary:
    id: UUID
    organization_id: UUID
    user_id: UUID
    login: str
    display_name: str
    email: str | None
    has_max_account: bool
    """Whether the member linked a MAX account - i.e. can receive ``MAX_MEMBERS``
    notifications."""
    department_id: UUID | None
    department_name: str | None
    role_code: str
    is_active: bool
    created_at: datetime


@dataclass(slots=True)
class OrganizationRegistrationResult:
    organization_id: UUID
    employee: OrganizationMemberSummary
    credentials_email: CredentialsEmailResult
    """Whether the employee was e-mailed their login and temporary password."""


@dataclass(slots=True)
class StaffAccountCreatedResult:
    member: OrganizationMemberSummary
    credentials_email: CredentialsEmailResult
