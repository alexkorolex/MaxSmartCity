"""The incident application services: the incident card (the read model staff see),
the assembled workflow service, and the generic repository services for the incident
aggregates."""

from __future__ import annotations

from uuid import UUID

from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy import select

from src.domains.collaboration.models import Assignment
from src.domains.geo.models import Address, House
from src.domains.incidents.models import (
    Incident,
    IncidentAffectedHouse,
    IncidentReportLink,
    IncidentStatusHistory,
    ResolutionDispute,
)
from src.domains.incidents.repositories import IncidentRepository, ResolutionDisputeRepository
from src.domains.incidents.schemas import (
    IncidentAssignmentSummary,
    IncidentCardResult,
    IncidentDisputeSummary,
    IncidentHistorySummary,
    IncidentHouseSummary,
    IncidentReportSummary,
)
from src.domains.incidents.services.base import (
    IncidentCoreBase,
    IncidentCoreNotFoundError,
)
from src.domains.incidents.services.report_grouping import IncidentGroupingMixin
from src.domains.incidents.services.resolution import IncidentResolutionMixin
from src.domains.reports.models import Report


class IncidentCardMixin(IncidentCoreBase):
    """Read model of a single incident."""

    async def get_card(self, incident_id: UUID) -> IncidentCardResult:
        incident = await self.session.get(Incident, incident_id)
        if incident is None:
            raise IncidentCoreNotFoundError(f"Incident {incident_id} was not found")
        house_rows = (
            await self.session.execute(
                select(House.id, Address.formatted)
                .join(IncidentAffectedHouse, IncidentAffectedHouse.house_id == House.id)
                .join(Address, Address.id == House.address_id)
                .where(IncidentAffectedHouse.incident_id == incident.id)
                .order_by(Address.formatted)
            )
        ).all()
        report_rows = (
            await self.session.scalars(
                select(Report)
                .join(IncidentReportLink, IncidentReportLink.report_id == Report.id)
                .where(
                    IncidentReportLink.incident_id == incident.id,
                    IncidentReportLink.is_active.is_(True),
                )
                .order_by(Report.received_at)
            )
        ).all()
        assignments = (
            await self.session.scalars(
                select(Assignment)
                .where(Assignment.incident_id == incident.id)
                .order_by(Assignment.created_at)
            )
        ).all()
        disputes = (
            await self.session.scalars(
                select(ResolutionDispute)
                .where(ResolutionDispute.incident_id == incident.id)
                .order_by(ResolutionDispute.created_at)
            )
        ).all()
        history = (
            await self.session.scalars(
                select(IncidentStatusHistory)
                .where(IncidentStatusHistory.incident_id == incident.id)
                .order_by(IncidentStatusHistory.created_at)
            )
        ).all()
        return IncidentCardResult(
            incident_id=incident.id,
            title=incident.title,
            description=incident.description,
            category_id=incident.category_id,
            status=incident.status,
            priority=incident.priority.value,
            version=incident.version,
            first_report_at=incident.first_report_at,
            last_report_at=incident.last_report_at,
            houses=[IncidentHouseSummary(house_id=row.id, address=row.formatted) for row in house_rows],
            reports=[
                IncidentReportSummary(
                    report_id=report.id,
                    text=report.text,
                    status=report.status.value,
                    received_at=report.received_at,
                    problem_continues=report.problem_continues,
                )
                for report in report_rows
            ],
            assignments=[
                IncidentAssignmentSummary(
                    assignment_id=item.id,
                    organization_id=item.organization_id,
                    role=item.role.value,
                    status=item.status.value,
                    due_at=item.due_at,
                )
                for item in assignments
            ],
            disputes=[
                IncidentDisputeSummary(
                    dispute_id=item.id,
                    report_id=item.report_id,
                    status=item.status.value,
                    comment=item.comment,
                    created_at=item.created_at,
                )
                for item in disputes
            ],
            history=[
                IncidentHistorySummary(
                    from_status=item.from_status.value if item.from_status else None,
                    to_status=item.to_status.value,
                    reason=item.reason,
                    created_at=item.created_at,
                )
                for item in history
            ],
        )


class IncidentCoreService(IncidentGroupingMixin, IncidentResolutionMixin, IncidentCardMixin):
    """Transactional application service for report grouping and incident workflow.

    Each concern lives in its own module of this package - grouping, status transitions,
    resident resolution feedback, notifications and the incident card - all sharing one
    session (``IncidentCoreBase``). The caller owns the transaction."""


class IncidentService(SQLAlchemyAsyncRepositoryService[Incident]):
    repository_type = IncidentRepository


class ResolutionDisputeService(SQLAlchemyAsyncRepositoryService[ResolutionDispute]):
    repository_type = ResolutionDisputeRepository
