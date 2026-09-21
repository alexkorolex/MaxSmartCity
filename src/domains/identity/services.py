from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from src.domains.identity.models import OperatorUser, Organization, Resident
from src.domains.identity.repositories import (
    OperatorUserRepository,
    OrganizationRepository,
    ResidentRepository,
)


class OrganizationService(SQLAlchemyAsyncRepositoryService[Organization]):
    repository_type = OrganizationRepository


class ResidentService(SQLAlchemyAsyncRepositoryService[Resident]):
    repository_type = ResidentRepository


class OperatorUserService(SQLAlchemyAsyncRepositoryService[OperatorUser]):
    repository_type = OperatorUserRepository
