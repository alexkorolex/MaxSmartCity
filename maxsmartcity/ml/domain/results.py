"""Independent task results and allow-list validation."""

from dataclasses import dataclass, field

from maxsmartcity.ml.domain.requests import DecisionRequest

CONTRACT_VERSION = "2.0.0-draft"


@dataclass(frozen=True, slots=True)
class ModelMetadata:
    name: str
    version: str
    score_kind: str
    taxonomy_version: str | None = None
    base_model: str | None = None
    dataset_version: str | None = None
    dataset_hash: str | None = None
    calibration_version: str | None = None


@dataclass(frozen=True, slots=True)
class ScoredCandidate:
    id: str
    score: float
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RankingResult:
    candidates: tuple[ScoredCandidate, ...] = ()
    abstain: bool = True
    abstain_reason: str | None = "NOT_CONFIGURED"
    model: ModelMetadata | None = None


@dataclass(frozen=True, slots=True)
class LabelPrediction:
    label_id: str
    score: float | None
    score_kind: str
    source: str


@dataclass(frozen=True, slots=True)
class ExtractedFeatures:
    values: dict[str, object] = field(default_factory=dict)
    missing_fields: tuple[str, ...] = ()
    extractor_version: str = "not-configured"


@dataclass(frozen=True, slots=True)
class DecisionResponse:
    request_id: str
    category: LabelPrediction | None
    features: ExtractedFeatures
    incident_ranking: RankingResult = field(default_factory=RankingResult)
    organization_ranking: RankingResult = field(default_factory=RankingResult)
    action_ranking: RankingResult = field(default_factory=RankingResult)
    requires_manual_review: bool = True
    input_truncated: bool = False
    contract_version: str = CONTRACT_VERSION
    warnings: tuple[str, ...] = ()


def validate_allowed_candidates(request: DecisionRequest, response: DecisionResponse) -> None:
    """Reject identifiers not supplied by backend policy/candidate generation."""
    allowed_groups = (
        (
            {candidate.id for candidate in request.incident_candidates},
            response.incident_ranking.candidates,
        ),
        (
            {candidate.id for candidate in request.organization_candidates},
            response.organization_ranking.candidates,
        ),
        (
            {candidate.id for candidate in request.action_candidates},
            response.action_ranking.candidates,
        ),
    )
    for allowed, ranked in allowed_groups:
        unknown = {candidate.id for candidate in ranked} - allowed
        if unknown:
            msg = f"ML response contains forbidden candidate ids: {sorted(unknown)}"
            raise ValueError(msg)
