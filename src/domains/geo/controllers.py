from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.dto import DTOData
from litestar.exceptions import NotFoundException
from litestar.params import FromPath, Parameter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.geo.models import Address, House
from src.domains.geo.schemas import AddressCreateDTO, AddressReadDTO, AddressUpdateDTO, HouseSummary
from src.domains.geo.services import AddressService


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


class HouseController(Controller):
    """Read-only: what a resident (or the "Сообщить о проблеме" flow) picks a home from.
    Houses are seeded by the ingestion pipeline, not created through this API."""

    path = "/geo/houses"
    tags = ("geo",)
    return_dto = None

    @get("/", name="geo:House:list")
    async def list_items(
        self,
        db_session: NamedDependency[AsyncSession],
        city: Annotated[str | None, Parameter()] = None,
        limit: Annotated[int, Parameter(ge=1, le=200)] = 200,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[HouseSummary]:
        with database_action("list", "geo.House"):
            statement = (
                select(House.id, Address.city, Address.street, Address.house_number, Address.formatted)
                .join(Address, Address.id == House.address_id)
                .order_by(Address.city, Address.street, Address.house_number)
                .limit(limit)
                .offset(offset)
            )
            if city:
                statement = statement.where(Address.city == city)
            rows = (await db_session.execute(statement)).all()
            return [
                HouseSummary(
                    house_id=row.id,
                    city=row.city,
                    street=row.street,
                    house_number=row.house_number,
                    formatted=row.formatted,
                )
                for row in rows
            ]

    @get("/{item_id:uuid}", name="geo:House:get")
    async def get_item(
        self, item_id: FromPath[UUID], db_session: NamedDependency[AsyncSession]
    ) -> HouseSummary:
        with database_action("get", "geo.House"):
            row = (
                await db_session.execute(
                    select(House.id, Address.city, Address.street, Address.house_number, Address.formatted)
                    .join(Address, Address.id == House.address_id)
                    .where(House.id == item_id)
                )
            ).first()
            if row is None:
                raise NotFoundException(f"House {item_id} was not found")
            return HouseSummary(
                house_id=row.id,
                city=row.city,
                street=row.street,
                house_number=row.house_number,
                formatted=row.formatted,
            )
