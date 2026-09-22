from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.common.state_machine import InvalidStateTransition
from src.domains.collaboration.enums import AssignmentStatus
from src.domains.collaboration.state_machine import (
    ASSIGNMENT_TRANSITIONS,
    ensure_assignment_transition,
)
from src.domains.incidents.enums import IncidentStatus
from src.domains.incidents.grouping import (
    GroupingConfig,
    IncidentCandidate,
    ProposedAction,
    char_ngram_cosine,
    propose_grouping,
)
from src.domains.incidents.state_machine import INCIDENT_TRANSITIONS, ensure_incident_transition
from src.domains.reports.enums import ReportStatus
from src.domains.reports.state_machine import REPORT_TRANSITIONS, ensure_report_transition

NOW = datetime(2026, 9, 22, 12, tzinfo=UTC)


def test_state_machines_cover_every_declared_state() -> None:
    assert set(REPORT_TRANSITIONS) == set(ReportStatus)
    assert set(INCIDENT_TRANSITIONS) == set(IncidentStatus)
    assert set(ASSIGNMENT_TRANSITIONS) == set(AssignmentStatus)


def test_valid_state_transitions_are_accepted() -> None:
    ensure_report_transition(ReportStatus.RECEIVED, ReportStatus.PROCESSING)
    ensure_incident_transition(IncidentStatus.IN_PROGRESS, IncidentStatus.RESOLVED)
    ensure_assignment_transition(AssignmentStatus.PROPOSED, AssignmentStatus.ACCEPTED)


@pytest.mark.parametrize(
    ("validator", "current", "target"),
    [
        (ensure_report_transition, ReportStatus.WITHDRAWN, ReportStatus.PROCESSING),
        (ensure_incident_transition, IncidentStatus.CANCELLED, IncidentStatus.IN_PROGRESS),
        (ensure_assignment_transition, AssignmentStatus.COMPLETED, AssignmentStatus.IN_PROGRESS),
    ],
)
def test_terminal_states_reject_transitions(validator: object, current: object, target: object) -> None:
    with pytest.raises(InvalidStateTransition):
        validator(current, target)  # type: ignore[operator]


def test_character_similarity_handles_russian_inflection_and_typo() -> None:
    score = char_ngram_cosine(
        "В доме не работает лифт",
        "Лифт снова не работаeт в нашем доме",
    )
    assert score > 0.45


def test_online_policy_attaches_clear_match() -> None:
    incident_id = uuid4()
    proposal = propose_grouping(
        "Во всём доме нет холодной воды",
        (
            IncidentCandidate(
                incident_id,
                "Нет холодной воды во всём доме",
                NOW - timedelta(hours=1),
            ),
        ),
        occurred_at=NOW,
    )
    assert proposal.action is ProposedAction.ATTACH
    assert proposal.selected_incident_id == incident_id


def test_online_policy_asks_when_top_candidates_are_ambiguous() -> None:
    candidates = tuple(
        IncidentCandidate(uuid4(), "В доме нет воды", NOW - timedelta(minutes=index)) for index in (10, 20)
    )
    proposal = propose_grouping("В доме нет воды", candidates, occurred_at=NOW)
    assert proposal.action is ProposedAction.CLARIFY
    assert "AMBIGUOUS_TOP_CANDIDATES" in proposal.reason_codes


def test_online_policy_creates_for_unrelated_text() -> None:
    proposal = propose_grouping(
        "Не вывезли мусор из контейнеров",
        (IncidentCandidate(uuid4(), "Не работает лифт", NOW - timedelta(hours=1)),),
        occurred_at=NOW,
    )
    assert proposal.action is ProposedAction.CREATE
    assert proposal.selected_incident_id is None


def test_grouping_thresholds_are_validated() -> None:
    with pytest.raises(ValueError, match="thresholds"):
        GroupingConfig(attach_threshold=0.3, clarify_threshold=0.5)
