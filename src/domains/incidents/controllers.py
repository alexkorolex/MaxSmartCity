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
from src.domains.incidents.models import Incident
from src.domains.incidents.schemas import (
    GroupReportCommand,
    GroupReportResult,
    IncidentReadDTO,
    TransitionIncidentCommand,
    TransitionIncidentResult,
)
from src.domains.incidents.services import (
    IncidentCoreConflictError,
    IncidentCoreNotFoundError,
    IncidentCoreService,
    IncidentService,
)
from src.security.dependency import provide_principal
from src.security.guards import require_bot_secret, require_roles
from src.security.principal import Principal


def provide_incident_service(db_session: NamedDependency[AsyncSession]) -> IncidentService:
    return IncidentService(session=db_session, auto_commit=True)


class IncidentController(Controller):
    path = "/incidents"
    tags = ("incidents",)
    return_dto = IncidentReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"service": Provide(provide_incident_service, sync_to_thread=False)}

    @get("/", name="incidents:Incident:list")
    async def list_items(
        self,
        service: NamedDependency[IncidentService],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Incident]:
        with database_action("list", "incidents.Incident"):
            return await service.get_many(LimitOffset(limit=limit, offset=offset), order_by=("id", False))

    @get("/{item_id:uuid}", name="incidents:Incident:get")
    async def get_item(self, item_id: FromPath[UUID], service: NamedDependency[IncidentService]) -> Incident:
        with database_action("get", "incidents.Incident"):
            return await service.get(item_id)

    @post(
        "/group-reports/{report_id:uuid}",
        status_code=200,
        name="incidents:group-report",
        guards=[require_bot_secret()],
    )
    async def group_report(
        self,
        report_id: FromPath[UUID],
        data: GroupReportCommand,
        db_session: NamedDependency[AsyncSession],
    ) -> GroupReportResult:
        try:
            async with db_session.begin():
                return await IncidentCoreService(db_session).group_report(report_id, data)
        except IncidentCoreNotFoundError as exc:
            raise NotFoundException(str(exc)) from exc
        except (IncidentCoreConflictError, InvalidStateTransition) as exc:
            raise ClientException(status_code=409, detail=str(exc)) from exc

    @post(
        "/{item_id:uuid}/status",
        status_code=200,
        name="incidents:transition-status",
        guards=[require_roles("admin", "housing_worker", "district_admin")],
        dependencies={"principal": Provide(provide_principal)},
    )
    async def transition_status(
        self,
        item_id: FromPath[UUID],
        data: TransitionIncidentCommand,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> TransitionIncidentResult:
        try:
            async with db_session.begin():
                return await IncidentCoreService(db_session).transition_incident(
                    item_id, data, changed_by_id=principal.actor_id
                )
        except IncidentCoreNotFoundError as exc:
            raise NotFoundException(str(exc)) from exc
        except (IncidentCoreConflictError, InvalidStateTransition) as exc:
            raise ClientException(status_code=409, detail=str(exc)) from exc
