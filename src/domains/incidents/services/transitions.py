"""Incident status changes: operator transitions, «Работы выполнены», auto-closing."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import exists, select

from src.common.enums import ActorType
from src.common.models import utc_now
from src.common.state_machine import transition_path
from src.domains.collaboration.enums import AssignmentStatus
from src.domains.collaboration.models import Assignment, AssignmentStatusHistory
from src.domains.collaboration.state_machine import ASSIGNMENT_TRANSITIONS
from src.domains.identity.models import Organization
from src.domains.incidents.enums import (
    IncidentStatus,
    ResolutionDisputeStatus,
)
from src.domains.incidents.models import (
    Incident,
    IncidentStatusHistory,
    ResolutionDispute,
)
from src.domains.incidents.schemas import (
    CompleteIncidentCommand,
    TransitionIncidentCommand,
    TransitionIncidentResult,
)
from src.domains.incidents.services.base import (
    AWAITING_RESIDENT_STATUSES,
    OPEN_ASSIGNMENT_STATUSES,
    RESOLUTION_CONFIRMATION_WINDOW,
    STAFF_COMPLETABLE_STATUSES,
    IncidentCoreConflictError,
    IncidentCoreNotFoundError,
)
from src.domains.incidents.services.notifications import IncidentNotificationsMixin
from src.domains.incidents.state_machine import INCIDENT_TRANSITIONS, ensure_incident_transition
from src.domains.notifications.enums import NotificationType
from src.domains.reports.enums import ReportStatus


class IncidentTransitionsMixin(IncidentNotificationsMixin):
    """Every incident status change goes through ``_apply_transition`` here."""

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
                    Incident.status.in_(AWAITING_RESIDENT_STATUSES),
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

    async def complete_by_staff(
        self,
        incident_id: UUID,
        command: CompleteIncidentCommand,
        *,
        changed_by: UUID,
        organization_id: UUID | None,
    ) -> TransitionIncidentResult:
        """A staff member reports the work as done: their organization's own assignments are
        completed, and the incident goes through the normal intermediate statuses to
        ``RESOLVED`` - residents are then asked to confirm (and the incident auto-closes
        after ``RESOLUTION_CONFIRMATION_WINDOW``). Refused while another organization's
        required assignment is still open. With no resident behind the incident there is
        nobody to confirm, so it is closed right away."""
        incident = await self.session.scalar(
            select(Incident).where(Incident.id == incident_id).with_for_update()
        )
        if incident is None:
            raise IncidentCoreNotFoundError(f"Incident {incident_id} was not found")
        if incident.status not in STAFF_COMPLETABLE_STATUSES:
            raise IncidentCoreConflictError(f"Incident in status {incident.status.value} cannot be completed")
        reason = (command.comment or "").strip() or "Работы выполнены"

        if organization_id is not None:
            own_assignments = (
                await self.session.scalars(
                    select(Assignment)
                    .where(
                        Assignment.incident_id == incident.id,
                        Assignment.organization_id == organization_id,
                        Assignment.status.in_(OPEN_ASSIGNMENT_STATUSES),
                    )
                    .with_for_update()
                )
            ).all()
            for assignment in own_assignments:
                self._complete_assignment(assignment, changed_by=changed_by, reason=reason)
            await self.session.flush()

        open_elsewhere = (
            await self.session.scalars(
                select(Organization.name)
                .join(Assignment, Assignment.organization_id == Organization.id)
                .where(
                    Assignment.incident_id == incident.id,
                    Assignment.required.is_(True),
                    Assignment.status.in_(OPEN_ASSIGNMENT_STATUSES),
                )
                .distinct()
            )
        ).all()
        if open_elsewhere:
            raise IncidentCoreConflictError(
                "Other required assignments are still open: " + ", ".join(sorted(open_elsewhere))
            )

        for step in transition_path(incident.status, IncidentStatus.RESOLVED, INCIDENT_TRANSITIONS):
            await self._apply_transition(
                incident,
                step,
                actor_type=ActorType.OPERATOR,
                actor_id=changed_by,
                reason=reason if step is IncidentStatus.RESOLVED else "Пройдено при завершении работ",
            )
        has_resident_reports = any(report.resident_id for report in await self._linked_reports(incident))
        if not has_resident_reports:
            await self._apply_transition(
                incident,
                IncidentStatus.CLOSED,
                actor_type=ActorType.OPERATOR,
                actor_id=changed_by,
                reason="Нет заявителей-жителей для подтверждения - закрыто сразу",
            )
        await self.session.flush()
        return TransitionIncidentResult(
            incident_id=incident.id, status=incident.status, version=incident.version
        )

    def _complete_assignment(self, assignment: Assignment, *, changed_by: UUID, reason: str) -> None:
        now = utc_now()
        for step in transition_path(assignment.status, AssignmentStatus.COMPLETED, ASSIGNMENT_TRANSITIONS):
            previous = assignment.status
            assignment.status = step
            if step is AssignmentStatus.ACCEPTED:
                assignment.accepted_at = now
            elif step is AssignmentStatus.IN_PROGRESS:
                assignment.started_at = assignment.started_at or now
            elif step is AssignmentStatus.COMPLETED:
                assignment.completed_at = now
            self.session.add(
                AssignmentStatusHistory(
                    assignment_id=assignment.id,
                    from_status=previous,
                    to_status=step,
                    changed_by=changed_by,
                    reason=reason,
                )
            )
        self._emit(
            assignment.id,
            "ASSIGNMENT_STATUS_CHANGED",
            {
                "assignment_id": str(assignment.id),
                "incident_id": str(assignment.incident_id),
                "to_status": AssignmentStatus.COMPLETED.value,
            },
            aggregate_type="ASSIGNMENT",
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

        if target in AWAITING_RESIDENT_STATUSES and previous not in AWAITING_RESIDENT_STATUSES:
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
