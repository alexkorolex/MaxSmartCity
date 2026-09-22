from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.dto import DTOData
from litestar.params import FromPath, Parameter
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.geo.models import Address, House
from src.domains.geo.schemas import AddressCreateDTO, AddressReadDTO, AddressUpdateDTO, HouseOption
from src.domains.geo.services import AddressService
from src.security.guards import require_resident


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


class HouseLookupController(Controller):
    path = "/geo/houses"
    tags = ("geo",)

    @get(
        "/",
        return_dto=None,
        name="geo:House:options",
        guards=[require_resident()],
    )
    async def list_options(
        self,
        db_session: NamedDependency[AsyncSession],
        q: Annotated[str | None, Parameter(min_length=2, max_length=200)] = None,
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> list[HouseOption]:
        statement = select(House.id, Address.formatted, Address.city, Address.district).join(
            Address, Address.id == House.address_id
        )
        if q:
            pattern = f"%{q.strip()}%"
            statement = statement.where(
                or_(
                    Address.formatted.ilike(pattern),
                    Address.city.ilike(pattern),
                    Address.district.ilike(pattern),
                )
            )
        rows = (
            await db_session.execute(
                statement.order_by(Address.formatted, House.id).limit(limit).offset(offset)
            )
        ).all()
        return [
            HouseOption(
                house_id=row.id,
                address=row.formatted,
                city=row.city,
                district=row.district,
            )
            for row in rows
        ]
