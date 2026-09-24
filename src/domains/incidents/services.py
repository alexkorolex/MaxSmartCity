from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy import Select, exists, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.enums import ActorType
from src.common.models import utc_now
from src.domains.collaboration.enums import AssignmentStatus
from src.domains.collaboration.models import Assignment
from src.domains.geo.models import Address, House, HouseManagement
from src.domains.geo.services import active_house_manager_id
from src.domains.incidents.enums import (
    AffectedHouseSource,
    GroupingMode,
    GroupingOutcome,
    IncidentStatus,
    LinkSource,
    ResolutionDisputeStatus,
    ResolutionFeedback,
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
    ResolutionDispute,
)
from src.domains.incidents.repositories import IncidentRepository, ResolutionDisputeRepository
from src.domains.incidents.schemas import (
    GroupReportCommand,
    GroupReportResult,
    IncidentAssignmentSummary,
    IncidentCardResult,
    IncidentDisputeSummary,
    IncidentHistorySummary,
    IncidentHouseSummary,
    IncidentReportSummary,
    ResolutionFeedbackCommand,
    ResolutionFeedbackResult,
    TransitionIncidentCommand,
    TransitionIncidentResult,
)
from src.domains.incidents.state_machine import ensure_incident_transition
from src.domains.infrastructure.models import OutboxEvent
from src.domains.notifications.dispatcher import OrganizationMessage, enqueue_organization_notification
from src.domains.notifications.enums import NotificationType
from src.domains.notifications.models import Notification
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

DISPUTE_ESCALATION_THRESHOLD = 3
DISPUTE_ESCALATION_WINDOW = timedelta(minutes=30)

RESOLUTION_CONFIRMATION_WINDOW = timedelta(days=3)
"""How long residents have to confirm or dispute a resolution before the incident (and
their requests with it) is closed automatically."""
_AWAITING_RESIDENT_STATUSES = frozenset({IncidentStatus.RESOLVED, IncidentStatus.AWAITING_CONFIRMATION})


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
        if command.target_status is IncidentStatus.RESOLVED:
            incomplete_assignment = await self.session.scalar(
                select(Assignment.id).where(
                    Assignment.incident_id == incident.id,
                    Assignment.required.is_(True),
                    Assignment.status != AssignmentStatus.COMPLETED,
                )
            )
            if incomplete_assignment is not None:
                raise IncidentCoreConflictError(
                    "All required assignments must be completed before resolving the incident"
                )
        await self._apply_transition(
            incident,
            command.target_status,
            actor_type=ActorType.OPERATOR,
            actor_id=changed_by_id,
            reason=command.reason,
        )
        await self.session.flush()
        return TransitionIncidentResult(
            incident_id=incident.id, status=incident.status, version=incident.version
        )

    async def transition_for_resident(
        self, incident: Incident, target: IncidentStatus, *, resident_id: UUID, reason: str | None
    ) -> None:
        """A resident-driven status change (confirming or disputing a resolution), with
        the same side effects as an operator's: closing their requests, notifications."""
        await self._apply_transition(
            incident, target, actor_type=ActorType.RESIDENT, actor_id=resident_id, reason=reason
        )

    async def close_unconfirmed_resolutions(self, *, limit: int = 100) -> int:
        """Close incidents whose residents neither confirmed nor disputed the resolution
        within ``RESOLUTION_CONFIRMATION_WINDOW`` - silence counts as consent. Incidents
        with an open dispute are left for an operator."""
        cutoff = utc_now() - RESOLUTION_CONFIRMATION_WINDOW
        open_dispute = exists().where(
            ResolutionDispute.incident_id == Incident.id,
            ResolutionDispute.status == ResolutionDisputeStatus.OPEN,
        )
        incidents = (
            await self.session.scalars(
                select(Incident)
                .where(
                    Incident.status.in_(_AWAITING_RESIDENT_STATUSES),
                    Incident.resolved_at <= cutoff,
                    ~open_dispute,
                )
                .order_by(Incident.resolved_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()
        for incident in incidents:
            await self._apply_transition(
                incident,
                IncidentStatus.CLOSED,
                actor_type=ActorType.SYSTEM,
                actor_id=None,
                reason="Резолюция не оспорена жителями в срок - заявка закрыта автоматически",
            )
        await self.session.flush()
        return len(incidents)

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

    async def record_resolution_feedback(
        self,
        incident_id: UUID,
        command: ResolutionFeedbackCommand,
        *,
        resident_id: UUID,
    ) -> ResolutionFeedbackResult:
        incident = await self.session.scalar(
            select(Incident).where(Incident.id == incident_id).with_for_update()
        )
        if incident is None:
            raise IncidentCoreNotFoundError(f"Incident {incident_id} was not found")
        report = await self.session.scalar(
            select(Report)
            .join(IncidentReportLink, IncidentReportLink.report_id == Report.id)
            .where(
                Report.id == command.report_id,
                Report.resident_id == resident_id,
                IncidentReportLink.incident_id == incident.id,
                IncidentReportLink.is_active.is_(True),
            )
            .with_for_update(of=Report)
        )
        if report is None:
            raise IncidentCoreNotFoundError("Report is not linked to this resident and incident")
        allowed = {
            IncidentStatus.RESOLVED,
            IncidentStatus.AWAITING_CONFIRMATION,
            IncidentStatus.RESOLUTION_DISPUTED,
        }
        if incident.status not in allowed:
            raise IncidentCoreConflictError(
                f"Resolution feedback is not allowed in status {incident.status.value}"
            )

        continues = command.feedback is ResolutionFeedback.PROBLEM_CONTINUES
        report.problem_continues = continues
        if continues:
            open_dispute = await self.session.scalar(
                select(ResolutionDispute).where(
                    ResolutionDispute.incident_id == incident.id,
                    ResolutionDispute.resident_id == resident_id,
                    ResolutionDispute.report_id == report.id,
                    ResolutionDispute.status == ResolutionDisputeStatus.OPEN,
                )
            )
            if open_dispute is None:
                self.session.add(
                    ResolutionDispute(
                        incident_id=incident.id,
                        resident_id=resident_id,
                        report_id=report.id,
                        status=ResolutionDisputeStatus.OPEN,
                        comment=command.comment,
                    )
                )
            dispute_count = await self.session.scalar(
                select(func.count(func.distinct(ResolutionDispute.resident_id))).where(
                    ResolutionDispute.incident_id == incident.id,
                    ResolutionDispute.status == ResolutionDisputeStatus.OPEN,
                    ResolutionDispute.created_at >= utc_now() - DISPUTE_ESCALATION_WINDOW,
                )
            )
            if (
                incident.status is not IncidentStatus.RESOLUTION_DISPUTED
                and (dispute_count or 0) >= DISPUTE_ESCALATION_THRESHOLD
            ):
                await self.transition_for_resident(
                    incident,
                    IncidentStatus.RESOLUTION_DISPUTED,
                    resident_id=resident_id,
                    reason=command.comment or "Resident reports that the problem continues",
                )
        elif incident.status in _AWAITING_RESIDENT_STATUSES:
            await self.transition_for_resident(
                incident,
                IncidentStatus.CLOSED,
                resident_id=resident_id,
                reason=command.comment or "Resident confirmed resolution",
            )
        else:
            raise IncidentCoreConflictError("An open resolution dispute must be handled by an operator")
        self._emit(
            incident.id,
            "RESOLUTION_FEEDBACK_RECORDED",
            {
                "incident_id": str(incident.id),
                "report_id": str(report.id),
                "resident_id": str(resident_id),
                "feedback": command.feedback.value,
            },
        )
        await self.session.flush()
        return ResolutionFeedbackResult(
            incident_id=incident.id,
            report_id=report.id,
            incident_status=incident.status,
            feedback=command.feedback,
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
        await self._notify_house_manager(report, incident, new_incident=False)
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
        await self._notify_house_manager(report, incident, new_incident=True)
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
        self._emit(
            report.id,
            "REPORT_GROUPING_DECIDED",
            {
                "report_id": str(report.id),
                "incident_id": str(incident_id) if incident_id else None,
                "outcome": outcome.value,
                "reason_codes": reasons,
            },
            aggregate_type="REPORT",
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

    async def _apply_transition(
        self,
        incident: Incident,
        target: IncidentStatus,
        *,
        actor_type: ActorType,
        actor_id: UUID | None,
        reason: str | None,
    ) -> None:
        """The one place an incident changes status: history, outbox event, and what that
        means for the residents' requests and the organizations handling them."""
        previous = incident.status
        ensure_incident_transition(previous, target)
        incident.status = target
        now = utc_now()
        if target is IncidentStatus.RESOLVED:
            incident.resolved_at = now
        elif target is IncidentStatus.CLOSED:
            incident.closed_at = now
        elif target is IncidentStatus.REOPENED:
            incident.closed_at = None
            incident.resolved_at = None
        self.session.add(
            IncidentStatusHistory(
                incident_id=incident.id,
                from_status=previous,
                to_status=target,
                changed_by_type=actor_type,
                changed_by_id=actor_id,
                reason=reason,
            )
        )
        self._emit(
            incident.id,
            "INCIDENT_STATUS_CHANGED",
            {
                "incident_id": str(incident.id),
                "from_status": previous.value,
                "to_status": target.value,
                "changed_by_type": actor_type.value,
            },
        )

        if target in _AWAITING_RESIDENT_STATUSES and previous not in _AWAITING_RESIDENT_STATUSES:
            days = RESOLUTION_CONFIRMATION_WINDOW.days
            await self._notify_residents(
                incident,
                NotificationType.RESOLUTION_REQUESTED,
                "Проблема устранена - подтвердите",
                f"По вашей заявке «{incident.title}» исполнитель сообщил, что проблема устранена. "
                "Подтвердите это или сообщите, что проблема сохраняется. Если ответа не будет "
                f"в течение {days} дн., заявка будет закрыта автоматически.",
            )
        elif target is IncidentStatus.CLOSED:
            await self._move_linked_reports(incident, ReportStatus.LINKED, ReportStatus.CLOSED, reason)
            await self._notify_residents(
                incident,
                NotificationType.REPORT_STATUS_CHANGED,
                "Заявка закрыта",
                f"Ваша заявка «{incident.title}» закрыта. Спасибо, что помогаете городу!",
            )
        elif target is IncidentStatus.REOPENED:
            await self._move_linked_reports(incident, ReportStatus.CLOSED, ReportStatus.LINKED, reason)
            await self._notify_residents(
                incident,
                NotificationType.INCIDENT_STATUS_CHANGED,
                "Заявка возобновлена",
                f"Работа по вашей заявке «{incident.title}» возобновлена.",
            )
            await self._notify_organizations(
                incident, "INCIDENT_REOPENED", "Заявка возобновлена", reason or incident.title
            )
        elif target is IncidentStatus.RESOLUTION_DISPUTED:
            await self._notify_organizations(
                incident,
                "RESOLUTION_DISPUTED",
                "Жители оспорили решение",
                f"«{incident.title}»: жители сообщают, что проблема сохраняется."
                + (f"\n\n{reason}" if reason else ""),
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

    async def _move_linked_reports(
        self, incident: Incident, source: ReportStatus, target: ReportStatus, reason: str | None
    ) -> None:
        for report in await self._linked_reports(incident):
            if report.status is source:
                self._transition_report(report, target, reason or f"Incident {incident.status.value}")

    async def _notify_residents(
        self, incident: Incident, notification_type: NotificationType, title: str, body: str
    ) -> None:
        for report in await self._linked_reports(incident):
            if report.resident_id is None:
                continue
            self.session.add(
                Notification(
                    resident_id=report.resident_id,
                    type=notification_type,
                    title=title,
                    body=body,
                    incident_id=incident.id,
                    report_id=report.id,
                )
            )

    async def _notify_organizations(self, incident: Incident, event_type: str, title: str, body: str) -> None:
        """Everyone working on the incident: its (non-cancelled) assignees plus the
        managing organization of every affected house."""
        assigned = select(Assignment.organization_id).where(
            Assignment.incident_id == incident.id,
            Assignment.status.not_in({AssignmentStatus.REJECTED, AssignmentStatus.CANCELLED}),
        )
        managing = (
            select(HouseManagement.organization_id)
            .join(IncidentAffectedHouse, IncidentAffectedHouse.house_id == HouseManagement.house_id)
            .where(IncidentAffectedHouse.incident_id == incident.id, HouseManagement.is_active.is_(True))
        )
        organization_ids = set((await self.session.scalars(assigned.union(managing))).all())
        for organization_id in sorted(organization_ids):
            enqueue_organization_notification(
                self.session,
                OrganizationMessage(
                    organization_id=organization_id,
                    event_type=event_type,
                    title=title,
                    body=body,
                    incident_id=incident.id,
                ),
            )

    async def _notify_house_manager(self, report: Report, incident: Incident, *, new_incident: bool) -> None:
        """Route a resident's request to the УК/ТСЖ managing the house it concerns."""
        if report.house_id is None:
            return
        organization_id = await active_house_manager_id(self.session, report.house_id)
        if organization_id is None:
            return
        address = await self.session.scalar(
            select(Address.formatted)
            .join(House, House.address_id == Address.id)
            .where(House.id == report.house_id)
        )
        title = "Новая заявка жителя" if new_incident else "Новое обращение по открытой заявке"
        enqueue_organization_notification(
            self.session,
            OrganizationMessage(
                organization_id=organization_id,
                event_type="RESIDENT_REPORT_RECEIVED",
                title=title,
                body="\n".join(part for part in (address, incident.title, report.text) if part),
                incident_id=incident.id,
                report_id=report.id,
                house_id=report.house_id,
            ),
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


def _decimal(value: float | None) -> Decimal | None:
    return Decimal(f"{value:.6f}") if value is not None else None


def _best_score(proposal: GroupingProposal | None) -> float | None:
    ranked = proposal.ranked if proposal is not None else ()
    return ranked[0].score if ranked else None


class ResolutionDisputeService(SQLAlchemyAsyncRepositoryService[ResolutionDispute]):
    repository_type = ResolutionDisputeRepository
