from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.geo.models import Address, House
from src.domains.incidents.enums import GroupingOutcome, IncidentStatus
from src.domains.incidents.models import (
    Incident,
    IncidentGroupingDecision,
    IncidentReportLink,
)
from src.domains.incidents.schemas import GroupReportCommand, TransitionIncidentCommand
from src.domains.incidents.services import IncidentCoreConflictError, IncidentCoreService
from src.domains.reports.enums import ReportSourceType, ReportStatus
from src.domains.reports.models import ProblemCategory, Report, ReportStatusHistory


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
