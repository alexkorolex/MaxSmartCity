from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated
from uuid import UUID

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, get, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ClientException, NotFoundException, PermissionDeniedException
from litestar.params import FromPath, Parameter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.state_machine import InvalidStateTransition
from src.database.logging import database_action
from src.domains.collaboration.enums import CommentVisibility
from src.domains.collaboration.models import Assignment, IncidentComment, WorkItem
from src.domains.collaboration.schemas import (
    AssignmentReadDTO,
    CreateAssignmentCommand,
    CreateAssignmentResult,
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
from src.domains.identity.admin_scope import resolve_organization_scope
from src.domains.identity.models import OperatorUser
from src.security.dependency import provide_principal
from src.security.guards import require_roles
from src.security.principal import Principal

_STAFF_ADMIN_ROLES = ("admin", "district_admin", "housing_worker")


def provide_assignment_service(db_session: NamedDependency[AsyncSession]) -> AssignmentService:
    return AssignmentService(session=db_session, auto_commit=True)


class AssignmentController(Controller):
    path = "/collaboration/assignments"
    tags = ("collaboration",)
    return_dto = AssignmentReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "service": Provide(provide_assignment_service, sync_to_thread=False),
            "principal": Provide(provide_principal),
        }

    @post(
        "/",
        status_code=201,
        return_dto=None,
        name="collaboration:Assignment:create-command",
        guards=[require_roles(*_STAFF_ADMIN_ROLES)],
    )
    async def create_assignment(
        self,
        data: CreateAssignmentCommand,
        service: NamedDependency[AssignmentService],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> CreateAssignmentResult:
        try:
            async with db_session.begin():
                return await service.create_for_incident(data, changed_by=principal.actor_id)
        except CollaborationNotFoundError as exc:
            raise NotFoundException(str(exc)) from exc
        except (CollaborationConflictError, InvalidStateTransition) as exc:
            raise ClientException(status_code=409, detail=str(exc)) from exc

    @get("/", name="collaboration:Assignment:list", guards=[require_roles(*_STAFF_ADMIN_ROLES)])
    async def list_items(
        self,
        service: NamedDependency[AssignmentService],
        principal: NamedDependency[Principal],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Assignment]:
        scope = resolve_organization_scope(principal)
        if scope.sees_nothing:
            return []
        with database_action("list", "collaboration.Assignment"):
            criteria = []
            if not scope.is_admin:
                criteria.append(Assignment.organization_id == scope.organization_id)
            return await service.get_many(
                LimitOffset(limit=limit, offset=offset), *criteria, order_by=("id", False)
            )

    @get("/{item_id:uuid}", name="collaboration:Assignment:get")
    async def get_item(
        self, item_id: FromPath[UUID], service: NamedDependency[AssignmentService]
    ) -> Assignment:
        with database_action("get", "collaboration.Assignment"):
            return await service.get(item_id)

    @post(
        "/{item_id:uuid}/status",
        status_code=200,
        return_dto=None,
        name="collaboration:Assignment:transition",
        guards=[require_roles(*_STAFF_ADMIN_ROLES)],
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
        self.dependencies = {
            "service": Provide(provide_workitem_service, sync_to_thread=False),
            "principal": Provide(provide_principal),
        }

    @get("/", name="collaboration:WorkItem:list", guards=[require_roles(*_STAFF_ADMIN_ROLES)])
    async def list_items(
        self,
        service: NamedDependency[WorkItemService],
        principal: NamedDependency[Principal],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[WorkItem]:
        scope = resolve_organization_scope(principal)
        if scope.sees_nothing:
            return []
        with database_action("list", "collaboration.WorkItem"):
            criteria = []
            if not scope.is_admin:
                criteria.append(WorkItem.organization_id == scope.organization_id)
            return await service.get_many(
                LimitOffset(limit=limit, offset=offset), *criteria, order_by=("id", False)
            )

    @get("/{item_id:uuid}", name="collaboration:WorkItem:get")
    async def get_item(self, item_id: FromPath[UUID], service: NamedDependency[WorkItemService]) -> WorkItem:
        with database_action("get", "collaboration.WorkItem"):
            return await service.get(item_id)


@dataclass(slots=True)
class IncidentCommentSummary:
    """Enriched over the raw ``IncidentComment`` row with the author's display name
    joined in - meaningfully more useful for a frontend comment thread than the bare
    ``author_user_id``."""

    id: UUID
    incident_id: UUID
    assignment_id: UUID | None
    work_item_id: UUID | None
    author_user_id: UUID
    author_display_name: str
    visibility: str
    text: str
    created_at: datetime


@dataclass(slots=True)
class IncidentCommentCreateRequest:
    incident_id: UUID
    text: str
    visibility: CommentVisibility = CommentVisibility.INTERNAL
    work_item_id: UUID | None = None
    assignment_id: UUID | None = None


class IncidentCommentController(Controller):
    """Admin-panel incident discussion thread. ``admin`` sees every comment (internal and
    public) on any incident; a ``district_admin``/``housing_worker`` only sees comments on
    incidents their own organization is assigned to."""

    path = "/collaboration/incident-comments"
    tags = ("collaboration",)
    return_dto = None

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"principal": Provide(provide_principal)}

    @get("/", name="collaboration:IncidentComment:list", guards=[require_roles(*_STAFF_ADMIN_ROLES)])
    async def list_items(
        self,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        incident_id: Annotated[UUID | None, Parameter()] = None,
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[IncidentCommentSummary]:
        scope = resolve_organization_scope(principal)
        if scope.sees_nothing:
            return []
        with database_action("list", "collaboration.IncidentComment"):
            statement = (
                select(
                    IncidentComment.id,
                    IncidentComment.incident_id,
                    IncidentComment.assignment_id,
                    IncidentComment.work_item_id,
                    IncidentComment.author_user_id,
                    OperatorUser.display_name.label("author_display_name"),
                    IncidentComment.visibility,
                    IncidentComment.text,
                    IncidentComment.created_at,
                )
                .select_from(IncidentComment)
                .join(OperatorUser, OperatorUser.id == IncidentComment.author_user_id)
            )
            if incident_id is not None:
                statement = statement.where(IncidentComment.incident_id == incident_id)
            if not scope.is_admin:
                assigned_incident_ids = select(Assignment.incident_id).where(
                    Assignment.organization_id == scope.organization_id
                )
                statement = statement.where(IncidentComment.incident_id.in_(assigned_incident_ids))
            statement = statement.order_by(IncidentComment.created_at.desc()).limit(limit).offset(offset)
            rows = (await db_session.execute(statement)).all()
            return [
                IncidentCommentSummary(
                    id=row.id,
                    incident_id=row.incident_id,
                    assignment_id=row.assignment_id,
                    work_item_id=row.work_item_id,
                    author_user_id=row.author_user_id,
                    author_display_name=row.author_display_name,
                    visibility=row.visibility.value,
                    text=row.text,
                    created_at=row.created_at,
                )
                for row in rows
            ]

    @post("/", name="collaboration:IncidentComment:create", guards=[require_roles(*_STAFF_ADMIN_ROLES)])
    async def create_item(
        self,
        data: IncidentCommentCreateRequest,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> IncidentCommentSummary:
        scope = resolve_organization_scope(principal)
        with database_action("create", "collaboration.IncidentComment"):
            if not scope.is_admin:
                if scope.organization_id is None:
                    raise PermissionDeniedException("No active organization membership")
                assigned = await db_session.scalar(
                    select(Assignment.id)
                    .where(
                        Assignment.incident_id == data.incident_id,
                        Assignment.organization_id == scope.organization_id,
                    )
                    .limit(1)
                )
                if assigned is None:
                    raise PermissionDeniedException("Organization is not assigned to this incident")

            comment = IncidentComment(
                incident_id=data.incident_id,
                assignment_id=data.assignment_id,
                work_item_id=data.work_item_id,
                author_user_id=principal.actor_id,
                visibility=data.visibility,
                text=data.text,
            )
            db_session.add(comment)
            await db_session.commit()

            statement = (
                select(
                    IncidentComment.id,
                    IncidentComment.incident_id,
                    IncidentComment.assignment_id,
                    IncidentComment.work_item_id,
                    IncidentComment.author_user_id,
                    OperatorUser.display_name.label("author_display_name"),
                    IncidentComment.visibility,
                    IncidentComment.text,
                    IncidentComment.created_at,
                )
                .select_from(IncidentComment)
                .join(OperatorUser, OperatorUser.id == IncidentComment.author_user_id)
                .where(IncidentComment.id == comment.id)
            )
            row = (await db_session.execute(statement)).first()
            if row is None:
                raise NotFoundException(f"Incident comment {comment.id} was not found")
            return IncidentCommentSummary(
                id=row.id,
                incident_id=row.incident_id,
                assignment_id=row.assignment_id,
                work_item_id=row.work_item_id,
                author_user_id=row.author_user_id,
                author_display_name=row.author_display_name,
                visibility=row.visibility.value,
                text=row.text,
                created_at=row.created_at,
            )
