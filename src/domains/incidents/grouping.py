"""Deterministic report-to-incident business policy.

Text similarity belongs to the optional ML recommendation flow. Incident Core only
applies explicit user choices and unambiguous structured rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Final
from uuid import UUID

SCORER_VERSION: Final = "deterministic-candidate-count-v1"
POLICY_VERSION: Final = "house-category-active-window-v2"


class ProposedAction(StrEnum):
    ATTACH = "ATTACH"
    CREATE = "CREATE"
    CLARIFY = "CLARIFY"


@dataclass(frozen=True, slots=True)
class GroupingConfig:
    candidate_window: timedelta = timedelta(days=3)

    def __post_init__(self) -> None:
        if self.candidate_window <= timedelta(0):
            raise ValueError("candidate_window must be positive")


@dataclass(frozen=True, slots=True)
class IncidentCandidate:
    incident_id: UUID
    last_activity_at: datetime


@dataclass(frozen=True, slots=True)
class GroupingProposal:
    action: ProposedAction
    selected_incident_id: UUID | None
    candidate_incident_ids: tuple[UUID, ...]
    reason_codes: tuple[str, ...]


def propose_grouping(
    candidates: tuple[IncidentCandidate, ...],
    *,
    allow_single_auto_attach: bool,
) -> GroupingProposal:
    """Apply the MVP policy without interpreting free-form text.

    Fixed scenarios may attach automatically only when exactly one active incident
    satisfies the backend-owned house/category/time constraints. ``other`` never
    auto-attaches: the resident must confirm an ML recommendation or create a new
    incident explicitly.
    """

    candidate_ids = tuple(candidate.incident_id for candidate in candidates)
    if not candidates:
        return GroupingProposal(
            ProposedAction.CREATE,
            None,
            (),
            ("NO_ACTIVE_CANDIDATES",),
        )
    if len(candidates) == 1 and allow_single_auto_attach:
        return GroupingProposal(
            ProposedAction.ATTACH,
            candidates[0].incident_id,
            candidate_ids,
            ("SAME_HOUSE", "SAME_CATEGORY", "ONLY_ACTIVE_CANDIDATE"),
        )
    return GroupingProposal(
        ProposedAction.CLARIFY,
        None,
        candidate_ids,
        ("USER_CHOICE_REQUIRED_FOR_OTHER" if not allow_single_auto_attach else "MULTIPLE_ACTIVE_CANDIDATES",),
    )
