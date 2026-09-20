from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, get
from litestar.di import NamedDependency, Provide
from litestar.params import FromPath, Parameter
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.collaboration.models import Assignment, WorkItem
from src.domains.collaboration.schemas import AssignmentReadDTO, WorkItemReadDTO
from src.domains.collaboration.services import AssignmentService, WorkItemService


def provide_assignment_service(db_session: NamedDependency[AsyncSession]) -> AssignmentService:
    return AssignmentService(session=db_session, auto_commit=True)


class AssignmentController(Controller):
    path = "/collaboration/assignments"
    tags = ("collaboration",)
    return_dto = AssignmentReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"service": Provide(provide_assignment_service, sync_to_thread=False)}

    @get("/", name="collaboration:Assignment:list")
    async def list_items(
        self,
        service: NamedDependency[AssignmentService],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Assignment]:
        with database_action("list", "collaboration.Assignment"):
            return await service.get_many(LimitOffset(limit=limit, offset=offset), order_by=("id", False))

    @get("/{item_id:uuid}", name="collaboration:Assignment:get")
    async def get_item(
        self, item_id: FromPath[UUID], service: NamedDependency[AssignmentService]
    ) -> Assignment:
        with database_action("get", "collaboration.Assignment"):
            return await service.get(item_id)


def provide_workitem_service(db_session: NamedDependency[AsyncSession]) -> WorkItemService:
    return WorkItemService(session=db_session, auto_commit=True)


class WorkItemController(Controller):
    path = "/collaboration/work-items"
    tags = ("collaboration",)
    return_dto = WorkItemReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"service": Provide(provide_workitem_service, sync_to_thread=False)}

    @get("/", name="collaboration:WorkItem:list")
    async def list_items(
        self,
        service: NamedDependency[WorkItemService],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[WorkItem]:
        with database_action("list", "collaboration.WorkItem"):
            return await service.get_many(LimitOffset(limit=limit, offset=offset), order_by=("id", False))

    @get("/{item_id:uuid}", name="collaboration:WorkItem:get")
    async def get_item(self, item_id: FromPath[UUID], service: NamedDependency[WorkItemService]) -> WorkItem:
        with database_action("get", "collaboration.WorkItem"):
            return await service.get(item_id)
