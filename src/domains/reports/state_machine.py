from src.common.state_machine import ensure_transition
from src.domains.reports.enums import ReportStatus

REPORT_TRANSITIONS: dict[ReportStatus, frozenset[ReportStatus]] = {
    ReportStatus.RECEIVED: frozenset(
        {
            ReportStatus.CLOSED,
            ReportStatus.PROCESSING,
            ReportStatus.NEEDS_CLARIFICATION,
            ReportStatus.REJECTED,
            ReportStatus.WITHDRAWN,
        }
    ),
    ReportStatus.PROCESSING: frozenset(
        {
            ReportStatus.CLOSED,
            ReportStatus.READY_FOR_TRIAGE,
            ReportStatus.LINKED,
            ReportStatus.NEEDS_CLARIFICATION,
            ReportStatus.REJECTED,
            ReportStatus.WITHDRAWN,
        }
    ),
    ReportStatus.READY_FOR_TRIAGE: frozenset(
        {
            ReportStatus.CLOSED,
            ReportStatus.LINKED,
            ReportStatus.NEEDS_CLARIFICATION,
            ReportStatus.REJECTED,
            ReportStatus.WITHDRAWN,
        }
    ),
    ReportStatus.NEEDS_CLARIFICATION: frozenset(
        {
            ReportStatus.CLOSED,
            ReportStatus.PROCESSING,
            ReportStatus.READY_FOR_TRIAGE,
            ReportStatus.LINKED,
            ReportStatus.REJECTED,
            ReportStatus.WITHDRAWN,
        }
    ),
    ReportStatus.LINKED: frozenset({ReportStatus.WITHDRAWN, ReportStatus.CLOSED}),
    ReportStatus.CLOSED: frozenset({ReportStatus.LINKED}),
    ReportStatus.REJECTED: frozenset(),
    ReportStatus.WITHDRAWN: frozenset(),
}


def ensure_report_transition(current: ReportStatus, target: ReportStatus) -> None:
    ensure_transition(current, target, REPORT_TRANSITIONS)
