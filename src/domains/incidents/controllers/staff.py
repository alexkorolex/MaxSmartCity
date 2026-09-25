"""Incidents for staff: the scoped list and card, grouping, status changes, «Работы выполнены»."""

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

from src.common.state_machine import InvalidStateTransition
from src.database.logging import database_action
from src.domains.geo.models import Address, House
from src.domains.identity.admin_scope import resolve_organization_scope
from src.domains.incidents.models import (
    Incident,
    IncidentAffectedHouse,
)
from src.domains.incidents.schemas import (
    CompleteIncidentCommand,
    GroupReportCommand,
    GroupReportResult,
    IncidentCardResult,
    IncidentReadDTO,
    TransitionIncidentCommand,
    TransitionIncidentResult,
)
from src.domains.incidents.scope import organization_incident_ids
from src.domains.incidents.services import (
    IncidentCoreConflictError,
    IncidentCoreNotFoundError,
    IncidentCoreService,
    IncidentService,
)
from src.security.dependency import provide_principal
from src.security.guards import require_roles
from src.security.principal import Principal

_STAFF_ROLES = ("admin", "housing_worker", "district_admin")


def provide_incident_service(db_session: NamedDependency[AsyncSession]) -> IncidentService:
    return IncidentService(session=db_session, auto_commit=True)


async def _ensure_incident_in_scope(
    db_session: AsyncSession, principal: Principal, incident_id: UUID
) -> None:
    """404 unless the caller may work on this incident: an admin always, other staff only
    within their organization's houses and assignments (``organization_incident_ids``)."""
    scope = resolve_organization_scope(principal)
    if scope.is_admin:
        return
    in_scope = scope.organization_id is not None and await db_session.scalar(
        select(Incident.id).where(
            Incident.id == incident_id, Incident.id.in_(organization_incident_ids(scope.organization_id))
        )
    )
    if not in_scope:
        raise NotFoundException(f"Incident {incident_id} was not found")


class IncidentController(Controller):
    """Staff work on incidents within their organization's houses and assignments."""

    path = "/incidents"
    tags = ("incidents",)
    return_dto = IncidentReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "service": Provide(provide_incident_service, sync_to_thread=False),
            "principal": Provide(provide_principal),
        }

    @get(
        "/",
        name="incidents:Incident:list",
        guards=[require_roles(*_STAFF_ROLES)],
    )
    async def list_items(
        self,
        service: NamedDependency[IncidentService],
        principal: NamedDependency[Principal],
        city: Annotated[str | None, Parameter()] = None,
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Incident]:
        scope = resolve_organization_scope(principal)
        if scope.sees_nothing:
            return []
        with database_action("list", "incidents.Incident"):
            criteria = []
            if city and scope.is_admin:
                house_ids = (
                    select(House.id).join(Address, Address.id == House.address_id).where(Address.city == city)
                )
                incident_ids = select(IncidentAffectedHouse.incident_id).where(
                    IncidentAffectedHouse.house_id.in_(house_ids)
                )
                criteria.append(Incident.id.in_(incident_ids))
            if not scope.is_admin:
                # Residents' requests reach their УК/ТСЖ through its houses, before triage.
                assert scope.organization_id is not None
                criteria.append(Incident.id.in_(organization_incident_ids(scope.organization_id)))
            return await service.get_many(
                LimitOffset(limit=limit, offset=offset), *criteria, order_by=("id", False)
            )

    @get("/{item_id:uuid}", name="incidents:Incident:get")
    async def get_item(self, item_id: FromPath[UUID], service: NamedDependency[IncidentService]) -> Incident:
        with database_action("get", "incidents.Incident"):
            return await service.get(item_id)

    @post(
        "/group-reports/{report_id:uuid}",
        status_code=200,
        return_dto=None,
        name="incidents:Incident:group-report",
        guards=[require_roles(*_STAFF_ROLES)],
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
        except IncidentCoreConflictError as exc:
            raise ClientException(status_code=409, detail=str(exc)) from exc

    @post(
        "/{item_id:uuid}/status",
        status_code=200,
        return_dto=None,
        name="incidents:Incident:transition-status",
        guards=[require_roles(*_STAFF_ROLES)],
    )
    async def transition_status(
        self,
        item_id: FromPath[UUID],
        data: TransitionIncidentCommand,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> TransitionIncidentResult:
        await _ensure_incident_in_scope(db_session, principal, item_id)
        try:
            result = await IncidentCoreService(db_session).transition_incident(
                item_id, data, changed_by_id=principal.actor_id
            )
        except IncidentCoreNotFoundError as exc:
            raise NotFoundException(str(exc)) from exc
        except (IncidentCoreConflictError, InvalidStateTransition) as exc:
            raise ClientException(status_code=409, detail=str(exc)) from exc
        await db_session.commit()
        return result

    @post(
        "/{item_id:uuid}/complete",
        status_code=200,
        return_dto=None,
        name="incidents:Incident:complete",
        guards=[require_roles(*_STAFF_ROLES)],
    )
    async def complete(
        self,
        item_id: FromPath[UUID],
        data: CompleteIncidentCommand,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> TransitionIncidentResult:
        """ "Работы выполнены": the caller's organization finished its part - the incident
        moves to ``RESOLVED`` and residents are asked to confirm (see
        ``IncidentCoreService.complete_by_staff``)."""
        await _ensure_incident_in_scope(db_session, principal, item_id)
        try:
            with database_action("update", "incidents.Incident"):
                result = await IncidentCoreService(db_session).complete_by_staff(
                    item_id,
                    data,
                    changed_by=principal.actor_id,
                    organization_id=principal.organization_id,
                )
        except IncidentCoreNotFoundError as exc:
            raise NotFoundException(str(exc)) from exc
        except (IncidentCoreConflictError, InvalidStateTransition) as exc:
            raise ClientException(status_code=409, detail=str(exc)) from exc
        await db_session.commit()
        return result

    @get(
        "/{item_id:uuid}/card",
        return_dto=None,
        name="incidents:Incident:card",
        guards=[require_roles(*_STAFF_ROLES)],
    )
    async def get_card(
        self,
        item_id: FromPath[UUID],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> IncidentCardResult:
        await _ensure_incident_in_scope(db_session, principal, item_id)
        try:
            with database_action("get", "incidents.Incident"):
                return await IncidentCoreService(db_session).get_card(item_id)
        except IncidentCoreNotFoundError as exc:
            raise NotFoundException(str(exc)) from exc
