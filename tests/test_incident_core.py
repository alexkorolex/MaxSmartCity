import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
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
    propose_grouping,
)
from src.domains.incidents.state_machine import INCIDENT_TRANSITIONS, ensure_incident_transition
from src.domains.reports.enums import ReportStatus
from src.domains.reports.state_machine import REPORT_TRANSITIONS, ensure_report_transition

NOW = datetime(2026, 9, 22, 12, tzinfo=UTC)
ROOT = Path(__file__).resolve().parent.parent


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
def test_terminal_states_reject_transitions(
    validator: Callable[[object, object], None], current: object, target: object
) -> None:
    with pytest.raises(InvalidStateTransition):
        validator(current, target)


def test_deterministic_policy_attaches_only_active_candidate_for_fixed_scenario() -> None:
    incident_id = uuid4()
    proposal = propose_grouping(
        (
            IncidentCandidate(
                incident_id,
                NOW - timedelta(hours=1),
            ),
        ),
        allow_single_auto_attach=True,
    )
    assert proposal.action is ProposedAction.ATTACH
    assert proposal.selected_incident_id == incident_id


def test_online_policy_asks_when_top_candidates_are_ambiguous() -> None:
    candidates = tuple(IncidentCandidate(uuid4(), NOW - timedelta(minutes=index)) for index in (10, 20))
    proposal = propose_grouping(candidates, allow_single_auto_attach=True)
    assert proposal.action is ProposedAction.CLARIFY
    assert "MULTIPLE_ACTIVE_CANDIDATES" in proposal.reason_codes


def test_deterministic_policy_creates_when_there_are_no_candidates() -> None:
    proposal = propose_grouping((), allow_single_auto_attach=True)
    assert proposal.action is ProposedAction.CREATE
    assert proposal.selected_incident_id is None


def test_other_never_auto_attaches_without_resident_choice() -> None:
    incident_id = uuid4()
    proposal = propose_grouping(
        (IncidentCandidate(incident_id, NOW - timedelta(hours=1)),),
        allow_single_auto_attach=False,
    )
    assert proposal.action is ProposedAction.CLARIFY
    assert proposal.selected_incident_id is None
    assert proposal.candidate_incident_ids == (incident_id,)
    assert proposal.reason_codes == ("USER_CHOICE_REQUIRED_FOR_OTHER",)


def test_candidate_window_must_be_positive() -> None:
    with pytest.raises(ValueError, match="candidate_window"):
        GroupingConfig(candidate_window=timedelta(0))


def test_seeded_problem_categories_match_ml_taxonomy() -> None:
    taxonomy = json.loads((ROOT / "ml/configs/taxonomy.backend-aligned.v2.json").read_text(encoding="utf-8"))
    migration = (ROOT / "migrations/sql/013_incident_mvp.up.sql").read_text(encoding="utf-8")

    for category in taxonomy["categories"]:
        assert f"'{category['id']}'" in migration
