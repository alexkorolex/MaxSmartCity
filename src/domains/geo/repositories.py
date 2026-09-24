from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from src.domains.geo.models import Address, AdministrativeArea, AffectedObject, House, HouseManagement


class AddressRepository(SQLAlchemyAsyncRepository[Address]):
    model_type = Address


class AdministrativeAreaRepository(SQLAlchemyAsyncRepository[AdministrativeArea]):
    model_type = AdministrativeArea


class HouseRepository(SQLAlchemyAsyncRepository[House]):
    model_type = House


class AffectedObjectRepository(SQLAlchemyAsyncRepository[AffectedObject]):
    model_type = AffectedObject


class HouseManagementRepository(SQLAlchemyAsyncRepository[HouseManagement]):
    model_type = HouseManagement
