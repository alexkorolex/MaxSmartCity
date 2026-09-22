from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, get, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ClientException, NotFoundException
from litestar.params import FromPath, Parameter
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.state_machine import InvalidStateTransition
from src.database.logging import database_action
from src.domains.collaboration.models import Assignment, WorkItem
from src.domains.collaboration.schemas import (
    AssignmentReadDTO,
    TransitionAssignmentCommand,
    TransitionAssignmentResult,
    WorkItemReadDTO,
)
from src.domains.collaboration.services import (
    AssignmentService,
    CollaborationConflictError,
    CollaborationNotFoundError,
    WorkItemService,
)
from src.security.dependency import provide_principal
from src.security.guards import require_roles
from src.security.principal import Principal


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

    @post(
        "/{item_id:uuid}/status",
        status_code=200,
        name="collaboration:Assignment:transition",
        guards=[require_roles("admin", "housing_worker", "district_admin")],
        dependencies={"principal": Provide(provide_principal)},
    )
    async def transition_status(
        self,
        item_id: FromPath[UUID],
        data: TransitionAssignmentCommand,
        service: NamedDependency[AssignmentService],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> TransitionAssignmentResult:
        try:
            async with db_session.begin():
                return await service.transition(item_id, data, changed_by=principal.actor_id)
        except CollaborationNotFoundError as exc:
            raise NotFoundException(str(exc)) from exc
        except (CollaborationConflictError, InvalidStateTransition) as exc:
            raise ClientException(status_code=409, detail=str(exc)) from exc


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
