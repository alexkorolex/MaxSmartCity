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
from src.domains.reports.enums import ReportSourceType
from src.domains.reports.models import ProblemCategory, Report
from src.domains.reports.schemas import (
    ProblemCategoryCreateDTO,
    ProblemCategoryReadDTO,
    ProblemCategoryUpdateDTO,
    ReportCreateDTO,
    ReportReadDTO,
)
from src.domains.reports.services import ProblemCategoryService, ReportService
from src.security.dependency import provide_principal
from src.security.guards import require_resident
from src.security.principal import Principal


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


def provide_report_service(db_session: NamedDependency[AsyncSession]) -> ReportService:
    return ReportService(session=db_session, auto_commit=True)


class ReportController(Controller):
    path = "/reports"
    tags = ("reports",)
    return_dto = ReportReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "service": Provide(provide_report_service, sync_to_thread=False),
            "principal": Provide(provide_principal),
        }

    @get("/", name="reports:Report:list")
    async def list_items(
        self,
        service: NamedDependency[ReportService],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Report]:
        with database_action("list", "reports.Report"):
            return await service.get_many(LimitOffset(limit=limit, offset=offset), order_by=("id", False))

    @get("/mine", name="reports:Report:mine", guards=[require_resident()])
    async def list_mine(
        self,
        service: NamedDependency[ReportService],
        principal: NamedDependency[Principal],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Report]:
        with database_action("list", "reports.Report"):
            return await service.get_many(
                LimitOffset(limit=limit, offset=offset),
                Report.resident_id == principal.actor_id,
                order_by=("received_at", True),
            )

    @get("/{item_id:uuid}", name="reports:Report:get")
    async def get_item(self, item_id: FromPath[UUID], service: NamedDependency[ReportService]) -> Report:
        with database_action("get", "reports.Report"):
            return await service.get(item_id)

    @post(
        "/",
        dto=ReportCreateDTO,
        name="reports:Report:create",
        guards=[require_resident()],
    )
    async def create_item(
        self,
        data: DTOData[Report],
        service: NamedDependency[ReportService],
        principal: NamedDependency[Principal],
    ) -> Report:
        with database_action("create", "reports.Report"):
            report = data.create_instance()
            report.resident_id = principal.actor_id
            report.source_type = ReportSourceType.MAX
            return await service.create(report)
