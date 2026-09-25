"""Incidents for residents: their house's problems, confirming or disputing a resolution."""

from collections.abc import Sequence
from uuid import UUID

from litestar import Controller, Router, get, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ClientException, HTTPException, NotFoundException, PermissionDeniedException
from litestar.params import FromPath
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.incidents.controllers.staff import provide_incident_service
from src.domains.incidents.enums import IncidentStatus, ResolutionDisputeStatus, ResolutionFeedback
from src.domains.incidents.models import (
    Incident,
    IncidentAffectedHouse,
    IncidentReportLink,
    ResolutionDispute,
)
from src.domains.incidents.schemas import (
    IncidentDisputeRequest,
    IncidentReadDTO,
    ResolutionDisputeReadDTO,
    ResolutionFeedbackCommand,
    ResolutionFeedbackResult,
)
from src.domains.incidents.services import (
    IncidentCoreConflictError,
    IncidentCoreNotFoundError,
    IncidentCoreService,
    IncidentService,
)
from src.domains.reports.models import Report
from src.security.dependency import provide_principal
from src.security.guards import require_resident
from src.security.principal import Principal


async def _require_resident_link(
    db_session: AsyncSession, *, incident_id: UUID, resident_id: UUID
) -> UUID | None:
    """Return the resident's active ``report_id`` linked to this incident, or raise if none."""
    result = await db_session.execute(
        select(IncidentReportLink.report_id)
        .join(Report, Report.id == IncidentReportLink.report_id)
        .where(
            IncidentReportLink.incident_id == incident_id,
            IncidentReportLink.is_active.is_(True),
            Report.resident_id == resident_id,
        )
    )
    report_id = result.scalars().first()
    if report_id is None:
        raise PermissionDeniedException("Resident is not linked to this incident")
    return report_id


class IncidentResidentController(Controller):
    """What a resident sees and says about incidents on their house."""

    path = "/incidents"
    tags = ("incidents",)
    return_dto = IncidentReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "service": Provide(provide_incident_service, sync_to_thread=False),
            "principal": Provide(provide_principal),
        }

    @get("/my-house", name="incidents:Incident:my-house", guards=[require_resident()])
    async def list_my_house(
        self,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> Sequence[Incident]:
        with database_action("list", "incidents.Incident"):
            latest_house = (
                (
                    await db_session.execute(
                        select(Report.house_id)
                        .where(
                            Report.resident_id == principal.actor_id,
                            Report.house_id.is_not(None),
                        )
                        .order_by(Report.received_at.desc())
                        .limit(1)
                    )
                )
                .scalars()
                .first()
            )
            if latest_house is None:
                return []

            result = await db_session.execute(
                select(Incident)
                .join(IncidentAffectedHouse, IncidentAffectedHouse.incident_id == Incident.id)
                .where(IncidentAffectedHouse.house_id == latest_house)
                .order_by(Incident.first_report_at.desc())
            )
            return list(result.scalars().all())

    @post(
        "/{item_id:uuid}/confirm-resolution",
        name="incidents:Incident:confirm-resolution",
        guards=[require_resident()],
    )
    async def confirm_resolution(
        self,
        item_id: FromPath[UUID],
        service: NamedDependency[IncidentService],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> Incident:
        with database_action("update", "incidents.Incident"):
            report_id = await _require_resident_link(
                db_session, incident_id=item_id, resident_id=principal.actor_id
            )

            incident = await service.get(item_id)
            if incident.status != IncidentStatus.AWAITING_CONFIRMATION:
                raise HTTPException(status_code=409, detail="Incident is not awaiting confirmation")

            # Same path as /resolution-feedback: closes the incident together with every
            # resident request linked to it, and notifies those residents.
            assert report_id is not None
            await IncidentCoreService(db_session).record_resolution_feedback(
                item_id,
                ResolutionFeedbackCommand(report_id=report_id, feedback=ResolutionFeedback.CONFIRMED),
                resident_id=principal.actor_id,
            )
            await db_session.commit()
            return incident

    @post(
        "/{item_id:uuid}/dispute-resolution",
        name="incidents:Incident:dispute-resolution",
        guards=[require_resident()],
        return_dto=ResolutionDisputeReadDTO,
    )
    async def dispute_resolution(
        self,
        item_id: FromPath[UUID],
        data: IncidentDisputeRequest,
        service: NamedDependency[IncidentService],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> ResolutionDispute:
        with database_action("create", "incidents.ResolutionDispute"):
            report_id = await _require_resident_link(
                db_session, incident_id=item_id, resident_id=principal.actor_id
            )

            incident = await service.get(item_id)
            if incident.status != IncidentStatus.AWAITING_CONFIRMATION:
                raise HTTPException(status_code=409, detail="Incident is not awaiting confirmation")

            dispute = ResolutionDispute(
                incident_id=item_id,
                resident_id=principal.actor_id,
                report_id=report_id,
                status=ResolutionDisputeStatus.OPEN,
                comment=data.comment,
            )
            db_session.add(dispute)
            await IncidentCoreService(db_session).transition_for_resident(
                incident,
                IncidentStatus.RESOLUTION_DISPUTED,
                resident_id=principal.actor_id,
                reason=data.comment,
            )
            await db_session.commit()
            return dispute

    @get(
        "/{item_id:uuid}/disputes",
        name="incidents:Incident:disputes",
        guards=[require_resident()],
        return_dto=ResolutionDisputeReadDTO,
    )
    async def list_disputes(
        self,
        item_id: FromPath[UUID],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> Sequence[ResolutionDispute]:
        with database_action("list", "incidents.ResolutionDispute"):
            result = await db_session.execute(
                select(ResolutionDispute)
                .where(
                    ResolutionDispute.incident_id == item_id,
                    ResolutionDispute.resident_id == principal.actor_id,
                )
                .order_by(ResolutionDispute.created_at.desc())
            )
            return list(result.scalars().all())

    @post(
        "/{item_id:uuid}/resolution-feedback",
        status_code=200,
        return_dto=None,
        name="incidents:Incident:resolution-feedback",
        guards=[require_resident()],
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
        except IncidentCoreConflictError as exc:
            raise ClientException(status_code=409, detail=str(exc)) from exc
