from __future__ import annotations

import hashlib
from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy import Select, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.enums import ActorType
from src.common.models import utc_now
from src.domains.incidents.enums import (
    AffectedHouseSource,
    GroupingMode,
    GroupingOutcome,
    IncidentStatus,
    LinkSource,
)
from src.domains.incidents.grouping import (
    POLICY_VERSION,
    SCORER_VERSION,
    GroupingConfig,
    GroupingProposal,
    IncidentCandidate,
    ProposedAction,
    propose_grouping,
)
from src.domains.incidents.models import (
    Incident,
    IncidentAffectedHouse,
    IncidentGroupingDecision,
    IncidentReportLink,
    IncidentStatusHistory,
)
from src.domains.incidents.repositories import IncidentRepository
from src.domains.incidents.schemas import (
    GroupReportCommand,
    GroupReportResult,
    TransitionIncidentCommand,
    TransitionIncidentResult,
)
from src.domains.incidents.state_machine import ensure_incident_transition
from src.domains.reports.enums import ReportStatus
from src.domains.reports.models import ProblemCategory, Report, ReportStatusHistory
from src.domains.reports.state_machine import ensure_report_transition

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


class IncidentCoreError(RuntimeError):
    pass


class IncidentCoreNotFoundError(IncidentCoreError):
    pass


class IncidentCoreConflictError(IncidentCoreError):
    pass


class IncidentService(SQLAlchemyAsyncRepositoryService[Incident]):
    repository_type = IncidentRepository


class IncidentCoreService:
    """Transactional application service for report grouping and incident workflow."""

    def __init__(self, session: AsyncSession, config: GroupingConfig | None = None) -> None:
        self.session = session
        self.config = config or GroupingConfig()

    async def group_report(
        self, report_id: UUID, command: GroupReportCommand | None = None
    ) -> GroupReportResult:
        command = command or GroupReportCommand()
        report = await self.session.scalar(select(Report).where(Report.id == report_id).with_for_update())
        if report is None:
            raise IncidentCoreNotFoundError(f"Report {report_id} was not found")

        existing = await self.session.scalar(
            select(IncidentReportLink).where(
                IncidentReportLink.report_id == report.id,
                IncidentReportLink.is_active.is_(True),
            )
        )
        if existing is not None:
            return GroupReportResult(
                report_id=report.id,
                outcome=GroupingOutcome.ATTACHED,
                incident_id=existing.incident_id,
                score=float(existing.score) if existing.score is not None else None,
                reason_codes=["ALREADY_LINKED"],
                policy_version=POLICY_VERSION,
                scorer_version=SCORER_VERSION,
            )

        if report.status in {ReportStatus.REJECTED, ReportStatus.WITHDRAWN, ReportStatus.LINKED}:
            raise IncidentCoreConflictError(f"Report in status {report.status.value} cannot be grouped")
        if report.house_id is None or report.category_id is None:
            return await self._needs_clarification(report, command, ["HOUSE_OR_CATEGORY_MISSING"])

        await self._lock_group(report.house_id, report.category_id)
        candidates = await self._load_candidates(report)
        event_time = report.occurred_at or report.received_at or report.created_at
        profiles = await self._build_profiles(candidates)
        proposal = propose_grouping(report.text or "", profiles, occurred_at=event_time, config=self.config)

        if command.mode is GroupingMode.CONFIRM_INCIDENT:
            if command.confirmed_incident_id is None:
                raise IncidentCoreConflictError("confirmed_incident_id is required in CONFIRM_INCIDENT mode")
            allowed = {candidate.id for candidate in candidates}
            if command.confirmed_incident_id not in allowed:
                raise IncidentCoreConflictError(
                    "Confirmed incident is not an active candidate for this house and category"
                )
            selected = command.confirmed_incident_id
            score = next((item.score for item in proposal.ranked if item.incident_id == selected), None)
            return await self._attach(
                report,
                selected,
                score,
                command,
                ["USER_CONFIRMED", "SAME_HOUSE", "SAME_CATEGORY"],
                proposal,
                LinkSource.MANUAL,
            )

        if command.mode is GroupingMode.FORCE_NEW:
            return await self._create(report, command, ["USER_REJECTED_CANDIDATES"], proposal)
        if proposal.action is ProposedAction.ATTACH and proposal.selected_incident_id is not None:
            return await self._attach(
                report,
                proposal.selected_incident_id,
                proposal.ranked[0].score,
                command,
                list(proposal.reason_codes),
                proposal,
                LinkSource.RULE,
            )
        if proposal.action is ProposedAction.CLARIFY:
            return await self._needs_clarification(report, command, list(proposal.reason_codes), proposal)
        return await self._create(report, command, list(proposal.reason_codes), proposal)

    async def transition_incident(
        self,
        incident_id: UUID,
        command: TransitionIncidentCommand,
        *,
        changed_by_id: UUID,
    ) -> TransitionIncidentResult:
        incident = await self.session.scalar(
            select(Incident).where(Incident.id == incident_id).with_for_update()
        )
        if incident is None:
            raise IncidentCoreNotFoundError(f"Incident {incident_id} was not found")
        if incident.version != command.expected_version:
            raise IncidentCoreConflictError(
                f"Expected version {command.expected_version}, actual version {incident.version}"
            )
        ensure_incident_transition(incident.status, command.target_status)
        previous = incident.status
        incident.status = command.target_status
        now = utc_now()
        if command.target_status is IncidentStatus.RESOLVED:
            incident.resolved_at = now
        elif command.target_status is IncidentStatus.CLOSED:
            incident.closed_at = now
        elif command.target_status is IncidentStatus.REOPENED:
            incident.closed_at = None
            incident.resolved_at = None
        self.session.add(
            IncidentStatusHistory(
                incident_id=incident.id,
                from_status=previous,
                to_status=command.target_status,
                changed_by_type=ActorType.OPERATOR,
                changed_by_id=changed_by_id,
                reason=command.reason,
            )
        )
        await self.session.flush()
        return TransitionIncidentResult(
            incident_id=incident.id, status=incident.status, version=incident.version
        )

    async def _load_candidates(self, report: Report) -> list[Incident]:
        event_time = report.occurred_at or report.received_at or report.created_at
        cutoff = event_time - self.config.candidate_window
        activity = func.coalesce(Incident.last_report_at, Incident.first_report_at, Incident.created_at)
        statement: Select[tuple[Incident]] = (
            select(Incident)
            .join(IncidentAffectedHouse, IncidentAffectedHouse.incident_id == Incident.id)
            .where(
                IncidentAffectedHouse.house_id == report.house_id,
                Incident.category_id == report.category_id,
                Incident.status.in_(ACTIVE_INCIDENT_STATUSES),
                activity >= cutoff,
            )
            .order_by(activity.desc(), Incident.id)
            .with_for_update(of=Incident)
        )
        return list((await self.session.scalars(statement)).all())

    async def _build_profiles(self, candidates: list[Incident]) -> tuple[IncidentCandidate, ...]:
        if not candidates:
            return ()
        candidate_ids = [candidate.id for candidate in candidates]
        rows = (
            await self.session.execute(
                select(IncidentReportLink.incident_id, Report.text)
                .join(Report, Report.id == IncidentReportLink.report_id)
                .where(
                    IncidentReportLink.incident_id.in_(candidate_ids),
                    IncidentReportLink.is_active.is_(True),
                    Report.text.is_not(None),
                )
                .order_by(Report.received_at.desc())
            )
        ).all()
        texts: dict[UUID, list[str]] = defaultdict(list)
        for incident_id, value in rows:
            if value and len(texts[incident_id]) < 20:
                texts[incident_id].append(value)
        return tuple(
            IncidentCandidate(
                incident_id=candidate.id,
                text=" ".join(
                    part for part in (candidate.title, candidate.description, *texts[candidate.id]) if part
                ),
                last_activity_at=(
                    candidate.last_report_at or candidate.first_report_at or candidate.created_at
                ),
            )
            for candidate in candidates
        )

    async def _attach(
        self,
        report: Report,
        incident_id: UUID,
        score: float | None,
        command: GroupReportCommand,
        reasons: list[str],
        proposal: GroupingProposal,
        source: LinkSource,
    ) -> GroupReportResult:
        incident = await self.session.get(Incident, incident_id)
        if incident is None:
            raise IncidentCoreNotFoundError(f"Incident {incident_id} was not found")
        event_time = report.occurred_at or report.received_at or report.created_at
        if incident.last_report_at is None or event_time > incident.last_report_at:
            incident.last_report_at = event_time
        await self._mark_linked(report)
        self.session.add(
            IncidentReportLink(
                incident_id=incident.id,
                report_id=report.id,
                link_source=source,
                score=_decimal(score),
                reason_codes=reasons,
            )
        )
        return await self._record_result(
            report, GroupingOutcome.ATTACHED, incident.id, score, reasons, command, proposal
        )

    async def _create(
        self,
        report: Report,
        command: GroupReportCommand,
        reasons: list[str],
        proposal: GroupingProposal,
    ) -> GroupReportResult:
        category_name = await self.session.scalar(
            select(ProblemCategory.name).where(ProblemCategory.id == report.category_id)
        )
        if category_name is None:
            raise IncidentCoreConflictError("Report category does not exist")
        event_time = report.occurred_at or report.received_at or report.created_at
        incident = Incident(
            title=category_name,
            description=report.text,
            category_id=report.category_id,
            priority=report.urgency,
            first_report_at=event_time,
            last_report_at=event_time,
        )
        self.session.add(incident)
        await self.session.flush()
        self.session.add_all(
            [
                IncidentAffectedHouse(
                    incident_id=incident.id,
                    house_id=report.house_id,
                    source=AffectedHouseSource.REPORT,
                ),
                IncidentStatusHistory(
                    incident_id=incident.id,
                    from_status=None,
                    to_status=IncidentStatus.NEW,
                    changed_by_type=ActorType.SYSTEM,
                    reason="Created from resident report",
                    request_id=command.request_id,
                ),
                IncidentReportLink(
                    incident_id=incident.id,
                    report_id=report.id,
                    link_source=LinkSource.RULE,
                    reason_codes=reasons,
                ),
            ]
        )
        await self._mark_linked(report)
        return await self._record_result(
            report, GroupingOutcome.CREATED, incident.id, None, reasons, command, proposal
        )

    async def _needs_clarification(
        self,
        report: Report,
        command: GroupReportCommand,
        reasons: list[str],
        proposal: GroupingProposal | None = None,
    ) -> GroupReportResult:
        if report.status is not ReportStatus.NEEDS_CLARIFICATION:
            self._transition_report(report, ReportStatus.NEEDS_CLARIFICATION, ",".join(reasons))
        return await self._record_result(
            report,
            GroupingOutcome.NEEDS_CLARIFICATION,
            None,
            _best_score(proposal),
            reasons,
            command,
            proposal,
        )

    async def _record_result(
        self,
        report: Report,
        outcome: GroupingOutcome,
        incident_id: UUID | None,
        score: float | None,
        reasons: list[str],
        command: GroupReportCommand,
        proposal: GroupingProposal | None,
    ) -> GroupReportResult:
        ranked = proposal.ranked if proposal is not None else ()
        candidate_ids = [item.incident_id for item in ranked]
        runner_up_score = ranked[1].score if len(ranked) > 1 else None
        self.session.add(
            IncidentGroupingDecision(
                report_id=report.id,
                outcome=outcome,
                selected_incident_id=incident_id,
                score=_decimal(score),
                runner_up_score=_decimal(runner_up_score),
                candidate_incident_ids=[str(item) for item in candidate_ids],
                reason_codes=reasons,
                policy_version=POLICY_VERSION,
                scorer_version=SCORER_VERSION,
                request_id=command.request_id,
            )
        )
        await self.session.flush()
        return GroupReportResult(
            report_id=report.id,
            outcome=outcome,
            incident_id=incident_id,
            score=score,
            candidate_incident_ids=candidate_ids,
            reason_codes=reasons,
            policy_version=POLICY_VERSION,
            scorer_version=SCORER_VERSION,
        )

    async def _mark_linked(self, report: Report) -> None:
        if report.status in {ReportStatus.RECEIVED, ReportStatus.NEEDS_CLARIFICATION}:
            self._transition_report(report, ReportStatus.PROCESSING, "Incident grouping started")
        if report.status in {ReportStatus.PROCESSING, ReportStatus.READY_FOR_TRIAGE}:
            self._transition_report(report, ReportStatus.LINKED, "Linked to incident")
        elif report.status is not ReportStatus.LINKED:
            raise IncidentCoreConflictError(f"Report in status {report.status.value} cannot be linked")

    def _transition_report(self, report: Report, target: ReportStatus, reason: str) -> None:
        previous = report.status
        ensure_report_transition(previous, target)
        report.status = target
        self.session.add(
            ReportStatusHistory(
                report_id=report.id,
                from_status=previous,
                to_status=target,
                changed_by_type=ActorType.SYSTEM,
                reason=reason,
            )
        )

    async def _lock_group(self, house_id: UUID, category_id: UUID) -> None:
        digest = hashlib.blake2b(f"{house_id}:{category_id}".encode(), digest_size=8).digest()
        lock_key = int.from_bytes(digest, byteorder="big", signed=True)
        await self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})


def _decimal(value: float | None) -> Decimal | None:
    return Decimal(f"{value:.6f}") if value is not None else None


def _best_score(proposal: GroupingProposal | None) -> float | None:
    ranked = proposal.ranked if proposal is not None else ()
    return ranked[0].score if ranked else None
