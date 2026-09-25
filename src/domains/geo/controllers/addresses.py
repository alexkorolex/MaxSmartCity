"""Addresses catalog and the list of cities that have any."""

from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.dto import DTOData
from litestar.params import FromPath, Parameter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.geo.models import Address
from src.domains.geo.schemas import (
    AddressCreateDTO,
    AddressReadDTO,
    AddressUpdateDTO,
)
from src.domains.geo.services import (
    AddressService,
)


def provide_address_service(db_session: NamedDependency[AsyncSession]) -> AddressService:
    return AddressService(session=db_session, auto_commit=True)


class AddressController(Controller):
    path = "/geo/addresses"
    tags = ("geo",)
    return_dto = AddressReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"service": Provide(provide_address_service, sync_to_thread=False)}

    @get("/", name="geo:Address:list")
    async def list_items(
        self,
        service: NamedDependency[AddressService],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Address]:
        with database_action("list", "geo.Address"):
            return await service.get_many(LimitOffset(limit=limit, offset=offset), order_by=("id", False))

    @get("/cities", name="geo:Address:cities", return_dto=None, cache=True)
    async def list_cities(self, db_session: NamedDependency[AsyncSession]) -> Sequence[str]:
        """Every distinct city that has at least one address on record - the complete set
        a filter dropdown should offer, not just whatever happens to already be loaded on
        the page (e.g. the small, unrelated set of organization headquarters cities)."""
        with database_action("list", "geo.Address"):
            result = await db_session.execute(
                select(Address.city).where(Address.city.is_not(None)).distinct().order_by(Address.city)
            )
            return [row[0] for row in result.all()]

    @get("/{item_id:uuid}", name="geo:Address:get")
    async def get_item(self, item_id: FromPath[UUID], service: NamedDependency[AddressService]) -> Address:
        with database_action("get", "geo.Address"):
            return await service.get(item_id)

    @post("/", dto=AddressCreateDTO, name="geo:Address:create")
    async def create_item(self, data: DTOData[Address], service: NamedDependency[AddressService]) -> Address:
        with database_action("create", "geo.Address"):
            return await service.create(data)

    @patch("/{item_id:uuid}", dto=AddressUpdateDTO, name="geo:Address:update")
    async def update_item(
        self,
        item_id: FromPath[UUID],
        data: DTOData[Address],
        service: NamedDependency[AddressService],
    ) -> Address:
        with database_action("update", "geo.Address"):
            return await service.update(data, item_id=item_id)

    @delete("/{item_id:uuid}", return_dto=None, name="geo:Address:delete")
    async def delete_item(self, item_id: FromPath[UUID], service: NamedDependency[AddressService]) -> None:
        with database_action("delete", "geo.Address"):
            await service.delete(item_id)
