from typing import ClassVar

from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig

from src.domains.identity.models import Organization, Resident


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
