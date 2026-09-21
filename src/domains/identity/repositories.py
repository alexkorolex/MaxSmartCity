from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from src.domains.identity.models import Department, OperatorUser, Organization, Resident


class OrganizationRepository(SQLAlchemyAsyncRepository[Organization]):
    model_type = Organization


class DepartmentRepository(SQLAlchemyAsyncRepository[Department]):
    model_type = Department


class ResidentRepository(SQLAlchemyAsyncRepository[Resident]):
    model_type = Resident


class OperatorUserRepository(SQLAlchemyAsyncRepository[OperatorUser]):
    model_type = OperatorUser
