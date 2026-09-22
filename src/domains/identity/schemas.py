from dataclasses import dataclass
from typing import ClassVar

from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig

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
