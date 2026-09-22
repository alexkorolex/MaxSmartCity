"""Deterministic online report-to-incident ranking and decision policy."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Final
from uuid import UUID

SCORER_VERSION: Final = "char-ngram-cosine-v1"
POLICY_VERSION: Final = "house-category-time-v1"
_SPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^\w\s]+", re.UNICODE)


class ProposedAction(StrEnum):
    ATTACH = "ATTACH"
    CREATE = "CREATE"
    CLARIFY = "CLARIFY"


@dataclass(frozen=True, slots=True)
class GroupingConfig:
    candidate_window: timedelta = timedelta(days=3)
    attach_threshold: float = 0.62
    clarify_threshold: float = 0.32
    minimum_margin: float = 0.08
    text_weight: float = 0.85
    recency_weight: float = 0.15

    def __post_init__(self) -> None:
        if self.candidate_window <= timedelta(0):
            raise ValueError("candidate_window must be positive")
        if not 0 <= self.clarify_threshold <= self.attach_threshold <= 1:
            raise ValueError("thresholds must satisfy 0 <= clarify <= attach <= 1")
        if not 0 <= self.minimum_margin <= 1:
            raise ValueError("minimum_margin must be between 0 and 1")
        if not math.isclose(self.text_weight + self.recency_weight, 1.0):
            raise ValueError("text_weight and recency_weight must sum to 1")


@dataclass(frozen=True, slots=True)
class IncidentCandidate:
    incident_id: UUID
    text: str
    last_activity_at: datetime


@dataclass(frozen=True, slots=True)
class ScoredIncident:
    incident_id: UUID
    score: float
    text_score: float
    recency_score: float


@dataclass(frozen=True, slots=True)
class GroupingProposal:
    action: ProposedAction
    selected_incident_id: UUID | None
    ranked: tuple[ScoredIncident, ...]
    reason_codes: tuple[str, ...]


def normalize_text(value: str) -> str:
    return _SPACE_RE.sub(" ", _NON_WORD_RE.sub(" ", value.casefold())).strip()


def char_ngram_cosine(left: str, right: str, *, minimum: int = 3, maximum: int = 5) -> float:
    """Character n-gram cosine is robust to Russian inflection, typos and short phrases."""
    left_vector = _ngrams(normalize_text(left), minimum, maximum)
    right_vector = _ngrams(normalize_text(right), minimum, maximum)
    if not left_vector or not right_vector:
        return 0.0
    dot = sum(count * right_vector.get(key, 0) for key, count in left_vector.items())
    left_norm = math.sqrt(sum(count * count for count in left_vector.values()))
    right_norm = math.sqrt(sum(count * count for count in right_vector.values()))
    return dot / (left_norm * right_norm)


def propose_grouping(
    report_text: str,
    candidates: tuple[IncidentCandidate, ...],
    *,
    occurred_at: datetime,
    config: GroupingConfig | None = None,
) -> GroupingProposal:
    settings = config or GroupingConfig()
    if not candidates:
        return GroupingProposal(ProposedAction.CREATE, None, (), ("NO_ACTIVE_CANDIDATES",))

    ranked = tuple(
        sorted(
            (_score_candidate(report_text, candidate, occurred_at, settings) for candidate in candidates),
            key=lambda candidate: (-candidate.score, str(candidate.incident_id)),
        )
    )
    best = ranked[0]
    runner_up_score = ranked[1].score if len(ranked) > 1 else 0.0
    margin = best.score - runner_up_score
    if best.score >= settings.attach_threshold and margin >= settings.minimum_margin:
        return GroupingProposal(
            ProposedAction.ATTACH,
            best.incident_id,
            ranked,
            ("SAME_HOUSE", "SAME_CATEGORY", "TEXT_AND_TIME_MATCH", "SUFFICIENT_MARGIN"),
        )
    if best.score >= settings.clarify_threshold:
        reasons = ["POSSIBLE_INCIDENT_MATCH"]
        if margin < settings.minimum_margin:
            reasons.append("AMBIGUOUS_TOP_CANDIDATES")
        else:
            reasons.append("BELOW_AUTO_ATTACH_THRESHOLD")
        return GroupingProposal(ProposedAction.CLARIFY, best.incident_id, ranked, tuple(reasons))
    return GroupingProposal(
        ProposedAction.CREATE,
        None,
        ranked,
        ("CANDIDATES_BELOW_SIMILARITY_THRESHOLD",),
    )


def _score_candidate(
    report_text: str,
    candidate: IncidentCandidate,
    occurred_at: datetime,
    config: GroupingConfig,
) -> ScoredIncident:
    text_score = char_ngram_cosine(report_text, candidate.text)
    age = max(timedelta(0), occurred_at - candidate.last_activity_at)
    recency_score = max(0.0, 1.0 - age / config.candidate_window)
    score = config.text_weight * text_score + config.recency_weight * recency_score
    return ScoredIncident(
        incident_id=candidate.incident_id,
        score=round(score, 6),
        text_score=round(text_score, 6),
        recency_score=round(recency_score, 6),
    )


def _ngrams(value: str, minimum: int, maximum: int) -> Counter[str]:
    padded = f" {value} "
    return Counter(
        padded[index : index + size]
        for size in range(minimum, maximum + 1)
        for index in range(max(0, len(padded) - size + 1))
    )
