from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.dto import DTOData
from litestar.params import FromPath, Parameter
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.identity.models import Organization
from src.domains.identity.schemas import (
    OrganizationCreateDTO,
    OrganizationReadDTO,
    OrganizationUpdateDTO,
)
from src.domains.identity.services import OrganizationService


def provide_organization_service(db_session: NamedDependency[AsyncSession]) -> OrganizationService:
    return OrganizationService(session=db_session, auto_commit=True)


class OrganizationController(Controller):
    path = "/identity/organizations"
    tags = ("identity",)
    return_dto = OrganizationReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"service": Provide(provide_organization_service, sync_to_thread=False)}

    @get("/", name="identity:Organization:list")
    async def list_items(
        self,
        service: NamedDependency[OrganizationService],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Organization]:
        with database_action("list", "identity.Organization"):
            return await service.get_many(LimitOffset(limit=limit, offset=offset), order_by=("id", False))

    @get("/{item_id:uuid}", name="identity:Organization:get")
    async def get_item(
        self, item_id: FromPath[UUID], service: NamedDependency[OrganizationService]
    ) -> Organization:
        with database_action("get", "identity.Organization"):
            return await service.get(item_id)

    @post("/", dto=OrganizationCreateDTO, name="identity:Organization:create")
    async def create_item(
        self, data: DTOData[Organization], service: NamedDependency[OrganizationService]
    ) -> Organization:
        with database_action("create", "identity.Organization"):
            return await service.create(data)

    @patch("/{item_id:uuid}", dto=OrganizationUpdateDTO, name="identity:Organization:update")
    async def update_item(
        self,
        item_id: FromPath[UUID],
        data: DTOData[Organization],
        service: NamedDependency[OrganizationService],
    ) -> Organization:
        with database_action("update", "identity.Organization"):
            return await service.update(data, item_id=item_id)

    @delete("/{item_id:uuid}", return_dto=None, name="identity:Organization:delete")
    async def delete_item(
        self, item_id: FromPath[UUID], service: NamedDependency[OrganizationService]
    ) -> None:
        with database_action("delete", "identity.Organization"):
            await service.delete(item_id)
