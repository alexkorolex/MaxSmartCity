from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, get, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ClientException, NotFoundException
from litestar.params import FromPath, Parameter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.enums import ActorType
from src.common.state_machine import InvalidStateTransition
from src.database.logging import database_action
from src.domains.incidents.models import Incident, IncidentReportLink
from src.domains.incidents.schemas import (
    GroupReportCommand,
    GroupReportResult,
    IncidentCardResult,
    IncidentReadDTO,
    ResolutionFeedbackCommand,
    ResolutionFeedbackResult,
    TransitionIncidentCommand,
    TransitionIncidentResult,
)
from src.domains.incidents.services import (
    ACTIVE_INCIDENT_STATUSES,
    IncidentCoreConflictError,
    IncidentCoreNotFoundError,
    IncidentCoreService,
    IncidentService,
)
from src.domains.reports.models import Report
from src.security.dependency import provide_principal
from src.security.guards import require_bot_secret, require_resident, require_roles
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

    @get(
        "/",
        name="incidents:Incident:list",
        guards=[require_roles("admin", "housing_worker", "district_admin")],
    )
    async def list_items(
        self,
        service: NamedDependency[IncidentService],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Incident]:
        with database_action("list", "incidents.Incident"):
            return await service.get_many(LimitOffset(limit=limit, offset=offset), order_by=("id", False))

    @get(
        "/my-house",
        name="incidents:Incident:my-house",
        guards=[require_resident()],
        dependencies={"principal": Provide(provide_principal)},
    )
    async def list_my_house(
        self,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Incident]:
        latest_house_id = await db_session.scalar(
            select(Report.house_id)
            .where(Report.resident_id == principal.actor_id, Report.house_id.is_not(None))
            .order_by(Report.received_at.desc())
            .limit(1)
        )
        if latest_house_id is None:
            return []
        return list(
            (
                await db_session.scalars(
                    select(Incident)
                    .join(
                        IncidentReportLink,
                        IncidentReportLink.incident_id == Incident.id,
                    )
                    .join(Report, Report.id == IncidentReportLink.report_id)
                    .where(
                        Report.house_id == latest_house_id,
                        IncidentReportLink.is_active.is_(True),
                        Incident.status.in_(ACTIVE_INCIDENT_STATUSES),
                    )
                    .distinct()
                    .order_by(Incident.last_report_at.desc().nullslast(), Incident.id)
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
        )

    @get(
        "/{item_id:uuid}",
        name="incidents:Incident:get",
        dependencies={"principal": Provide(provide_principal)},
    )
    async def get_item(
        self,
        item_id: FromPath[UUID],
        service: NamedDependency[IncidentService],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> Incident:
        with database_action("get", "incidents.Incident"):
            incident = await service.get(item_id)
        if principal.actor_type is ActorType.RESIDENT:
            report_id = await db_session.scalar(
                select(Report.id)
                .join(IncidentReportLink, IncidentReportLink.report_id == Report.id)
                .where(
                    Report.resident_id == principal.actor_id,
                    IncidentReportLink.incident_id == item_id,
                    IncidentReportLink.is_active.is_(True),
                )
                .limit(1)
            )
            if report_id is None:
                raise NotFoundException(f"Incident {item_id} was not found")
        return incident

    @get(
        "/{item_id:uuid}/card",
        name="incidents:Incident:card",
        return_dto=None,
        guards=[require_roles("admin", "housing_worker", "district_admin")],
    )
    async def get_card(
        self,
        item_id: FromPath[UUID],
        db_session: NamedDependency[AsyncSession],
    ) -> IncidentCardResult:
        try:
            return await IncidentCoreService(db_session).get_card(item_id)
        except IncidentCoreNotFoundError as exc:
            raise NotFoundException(str(exc)) from exc

    @post(
        "/group-reports/{report_id:uuid}",
        status_code=200,
        return_dto=None,
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
        return_dto=None,
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

    @post(
        "/{item_id:uuid}/resolution-feedback",
        status_code=200,
        return_dto=None,
        name="incidents:resolution-feedback",
        guards=[require_resident()],
        dependencies={"principal": Provide(provide_principal)},
    )
    async def resolution_feedback(
        self,
        item_id: FromPath[UUID],
        data: ResolutionFeedbackCommand,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> ResolutionFeedbackResult:
        try:
            async with db_session.begin():
                return await IncidentCoreService(db_session).record_resolution_feedback(
                    item_id, data, resident_id=principal.actor_id
                )
        except IncidentCoreNotFoundError as exc:
            raise NotFoundException(str(exc)) from exc
        except (IncidentCoreConflictError, InvalidStateTransition) as exc:
            raise ClientException(status_code=409, detail=str(exc)) from exc
