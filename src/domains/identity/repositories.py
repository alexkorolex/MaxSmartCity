from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from src.domains.identity.models import OperatorUser, Organization, Resident


class OrganizationRepository(SQLAlchemyAsyncRepository[Organization]):
    model_type = Organization


class ResidentRepository(SQLAlchemyAsyncRepository[Resident]):
    model_type = Resident


class OperatorUserRepository(SQLAlchemyAsyncRepository[OperatorUser]):
    model_type = OperatorUser
