"""Who takes part in a report's chat: the resident who filed it, and the organizations
working on it - its house's УК/ТСЖ and the ones assigned to its incident."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.collaboration.enums import AssignmentStatus
from src.domains.collaboration.models import Assignment
from src.domains.geo.models import HouseManagement
from src.domains.identity.models import Organization
from src.domains.incidents.models import IncidentReportLink
from src.domains.incidents.scope import organization_report_ids
from src.domains.reports.models import Report


class ChatNotFoundError(RuntimeError):
    pass


class ChatConflictError(RuntimeError):
    pass


class ChatForbiddenError(RuntimeError):
    pass


async def report_organizations(session: AsyncSession, report: Report) -> list[tuple[UUID, str]]:
    """``(id, name)`` of every organization working on ``report``, house manager first."""
    found: dict[UUID, str] = {}
    if report.house_id is not None:
        manager = (
            await session.execute(
                select(Organization.id, Organization.name)
                .join(HouseManagement, HouseManagement.organization_id == Organization.id)
                .where(HouseManagement.house_id == report.house_id, HouseManagement.is_active.is_(True))
            )
        ).first()
        if manager is not None:
            found[manager.id] = manager.name
    assigned = await session.execute(
        select(Organization.id, Organization.name)
        .join(Assignment, Assignment.organization_id == Organization.id)
        .join(IncidentReportLink, IncidentReportLink.incident_id == Assignment.incident_id)
        .where(
            IncidentReportLink.report_id == report.id,
            IncidentReportLink.is_active.is_(True),
            Assignment.status.not_in({AssignmentStatus.REJECTED, AssignmentStatus.CANCELLED}),
        )
        .order_by(Assignment.created_at)
    )
    for row in assigned:
        found.setdefault(row.id, row.name)
    return list(found.items())


async def resident_report(session: AsyncSession, report_id: UUID, resident_id: UUID) -> Report:
    report = await session.scalar(
        select(Report).where(Report.id == report_id, Report.resident_id == resident_id)
    )
    if report is None:
        raise ChatNotFoundError(f"Report {report_id} was not found")
    return report


async def staff_report(session: AsyncSession, report_id: UUID, organization_id: UUID | None) -> Report:
    """The report, if the staff member may chat on it: an admin (``organization_id=None``)
    always, others only within their organization's scope. 404 otherwise - a report's
    existence is never revealed to someone who can't see it."""
    statement = select(Report).where(Report.id == report_id, Report.resident_id.is_not(None))
    if organization_id is not None:
        statement = statement.where(Report.id.in_(organization_report_ids(organization_id)))
    report = await session.scalar(statement)
    if report is None:
        raise ChatNotFoundError(f"Report {report_id} was not found")
    return report
