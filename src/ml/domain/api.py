"""Transport-neutral batch, health and error response objects."""

from dataclasses import dataclass
from enum import StrEnum

from src.ml.domain.requests import DecisionRequest
from src.ml.domain.results import DecisionResponse, ModelMetadata


class ErrorCode(StrEnum):
    INVALID_INPUT = "INVALID_INPUT"
    INPUT_TOO_LONG = "INPUT_TOO_LONG"
    UNKNOWN_CONTRACT_VERSION = "UNKNOWN_CONTRACT_VERSION"
    FORBIDDEN_CANDIDATE = "FORBIDDEN_CANDIDATE"
    MODEL_NOT_READY = "MODEL_NOT_READY"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    BATCH_OVERFLOW = "BATCH_OVERFLOW"


@dataclass(frozen=True, slots=True)
class ErrorResponse:
    request_id: str | None
    code: ErrorCode
    message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class BatchDecisionRequest:
    batch_id: str
    items: tuple[DecisionRequest, ...]
    deadline_ms: int


@dataclass(frozen=True, slots=True)
class BatchDecisionItem:
    request_id: str
    response: DecisionResponse | None = None
    error: ErrorResponse | None = None


@dataclass(frozen=True, slots=True)
class BatchDecisionResponse:
    batch_id: str
    items: tuple[BatchDecisionItem, ...]


@dataclass(frozen=True, slots=True)
class HealthResponse:
    status: str


@dataclass(frozen=True, slots=True)
class ReadinessResponse:
    ready: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ModelsResponse:
    models: tuple[ModelMetadata, ...]
