"""Shared foundation of the incident core service: its errors, the status sets and time
windows the workflow is built on, and the session-level helpers every part uses."""

from __future__ import annotations

import hashlib
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.enums import ActorType
from src.domains.collaboration.enums import AssignmentStatus
from src.domains.incidents.enums import (
    IncidentStatus,
)
from src.domains.incidents.grouping import (
    GroupingConfig,
)
from src.domains.incidents.models import (
    Incident,
    IncidentReportLink,
)
from src.domains.infrastructure.models import OutboxEvent
from src.domains.reports.enums import ReportStatus
from src.domains.reports.models import Report, ReportStatusHistory
from src.domains.reports.state_machine import ensure_report_transition


class IncidentCoreError(RuntimeError):
    pass


class IncidentCoreNotFoundError(IncidentCoreError):
    pass


class IncidentCoreConflictError(IncidentCoreError):
    pass


ACTIVE_INCIDENT_STATUSES = frozenset(
    {
        IncidentStatus.NEW,
        IncidentStatus.TRIAGE,
        IncidentStatus.CONFIRMED,
        IncidentStatus.ASSIGNED,
        IncidentStatus.IN_PROGRESS,
        IncidentStatus.RESOLVED,
        IncidentStatus.AWAITING_CONFIRMATION,
        IncidentStatus.RESOLUTION_DISPUTED,
        IncidentStatus.REOPENED,
    }
)

STAFF_COMPLETABLE_STATUSES = frozenset(
    {
        IncidentStatus.NEW,
        IncidentStatus.TRIAGE,
        IncidentStatus.CONFIRMED,
        IncidentStatus.ASSIGNED,
        IncidentStatus.IN_PROGRESS,
        IncidentStatus.REOPENED,
        IncidentStatus.RESOLUTION_DISPUTED,
    }
)

OPEN_ASSIGNMENT_STATUSES = frozenset(
    {
        AssignmentStatus.PROPOSED,
        AssignmentStatus.ACCEPTED,
        AssignmentStatus.IN_PROGRESS,
        AssignmentStatus.BLOCKED,
        AssignmentStatus.MONITORING,
    }
)

FINAL_REPORT_STATUSES = frozenset({ReportStatus.CLOSED, ReportStatus.REJECTED, ReportStatus.WITHDRAWN})

DISPUTE_ESCALATION_THRESHOLD = 3

DISPUTE_ESCALATION_WINDOW = timedelta(minutes=30)

RESOLUTION_CONFIRMATION_WINDOW = timedelta(days=3)

AWAITING_RESIDENT_STATUSES = frozenset({IncidentStatus.RESOLVED, IncidentStatus.AWAITING_CONFIRMATION})


class IncidentCoreBase:
    """Transactional application service for report grouping and incident workflow -
    the session, report status history, outbox events and the grouping lock every part
    of ``IncidentCoreService`` builds on."""

    def __init__(self, session: AsyncSession, config: GroupingConfig | None = None) -> None:
        self.session = session
        self.config = config or GroupingConfig()

    def _transition_report(
        self,
        report: Report,
        target: ReportStatus,
        reason: str,
        *,
        actor_type: ActorType = ActorType.SYSTEM,
        actor_id: UUID | None = None,
    ) -> None:
        previous = report.status
        ensure_report_transition(previous, target)
        report.status = target
        self.session.add(
            ReportStatusHistory(
                report_id=report.id,
                from_status=previous,
                to_status=target,
                changed_by_type=actor_type,
                changed_by_id=actor_id,
                reason=reason,
            )
        )

    async def _linked_reports(self, incident: Incident) -> list[Report]:
        return list(
            (
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
        )

    def _emit(
        self,
        aggregate_id: UUID,
        event_type: str,
        payload: dict[str, object],
        *,
        aggregate_type: str = "INCIDENT",
    ) -> None:
        self.session.add(
            OutboxEvent(
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                event_type=event_type,
                payload=payload,
            )
        )

    async def _lock_group(self, house_id: UUID, category_id: UUID) -> None:
        digest = hashlib.blake2b(f"{house_id}:{category_id}".encode(), digest_size=8).digest()
        lock_key = int.from_bytes(digest, byteorder="big", signed=True)
        await self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
