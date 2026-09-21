from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from src.domains.identity.models import Department, OperatorUser, Organization, Resident
from src.domains.identity.repositories import (
    DepartmentRepository,
    OperatorUserRepository,
    OrganizationRepository,
    ResidentRepository,
)


class OrganizationService(SQLAlchemyAsyncRepositoryService[Organization]):
    repository_type = OrganizationRepository


class DepartmentService(SQLAlchemyAsyncRepositoryService[Department]):
    repository_type = DepartmentRepository


class ResidentService(SQLAlchemyAsyncRepositoryService[Resident]):
    repository_type = ResidentRepository


class OperatorUserService(SQLAlchemyAsyncRepositoryService[OperatorUser]):
    repository_type = OperatorUserRepository
