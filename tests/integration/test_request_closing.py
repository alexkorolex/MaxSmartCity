"""Closing requests: a staff member reports the work as done, and a resident closes their
own report because the problem went away."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.collaboration.enums import AssignmentRole, AssignmentStatus
from src.domains.collaboration.models import Assignment
from src.domains.collaboration.schemas import CreateAssignmentCommand
from src.domains.collaboration.services import AssignmentService
from src.domains.identity.models import OperatorUser, Resident
from src.domains.incidents.enums import GroupingMode, IncidentStatus
from src.domains.incidents.schemas import (
    CloseReportCommand,
    CompleteIncidentCommand,
    GroupReportCommand,
    TransitionIncidentCommand,
)
from src.domains.incidents.services import IncidentCoreConflictError, IncidentCoreService
from src.domains.notifications.enums import NotificationType
from src.domains.reports.enums import ReportStatus
from src.domains.reports.models import Report
from tests.integration.test_housing_organizations import (
    _approved_organization,
    _organization_notifications,
    _resident_notifications,
    _resident_request,
)


async def _operator(db_session: AsyncSession) -> OperatorUser:
    operator = OperatorUser(login=f"worker-{uuid4().hex}", display_name="Мастер")
    db_session.add(operator)
    await db_session.flush()
    return operator


@pytest.mark.anyio
async def test_staff_completes_a_new_request_and_residents_are_asked_to_confirm(
    db_session: AsyncSession,
) -> None:
    manager, resident, report, incident = await _resident_request(db_session)
    operator = await _operator(db_session)
    assert incident.status is IncidentStatus.NEW

    result = await IncidentCoreService(db_session).complete_by_staff(
        incident.id,
        CompleteIncidentCommand(comment="Кровлю залатали"),
        changed_by=operator.id,
        organization_id=manager.id,
    )
    assert result.status is IncidentStatus.RESOLVED
    assert incident.resolved_at is not None
    assert await _resident_notifications(db_session, resident) == [NotificationType.RESOLUTION_REQUESTED]
    assert report.status is ReportStatus.LINKED

    with pytest.raises(IncidentCoreConflictError, match="cannot be completed"):
        await IncidentCoreService(db_session).complete_by_staff(
            incident.id, CompleteIncidentCommand(), changed_by=operator.id, organization_id=manager.id
        )


@pytest.mark.anyio
async def test_completing_closes_own_assignment_but_waits_for_other_required_ones(
    db_session: AsyncSession,
) -> None:
    manager, _resident, _report, incident = await _resident_request(db_session)
    utility = await _approved_organization(db_session)
    operator = await _operator(db_session)
    service = IncidentCoreService(db_session)
    for target in (IncidentStatus.TRIAGE, IncidentStatus.CONFIRMED):
        await service.transition_incident(
            incident.id,
            TransitionIncidentCommand(target_status=target, expected_version=incident.version),
            changed_by_id=operator.id,
        )
    assignments = AssignmentService(session=db_session)
    for organization in (manager, utility):
        await assignments.create_for_incident(
            CreateAssignmentCommand(
                incident_id=incident.id, organization_id=organization.id, role=AssignmentRole.EXECUTOR
            ),
            changed_by=operator.id,
        )

    with pytest.raises(IncidentCoreConflictError, match="УК Дом"):
        await service.complete_by_staff(
            incident.id, CompleteIncidentCommand(), changed_by=operator.id, organization_id=manager.id
        )
    own = await db_session.scalar(
        select(Assignment).where(
            Assignment.incident_id == incident.id, Assignment.organization_id == manager.id
        )
    )
    assert own is not None
    assert own.status is AssignmentStatus.COMPLETED
    assert own.completed_at is not None

    result = await service.complete_by_staff(
        incident.id, CompleteIncidentCommand(), changed_by=operator.id, organization_id=utility.id
    )
    assert result.status is IncidentStatus.RESOLVED


@pytest.mark.anyio
async def test_request_without_residents_is_closed_right_away(db_session: AsyncSession) -> None:
    manager, _resident, report, incident = await _resident_request(db_session)
    report.resident_id = None
    await db_session.flush()
    operator = await _operator(db_session)

    result = await IncidentCoreService(db_session).complete_by_staff(
        incident.id, CompleteIncidentCommand(), changed_by=operator.id, organization_id=manager.id
    )
    assert result.status is IncidentStatus.CLOSED


@pytest.mark.anyio
async def test_sole_reporter_closing_a_fresh_request_cancels_it(db_session: AsyncSession) -> None:
    _manager, resident, report, incident = await _resident_request(db_session)

    result = await IncidentCoreService(db_session).close_by_resident(
        report.id, CloseReportCommand(comment="Сами починили"), resident_id=resident.id
    )
    assert result.report_status == "CLOSED"
    assert incident.status is IncidentStatus.CANCELLED
    assert report.problem_continues is False

    with pytest.raises(IncidentCoreConflictError, match="already closed"):
        await IncidentCoreService(db_session).close_by_resident(
            report.id, CloseReportCommand(), resident_id=resident.id
        )


@pytest.mark.anyio
async def test_one_of_several_reporters_closing_tells_the_organization(db_session: AsyncSession) -> None:
    manager, resident, report, incident = await _resident_request(db_session)
    neighbour = Resident(max_user_id=40_000 + int(uuid4().hex[:6], 16))
    db_session.add(neighbour)
    await db_session.flush()
    neighbour_report = Report(
        source_type=report.source_type,
        source_external_id=uuid4().hex,
        text="И у нас течёт",
        house_id=report.house_id,
        category_id=report.category_id,
        resident_id=neighbour.id,
    )
    db_session.add(neighbour_report)
    await db_session.flush()
    grouped = await IncidentCoreService(db_session).group_report(
        neighbour_report.id,
        GroupReportCommand(mode=GroupingMode.CONFIRM_INCIDENT, confirmed_incident_id=incident.id),
    )
    assert grouped.incident_id == incident.id

    await IncidentCoreService(db_session).close_by_resident(
        report.id, CloseReportCommand(), resident_id=resident.id
    )
    assert report.status is ReportStatus.CLOSED
    assert incident.status is IncidentStatus.NEW
    notifications = await _organization_notifications(db_session, manager.id)
    events = [event.payload["event_type"] for event in notifications]
    assert "RESIDENT_CLOSED_REPORT" in events


@pytest.mark.anyio
async def test_closing_while_awaiting_confirmation_confirms_the_fix(db_session: AsyncSession) -> None:
    manager, resident, report, incident = await _resident_request(db_session)
    operator = await _operator(db_session)
    await IncidentCoreService(db_session).complete_by_staff(
        incident.id, CompleteIncidentCommand(), changed_by=operator.id, organization_id=manager.id
    )

    result = await IncidentCoreService(db_session).close_by_resident(
        report.id, CloseReportCommand(), resident_id=resident.id
    )
    assert result.incident_status is IncidentStatus.CLOSED
    assert report.status is ReportStatus.CLOSED
