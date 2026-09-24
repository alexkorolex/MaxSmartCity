from dataclasses import dataclass
from datetime import date
from typing import ClassVar
from uuid import UUID

from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig

from src.domains.geo.models import Address, AdministrativeArea, AffectedObject, House


class AddressCreateDTO(SQLAlchemyDTO[Address]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"created_at", "id", "updated_at"}, forbid_unknown_fields=True
    )


class AddressUpdateDTO(SQLAlchemyDTO[Address]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"created_at", "id", "updated_at"}, forbid_unknown_fields=True, partial=True
    )


class AddressReadDTO(SQLAlchemyDTO[Address]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig()


class AdministrativeAreaCreateDTO(SQLAlchemyDTO[AdministrativeArea]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"created_at", "id", "updated_at"}, forbid_unknown_fields=True
    )


class AdministrativeAreaUpdateDTO(SQLAlchemyDTO[AdministrativeArea]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"created_at", "id", "updated_at"}, forbid_unknown_fields=True, partial=True
    )


class AdministrativeAreaReadDTO(SQLAlchemyDTO[AdministrativeArea]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig()


class HouseCreateDTO(SQLAlchemyDTO[House]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"created_at", "id", "updated_at"}, forbid_unknown_fields=True
    )


class HouseUpdateDTO(SQLAlchemyDTO[House]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"created_at", "id", "updated_at"}, forbid_unknown_fields=True, partial=True
    )


class HouseReadDTO(SQLAlchemyDTO[House]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig()


class AffectedObjectCreateDTO(SQLAlchemyDTO[AffectedObject]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"created_at", "id", "updated_at"}, forbid_unknown_fields=True
    )


class AffectedObjectUpdateDTO(SQLAlchemyDTO[AffectedObject]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"created_at", "id", "updated_at"}, forbid_unknown_fields=True, partial=True
    )


class AffectedObjectReadDTO(SQLAlchemyDTO[AffectedObject]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig()


@dataclass(slots=True)
class HouseSummary:
    """A house with its address flattened in - what a resident picks their home from,
    without a second round trip to resolve ``House.address_id``."""

    house_id: UUID
    city: str | None
    street: str | None
    house_number: str | None
    formatted: str
    managed_by_organization_id: UUID | None = None
    """The УК/ТСЖ currently managing the house, if any."""
    managed_by_organization_name: str | None = None


@dataclass
class AssignHouseManagementCommand:
    """Record who manages a house: either the residents' own choice (general meeting,
    ТСЖ) or, when they chose none / it wasn't implemented, a management company from the
    Перечень appointed by the local authority (Правила №1616, п. 5). Replaces the house's
    current manager, if any."""

    house_id: UUID
    organization_id: UUID
    basis: str
    """Legal basis, e.g. "протокол общего собрания №3 от 01.02.2026" or "решение
    администрации №... об определении УК из Перечня"."""
    assigned_via_reserve_registry: bool = False
    effective_from: date | None = None
    """Defaults to today."""


@dataclass
class TerminateHouseManagementCommand:
    effective_to: date | None = None
    """Defaults to today."""
    reason: str | None = None


@dataclass(slots=True)
class HouseManagementSummary:
    id: UUID
    house_id: UUID
    house_formatted: str
    organization_id: UUID
    organization_name: str
    organization_type: str
    organization_inn: str | None
    is_active: bool
    basis: str | None
    assigned_via_reserve_registry: bool
    effective_from: date | None
    effective_to: date | None
