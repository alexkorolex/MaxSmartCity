from typing import ClassVar

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
