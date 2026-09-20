from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from src.domains.geo.models import Address, AdministrativeArea, AffectedObject, House
from src.domains.geo.repositories import (
    AddressRepository,
    AdministrativeAreaRepository,
    AffectedObjectRepository,
    HouseRepository,
)


class AddressService(SQLAlchemyAsyncRepositoryService[Address]):
    repository_type = AddressRepository


class AdministrativeAreaService(SQLAlchemyAsyncRepositoryService[AdministrativeArea]):
    repository_type = AdministrativeAreaRepository


class HouseService(SQLAlchemyAsyncRepositoryService[House]):
    repository_type = HouseRepository


class AffectedObjectService(SQLAlchemyAsyncRepositoryService[AffectedObject]):
    repository_type = AffectedObjectRepository
