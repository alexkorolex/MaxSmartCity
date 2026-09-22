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

    async def upsert_by_max_user_id(
        self, *, max_user_id: int, username: str | None, display_name: str | None
    ) -> Resident:
        """Shared by the bot-token auth endpoint and the MAX webhook handler - both
        identify a resident purely by their MAX ``max_user_id``, no login/password."""
        resident = await self.get_one_or_none(max_user_id=max_user_id)
        if resident is None:
            return await self.create(
                Resident(max_user_id=max_user_id, username=username, display_name=display_name)
            )
        if username != resident.username or display_name != resident.display_name:
            return await self.update(
                {"username": username, "display_name": display_name}, item_id=resident.id
            )
        return resident


class OperatorUserService(SQLAlchemyAsyncRepositoryService[OperatorUser]):
    repository_type = OperatorUserRepository
