"""Problem categories residents file reports under."""

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
from src.domains.reports.models import ProblemCategory
from src.domains.reports.schemas import (
    ProblemCategoryCreateDTO,
    ProblemCategoryReadDTO,
    ProblemCategoryUpdateDTO,
)
from src.domains.reports.services import (
    ProblemCategoryService,
)


def provide_problemcategory_service(
    db_session: NamedDependency[AsyncSession],
) -> ProblemCategoryService:
    return ProblemCategoryService(session=db_session, auto_commit=True)


class ProblemCategoryController(Controller):
    path = "/reports/categories"
    tags = ("reports",)
    return_dto = ProblemCategoryReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"service": Provide(provide_problemcategory_service, sync_to_thread=False)}

    @get("/", name="reports:ProblemCategory:list", cache=True)
    async def list_items(
        self,
        service: NamedDependency[ProblemCategoryService],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[ProblemCategory]:
        with database_action("list", "reports.ProblemCategory"):
            return await service.get_many(LimitOffset(limit=limit, offset=offset), order_by=("id", False))

    @get("/{item_id:uuid}", name="reports:ProblemCategory:get")
    async def get_item(
        self, item_id: FromPath[UUID], service: NamedDependency[ProblemCategoryService]
    ) -> ProblemCategory:
        with database_action("get", "reports.ProblemCategory"):
            return await service.get(item_id)

    @post("/", dto=ProblemCategoryCreateDTO, name="reports:ProblemCategory:create")
    async def create_item(
        self, data: DTOData[ProblemCategory], service: NamedDependency[ProblemCategoryService]
    ) -> ProblemCategory:
        with database_action("create", "reports.ProblemCategory"):
            return await service.create(data)

    @patch("/{item_id:uuid}", dto=ProblemCategoryUpdateDTO, name="reports:ProblemCategory:update")
    async def update_item(
        self,
        item_id: FromPath[UUID],
        data: DTOData[ProblemCategory],
        service: NamedDependency[ProblemCategoryService],
    ) -> ProblemCategory:
        with database_action("update", "reports.ProblemCategory"):
            return await service.update(data, item_id=item_id)

    @delete("/{item_id:uuid}", return_dto=None, name="reports:ProblemCategory:delete")
    async def delete_item(
        self, item_id: FromPath[UUID], service: NamedDependency[ProblemCategoryService]
    ) -> None:
        with database_action("delete", "reports.ProblemCategory"):
            await service.delete(item_id)
