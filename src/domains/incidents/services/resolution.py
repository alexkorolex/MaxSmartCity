"""Residents' say on a resolution: confirming, disputing, closing their own report."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from src.common.enums import ActorType
from src.common.models import utc_now
from src.domains.incidents.enums import (
    IncidentStatus,
    ResolutionDisputeStatus,
    ResolutionFeedback,
)
from src.domains.incidents.models import (
    Incident,
    IncidentReportLink,
    ResolutionDispute,
)
from src.domains.incidents.schemas import (
    CloseReportCommand,
    CloseReportResult,
    ResolutionFeedbackCommand,
    ResolutionFeedbackResult,
)
from src.domains.incidents.services.base import (
    ACTIVE_INCIDENT_STATUSES,
    AWAITING_RESIDENT_STATUSES,
    DISPUTE_ESCALATION_THRESHOLD,
    DISPUTE_ESCALATION_WINDOW,
    FINAL_REPORT_STATUSES,
    IncidentCoreConflictError,
    IncidentCoreNotFoundError,
)
from src.domains.incidents.services.transitions import IncidentTransitionsMixin
from src.domains.reports.enums import ReportStatus
from src.domains.reports.models import Report


class IncidentResolutionMixin(IncidentTransitionsMixin):
    """Resident-driven resolution feedback and report closing."""

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
        elif incident.status in AWAITING_RESIDENT_STATUSES:
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

    async def close_by_resident(
        self, report_id: UUID, command: CloseReportCommand, *, resident_id: UUID
    ) -> CloseReportResult:
        """A resident closes their own report because the problem went away.

        - Awaiting their confirmation of a fix: it *is* that confirmation - the incident
          closes (with every resident's report on it).
        - Nobody else is still waiting on the incident and work hasn't started (``NEW``/
          ``TRIAGE``): the incident is cancelled.
        - Otherwise the organizations on the incident are told, so they can wrap it up.
        """
        report = await self.session.scalar(
            select(Report).where(Report.id == report_id, Report.resident_id == resident_id).with_for_update()
        )
        if report is None:
            raise IncidentCoreNotFoundError(f"Report {report_id} was not found")
        if report.status in FINAL_REPORT_STATUSES:
            raise IncidentCoreConflictError(f"Report in status {report.status.value} is already closed")
        comment = (command.comment or "").strip() or None
        incident = await self.session.scalar(
            select(Incident)
            .join(IncidentReportLink, IncidentReportLink.incident_id == Incident.id)
            .where(IncidentReportLink.report_id == report.id, IncidentReportLink.is_active.is_(True))
            .with_for_update(of=Incident)
        )

        if incident is not None and incident.status in AWAITING_RESIDENT_STATUSES:
            await self.record_resolution_feedback(
                incident.id,
                ResolutionFeedbackCommand(
                    report_id=report.id, feedback=ResolutionFeedback.CONFIRMED, comment=comment
                ),
                resident_id=resident_id,
            )
            if report.status not in FINAL_REPORT_STATUSES:
                self._transition_report(
                    report,
                    ReportStatus.CLOSED,
                    comment or "Житель подтвердил, что проблема решена",
                    actor_type=ActorType.RESIDENT,
                    actor_id=resident_id,
                )
        else:
            report.problem_continues = False
            self._transition_report(
                report,
                ReportStatus.CLOSED,
                comment or "Житель сообщил, что проблема решилась",
                actor_type=ActorType.RESIDENT,
                actor_id=resident_id,
            )
            if incident is not None and incident.status in ACTIVE_INCIDENT_STATUSES:
                others_open = any(
                    other.id != report.id and other.status not in FINAL_REPORT_STATUSES
                    for other in await self._linked_reports(incident)
                )
                if not others_open and incident.status in {IncidentStatus.NEW, IncidentStatus.TRIAGE}:
                    await self._apply_transition(
                        incident,
                        IncidentStatus.CANCELLED,
                        actor_type=ActorType.RESIDENT,
                        actor_id=resident_id,
                        reason="Все заявители сообщили, что проблема решилась",
                    )
                else:
                    body = f"«{incident.title}»: заявитель закрыл обращение."
                    if not others_open:
                        body += "\nДругих открытых обращений нет - проверьте и завершите заявку."
                    if comment:
                        body += f"\n\n{comment}"
                    await self._notify_organizations(
                        incident, "RESIDENT_CLOSED_REPORT", "Житель сообщил, что проблема решилась", body
                    )
        self._emit(
            report.id,
            "REPORT_CLOSED_BY_RESIDENT",
            {
                "report_id": str(report.id),
                "resident_id": str(resident_id),
                "incident_id": str(incident.id) if incident else None,
            },
            aggregate_type="REPORT",
        )
        await self.session.flush()
        return CloseReportResult(
            report_id=report.id,
            report_status=report.status.value,
            incident_id=incident.id if incident else None,
            incident_status=incident.status if incident else None,
        )
