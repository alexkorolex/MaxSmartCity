from dataclasses import dataclass
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


@dataclass(slots=True)
class HouseOption:
    """Compact house contract used by resident report forms."""

    house_id: UUID
    address: str
    city: str | None
    district: str | None


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
