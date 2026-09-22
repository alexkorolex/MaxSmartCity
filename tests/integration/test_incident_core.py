from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.collaboration.enums import AssignmentRole, AssignmentStatus
from src.domains.collaboration.models import Assignment
from src.domains.collaboration.schemas import (
    CreateAssignmentCommand,
    TransitionAssignmentCommand,
)
from src.domains.collaboration.services import AssignmentService, CollaborationConflictError
from src.domains.geo.models import Address, House
from src.domains.identity.enums import OrganizationType
from src.domains.identity.models import OperatorUser, Organization, Resident
from src.domains.incidents.enums import (
    GroupingOutcome,
    IncidentStatus,
    ResolutionFeedback,
)
from src.domains.incidents.models import (
    Incident,
    IncidentGroupingDecision,
    IncidentReportLink,
)
from src.domains.incidents.schemas import (
    GroupReportCommand,
    ResolutionFeedbackCommand,
    TransitionIncidentCommand,
)
from src.domains.incidents.services import IncidentCoreConflictError, IncidentCoreService
from src.domains.infrastructure.models import OutboxEvent
from src.domains.reports.enums import ReportSourceType, ReportStatus
from src.domains.reports.models import ProblemCategory, Report, ReportStatusHistory
from src.domains.reports.schemas import CreateReportCommand
from src.domains.reports.services import ReportIntakeConflictError, ReportIntakeService


async def _catalog(db_session: AsyncSession) -> tuple[House, ProblemCategory]:
    address = Address(formatted=f"Тестовый адрес {uuid4()}")
    category = ProblemCategory(code=f"WATER_{uuid4().hex}", name="Нет холодной воды")
    db_session.add_all([address, category])
    await db_session.flush()
    house = House(address_id=address.id, external_id=f"test-{uuid4()}")
    db_session.add(house)
    await db_session.flush()
    return house, category


def _report(house: House, category: ProblemCategory, text: str) -> Report:
    return Report(
        source_type=ReportSourceType.MAX,
        source_external_id=uuid4().hex,
        text=text,
        house_id=house.id,
        category_id=category.id,
    )


@pytest.mark.anyio
async def test_grouping_creates_then_attaches_and_is_idempotent(db_session: AsyncSession) -> None:
    house, category = await _catalog(db_session)
    first = _report(house, category, "Во всём доме нет холодной воды")
    db_session.add(first)
    await db_session.flush()
    service = IncidentCoreService(db_session)

    created = await service.group_report(first.id, GroupReportCommand())
    assert created.outcome is GroupingOutcome.CREATED
    assert created.incident_id is not None
    assert first.status is ReportStatus.LINKED

    second = _report(house, category, "Во всём доме нет холодной воды")
    db_session.add(second)
    await db_session.flush()
    attached = await service.group_report(second.id, GroupReportCommand())
    assert attached.outcome is GroupingOutcome.ATTACHED
    assert attached.incident_id == created.incident_id

    repeated = await service.group_report(second.id, GroupReportCommand())
    assert repeated.incident_id == attached.incident_id
    assert repeated.reason_codes == ["ALREADY_LINKED"]
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(IncidentReportLink)
            .where(IncidentReportLink.report_id == second.id)
        )
        == 1
    )
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(IncidentGroupingDecision)
            .where(IncidentGroupingDecision.report_id.in_([first.id, second.id]))
        )
        == 2
    )
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(ReportStatusHistory)
            .where(ReportStatusHistory.report_id == first.id)
        )
        == 2
    )


@pytest.mark.anyio
async def test_incident_transition_checks_state_and_version(db_session: AsyncSession) -> None:
    house, category = await _catalog(db_session)
    report = _report(house, category, "Не работает лифт")
    db_session.add(report)
    await db_session.flush()
    service = IncidentCoreService(db_session)
    grouped = await service.group_report(report.id)
    incident = await db_session.get(Incident, grouped.incident_id)
    assert incident is not None

    result = await service.transition_incident(
        incident.id,
        TransitionIncidentCommand(
            target_status=IncidentStatus.TRIAGE,
            expected_version=incident.version,
            reason="Оператор начал проверку",
        ),
        changed_by_id=uuid4(),
    )
    assert result.status is IncidentStatus.TRIAGE

    with pytest.raises(IncidentCoreConflictError, match="Expected version"):
        await service.transition_incident(
            incident.id,
            TransitionIncidentCommand(
                target_status=IncidentStatus.CONFIRMED,
                expected_version=1,
            ),
            changed_by_id=uuid4(),
        )


@pytest.mark.anyio
async def test_resident_intake_assignment_card_and_resolution_flow(
    db_session: AsyncSession,
) -> None:
    house, category = await _catalog(db_session)
    resident = Resident(max_user_id=10_000 + int(uuid4().hex[:6], 16))
    operator = OperatorUser(login=f"operator-{uuid4()}", display_name="Operator")
    organization = Organization(
        code=f"org-{uuid4().hex}",
        name="Test management company",
        type=OrganizationType.ADMINISTRATION,
    )
    db_session.add_all([resident, operator, organization])
    await db_session.flush()

    command = CreateReportCommand(
        source_external_id=f"max-{uuid4()}",
        house_id=house.id,
        category_code=category.code,
        text="No cold water in the entire building",
    )
    intake = ReportIntakeService(db_session)
    created = await intake.create(command, resident_id=resident.id)
    assert created.grouping.outcome is GroupingOutcome.CREATED
    assert created.grouping.incident_id is not None

    repeated = await intake.create(command, resident_id=resident.id)
    assert repeated.report_id == created.report_id
    assert repeated.grouping.incident_id == created.grouping.incident_id
    assert repeated.grouping.reason_codes == ["ALREADY_LINKED"]

    with pytest.raises(ReportIntakeConflictError, match="different payload"):
        await intake.create(
            CreateReportCommand(
                source_external_id=command.source_external_id,
                house_id=house.id,
                category_code=category.code,
                text="A different immutable payload",
            ),
            resident_id=resident.id,
        )

    incident_service = IncidentCoreService(db_session)
    incident = await db_session.get(Incident, created.grouping.incident_id)
    assert incident is not None
    for target in (IncidentStatus.TRIAGE, IncidentStatus.CONFIRMED):
        await incident_service.transition_incident(
            incident.id,
            TransitionIncidentCommand(target_status=target, expected_version=incident.version),
            changed_by_id=operator.id,
        )

    assignment = await AssignmentService(session=db_session).create_for_incident(
        CreateAssignmentCommand(
            incident_id=incident.id,
            organization_id=organization.id,
            role=AssignmentRole.EXECUTOR,
        ),
        changed_by=operator.id,
    )
    assert assignment.status.value == "PROPOSED"
    assert incident.status is IncidentStatus.ASSIGNED
    with pytest.raises(CollaborationConflictError, match="already exists"):
        await AssignmentService(session=db_session).create_for_incident(
            CreateAssignmentCommand(
                incident_id=incident.id,
                organization_id=organization.id,
                role=AssignmentRole.EXECUTOR,
            ),
            changed_by=operator.id,
        )

    card = await incident_service.get_card(incident.id)
    assert [item.report_id for item in card.reports] == [created.report_id]
    assert [item.assignment_id for item in card.assignments] == [assignment.assignment_id]
    assert [item.house_id for item in card.houses] == [house.id]

    with pytest.raises(IncidentCoreConflictError, match="required assignments"):
        await incident_service.transition_incident(
            incident.id,
            TransitionIncidentCommand(
                target_status=IncidentStatus.RESOLVED,
                expected_version=incident.version,
            ),
            changed_by_id=operator.id,
        )

    assignment_model = await db_session.get(Assignment, assignment.assignment_id)
    assert assignment_model is not None
    assignment_service = AssignmentService(session=db_session)
    for target in (
        AssignmentStatus.ACCEPTED,
        AssignmentStatus.IN_PROGRESS,
        AssignmentStatus.COMPLETED,
    ):
        await assignment_service.transition(
            assignment_model.id,
            TransitionAssignmentCommand(
                target_status=target,
                expected_version=assignment_model.version,
            ),
            changed_by=operator.id,
        )

    await incident_service.transition_incident(
        incident.id,
        TransitionIncidentCommand(
            target_status=IncidentStatus.RESOLVED,
            expected_version=incident.version,
        ),
        changed_by_id=operator.id,
    )
    feedback = await incident_service.record_resolution_feedback(
        incident.id,
        ResolutionFeedbackCommand(
            report_id=created.report_id,
            feedback=ResolutionFeedback.CONFIRMED,
        ),
        resident_id=resident.id,
    )
    assert feedback.incident_status is IncidentStatus.CLOSED
    assert incident.closed_at is not None

    events = (
        await db_session.scalars(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id.in_([created.report_id, incident.id, assignment.assignment_id])
            )
        )
    ).all()
    assert {
        "REPORT_RECEIVED",
        "REPORT_GROUPING_DECIDED",
        "INCIDENT_STATUS_CHANGED",
        "ASSIGNMENT_CREATED",
        "RESOLUTION_FEEDBACK_RECORDED",
    }.issubset({event.event_type for event in events})


@pytest.mark.anyio
async def test_resolution_dispute_escalates_only_after_three_residents(
    db_session: AsyncSession,
) -> None:
    house, category = await _catalog(db_session)
    operator = OperatorUser(login=f"operator-{uuid4()}", display_name="Operator")
    residents = [Resident(max_user_id=20_000 + index + int(uuid4().hex[:5], 16)) for index in range(3)]
    db_session.add_all([operator, *residents])
    await db_session.flush()

    report_ids = []
    incident_id = None
    intake = ReportIntakeService(db_session)
    for resident in residents:
        result = await intake.create(
            CreateReportCommand(
                source_external_id=f"dispute-{uuid4()}",
                house_id=house.id,
                category_code=category.code,
                text="The same water outage affects the entire building",
            ),
            resident_id=resident.id,
        )
        report_ids.append(result.report_id)
        incident_id = incident_id or result.grouping.incident_id
        assert result.grouping.incident_id == incident_id

    assert incident_id is not None
    incident = await db_session.get(Incident, incident_id)
    assert incident is not None
    service = IncidentCoreService(db_session)
    for target in (
        IncidentStatus.TRIAGE,
        IncidentStatus.CONFIRMED,
        IncidentStatus.RESOLVED,
    ):
        await service.transition_incident(
            incident.id,
            TransitionIncidentCommand(target_status=target, expected_version=incident.version),
            changed_by_id=operator.id,
        )

    for index, resident in enumerate(residents):
        feedback = await service.record_resolution_feedback(
            incident.id,
            ResolutionFeedbackCommand(
                report_id=report_ids[index],
                feedback=ResolutionFeedback.PROBLEM_CONTINUES,
                comment="The water is still off",
            ),
            resident_id=resident.id,
        )
        expected = IncidentStatus.RESOLUTION_DISPUTED if index == 2 else IncidentStatus.RESOLVED
        assert feedback.incident_status is expected

    card = await service.get_card(incident.id)
    assert len(card.disputes) == 3
