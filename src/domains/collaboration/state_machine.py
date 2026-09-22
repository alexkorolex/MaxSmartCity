from src.common.state_machine import ensure_transition
from src.domains.collaboration.enums import AssignmentStatus

ASSIGNMENT_TRANSITIONS: dict[AssignmentStatus, frozenset[AssignmentStatus]] = {
    AssignmentStatus.PROPOSED: frozenset(
        {AssignmentStatus.ACCEPTED, AssignmentStatus.REJECTED, AssignmentStatus.CANCELLED}
    ),
    AssignmentStatus.ACCEPTED: frozenset({AssignmentStatus.IN_PROGRESS, AssignmentStatus.CANCELLED}),
    AssignmentStatus.IN_PROGRESS: frozenset(
        {
            AssignmentStatus.BLOCKED,
            AssignmentStatus.COMPLETED,
            AssignmentStatus.MONITORING,
            AssignmentStatus.CANCELLED,
        }
    ),
    AssignmentStatus.BLOCKED: frozenset({AssignmentStatus.IN_PROGRESS, AssignmentStatus.CANCELLED}),
    AssignmentStatus.MONITORING: frozenset(
        {
            AssignmentStatus.IN_PROGRESS,
            AssignmentStatus.COMPLETED,
            AssignmentStatus.CANCELLED,
        }
    ),
    AssignmentStatus.COMPLETED: frozenset(),
    AssignmentStatus.REJECTED: frozenset(),
    AssignmentStatus.CANCELLED: frozenset(),
}


def ensure_assignment_transition(current: AssignmentStatus, target: AssignmentStatus) -> None:
    ensure_transition(current, target, ASSIGNMENT_TRANSITIONS)
