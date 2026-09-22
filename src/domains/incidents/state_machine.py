from src.common.state_machine import ensure_transition
from src.domains.incidents.enums import IncidentStatus

INCIDENT_TRANSITIONS: dict[IncidentStatus, frozenset[IncidentStatus]] = {
    IncidentStatus.NEW: frozenset({IncidentStatus.TRIAGE, IncidentStatus.REJECTED, IncidentStatus.CANCELLED}),
    IncidentStatus.TRIAGE: frozenset(
        {
            IncidentStatus.CONFIRMED,
            IncidentStatus.REJECTED,
            IncidentStatus.CANCELLED,
            IncidentStatus.MERGED,
        }
    ),
    IncidentStatus.CONFIRMED: frozenset(
        {
            IncidentStatus.ASSIGNED,
            IncidentStatus.IN_PROGRESS,
            IncidentStatus.RESOLVED,
            IncidentStatus.CANCELLED,
            IncidentStatus.MERGED,
        }
    ),
    IncidentStatus.ASSIGNED: frozenset(
        {
            IncidentStatus.IN_PROGRESS,
            IncidentStatus.RESOLVED,
            IncidentStatus.CANCELLED,
            IncidentStatus.MERGED,
        }
    ),
    IncidentStatus.IN_PROGRESS: frozenset(
        {IncidentStatus.RESOLVED, IncidentStatus.CANCELLED, IncidentStatus.MERGED}
    ),
    IncidentStatus.RESOLVED: frozenset(
        {
            IncidentStatus.AWAITING_CONFIRMATION,
            IncidentStatus.CLOSED,
            IncidentStatus.RESOLUTION_DISPUTED,
            IncidentStatus.REOPENED,
        }
    ),
    IncidentStatus.AWAITING_CONFIRMATION: frozenset(
        {IncidentStatus.CLOSED, IncidentStatus.RESOLUTION_DISPUTED, IncidentStatus.REOPENED}
    ),
    IncidentStatus.RESOLUTION_DISPUTED: frozenset(
        {IncidentStatus.IN_PROGRESS, IncidentStatus.RESOLVED, IncidentStatus.CLOSED}
    ),
    IncidentStatus.REOPENED: frozenset(
        {
            IncidentStatus.ASSIGNED,
            IncidentStatus.IN_PROGRESS,
            IncidentStatus.RESOLVED,
            IncidentStatus.CANCELLED,
        }
    ),
    IncidentStatus.CLOSED: frozenset({IncidentStatus.REOPENED}),
    IncidentStatus.REJECTED: frozenset(),
    IncidentStatus.CANCELLED: frozenset(),
    IncidentStatus.MERGED: frozenset(),
}


def ensure_incident_transition(current: IncidentStatus, target: IncidentStatus) -> None:
    ensure_transition(current, target, INCIDENT_TRANSITIONS)
