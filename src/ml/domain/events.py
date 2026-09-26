"""Backend-facing asynchronous job and feedback contracts."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from src.ml.domain.requests import DecisionRequest
from src.ml.domain.results import DecisionResponse


class FeedbackType(StrEnum):
    ACCEPTED = "ACCEPTED"
    OVERRIDDEN = "OVERRIDDEN"
    REPORT_DETACHED = "REPORT_DETACHED"
    REPORT_ATTACHED = "REPORT_ATTACHED"
    INCIDENT_MERGED = "INCIDENT_MERGED"
    INCIDENT_SPLIT = "INCIDENT_SPLIT"
    ORGANIZATION_CHANGED = "ORGANIZATION_CHANGED"
    RESOLUTION_DISPUTED = "RESOLUTION_DISPUTED"


@dataclass(frozen=True, slots=True)
class DecisionRequested:
    event_id: str
    occurred_at: datetime
    request_id: str
    attempt: int
    request: DecisionRequest


@dataclass(frozen=True, slots=True)
class DecisionCompleted:
    event_id: str
    causation_event_id: str
    occurred_at: datetime
    request_id: str
    response: DecisionResponse


@dataclass(frozen=True, slots=True)
class DecisionFailed:
    event_id: str
    causation_event_id: str
    occurred_at: datetime
    request_id: str
    error_code: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class DecisionFeedback:
    feedback_id: str
    decision_id: str
    occurred_at: datetime
    feedback_type: FeedbackType
    prediction: dict[str, object]
    operator_action: dict[str, object]
    metadata: dict[str, str] = field(default_factory=dict)
