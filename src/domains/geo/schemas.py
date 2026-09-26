from dataclasses import dataclass, field
from datetime import date, datetime
from typing import ClassVar, Literal
from uuid import UUID

from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig

from src.domains.geo.enums import AdministrativeAreaType
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


@dataclass(slots=True)
class HouseDataSource:
    """Where a piece of reference data came from, so the resident can judge how fresh
    and trustworthy it is."""

    code: str
    url: str | None
    data_kind: str
    """``REAL`` or ``DEMO`` - demo data must never be presented as a real fact."""
    retrieved_at: datetime


@dataclass(slots=True)
class HouseManagingOrganization:
    """The house's management company as published in open sources (ГИС ЖКХ, cian.ru,
    ...) - reference data from ingestion, including its contacts."""

    name: str
    type: str
    inn: str | None
    ogrn: str | None
    phones: list[str]
    email: str | None
    website: str | None
    basis: str | None
    period_from: date | None
    is_platform_manager: bool
    """The same organization (by INN or OGRN) is connected to Smart City and receives residents'
    requests directly."""
    sources: list[HouseDataSource]


@dataclass(slots=True)
class HousePlatformManager:
    """The УК/ТСЖ connected to Smart City that currently manages the house."""

    organization_id: UUID
    name: str
    type: str
    inn: str | None
    ogrn: str | None
    effective_from: date | None


@dataclass(slots=True)
class HouseInfo:
    house: HouseSummary
    management_method: str | None
    official_status: str | None
    platform_manager: HousePlatformManager | None
    managing_organizations: list[HouseManagingOrganization]


@dataclass(slots=True)
class GeoJSONPoint:
    coordinates: tuple[float, float]
    type: Literal["Point"] = "Point"


@dataclass(slots=True)
class HouseMapProperties:
    house_id: UUID
    formatted: str
    city: str | None
    street: str | None
    house_number: str | None
    active_reports: int
    active_incidents: int
    footprint_area_m2: float | None = None
    size_group: Literal["UP_TO_MEDIAN", "ABOVE_MEDIAN"] | None = None


@dataclass(slots=True)
class HouseMapFeature:
    id: str
    geometry: GeoJSONPoint | None
    properties: HouseMapProperties
    type: Literal["Feature"] = "Feature"


@dataclass(slots=True)
class HouseMapMetadata:
    city: str
    returned: int
    limit: int
    offset: int
    has_more: bool
    located: int
    unlocated: int
    geometry_source: Literal["HOUSE_OR_ADDRESS_POINT"] = "HOUSE_OR_ADDRESS_POINT"
    footprint_area_available: bool = False
    median_footprint_area_m2: float | None = None


@dataclass(slots=True)
class HouseMapFeatureCollection:
    features: list[HouseMapFeature]
    metadata: HouseMapMetadata
    type: Literal["FeatureCollection"] = "FeatureCollection"


@dataclass(slots=True)
class TerritoryNode:
    id: UUID
    parent_id: UUID | None
    name: str
    type: str
    direct_house_count: int
    house_count: int
    authorities: list[str]


@dataclass(slots=True)
class TerritoryStreetShare:
    territory_id: UUID
    territory_name: str
    house_count: int


@dataclass(slots=True)
class TerritoryStreet:
    street: str
    house_count: int
    territories: list[TerritoryStreetShare]


@dataclass(slots=True)
class TerritoryHouse:
    house_id: UUID
    formatted: str
    house_number: str | None
    territory_id: UUID
    territory_name: str


@dataclass
class TerritoryCreateCommand:
    name: str
    type: AdministrativeAreaType
    parent_id: UUID | None = None


@dataclass
class TerritoryUpdateCommand:
    name: str | None = None
    type: AdministrativeAreaType | None = None
    parent_id: UUID | None = None


@dataclass
class TerritoryAssignCommand:
    streets: list[str] = field(default_factory=list)
    house_ids: list[UUID] = field(default_factory=list)


@dataclass(slots=True)
class TerritoryAssignResult:
    moved: int
