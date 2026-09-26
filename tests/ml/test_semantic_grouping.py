from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import numpy as np

from maxsmartcity.ml.inference.semantic_grouping import (
    SemanticAction,
    SemanticGroupingConfig,
    SemanticGroupingService,
    SemanticIncidentCandidate,
    suggest_cluster_title,
)
from maxsmartcity.ml.ports.models import ComponentUnavailableError

NOW = datetime(2026, 9, 25, 12, tzinfo=UTC)


class FixedEmbeddingProvider:
    model_name = "fixed-test-embeddings"

    def __init__(self, vectors: tuple[tuple[float, ...], ...]) -> None:
        self.vectors = vectors

    def embed_queries(self, texts: Sequence[str]) -> np.ndarray:
        assert len(texts) == 1
        return np.asarray(self.vectors[:1], dtype=np.float32)

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        assert len(texts) == len(self.vectors) - 1
        return np.asarray(self.vectors[1:], dtype=np.float32)


class UnavailableEmbeddingProvider:
    model_name = "unavailable"

    def embed_queries(self, texts: Sequence[str]) -> np.ndarray:
        del texts
        raise ComponentUnavailableError

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        del texts
        raise ComponentUnavailableError


def candidate(identifier: str, text: str, *, age_hours: int = 1) -> SemanticIncidentCandidate:
    return SemanticIncidentCandidate(
        incident_id=identifier,
        title=text,
        representative_texts=(text,),
        last_activity_at=NOW - timedelta(hours=age_hours),
    )


def test_clear_semantic_match_is_only_a_recommendation_to_attach() -> None:
    service = SemanticGroupingService(
        FixedEmbeddingProvider(((1, 0), (0.99, 0.01), (0, 1))),
        SemanticGroupingConfig(attach_threshold=0.9, clarify_threshold=0.7),
    )

    result = service.recommend(
        "во дворе огромная яма",
        (candidate("INC-ROAD", "разбит асфальт во дворе"), candidate("INC-NOISE", "ночной шум")),
        occurred_at=NOW,
    )

    assert result.action is SemanticAction.ATTACH
    assert result.selected_incident_id == "INC-ROAD"
    assert result.reason_codes == ("SEMANTIC_MATCH", "SUFFICIENT_MARGIN")


def test_close_candidates_require_user_clarification() -> None:
    service = SemanticGroupingService(
        FixedEmbeddingProvider(((1, 0), (0.9, 0.1), (0.89, 0.11))),
        SemanticGroupingConfig(attach_threshold=0.8, clarify_threshold=0.7, minimum_margin=0.04),
    )

    result = service.recommend(
        "что-то шумит у подъезда",
        (candidate("INC-A", "шум вентиляции"), candidate("INC-B", "шум трансформатора")),
        occurred_at=NOW,
    )

    assert result.action is SemanticAction.CLARIFY
    assert result.selected_incident_id == "INC-A"
    assert "AMBIGUOUS_TOP_CANDIDATES" in result.reason_codes


def test_no_candidates_recommends_creation_with_short_title_without_embedding_call() -> None:
    service = SemanticGroupingService(UnavailableEmbeddingProvider())

    result = service.recommend("сломана детская площадка", (), occurred_at=NOW)

    assert result.action is SemanticAction.CREATE
    assert result.suggested_title == "Другая проблема"


def test_unavailable_model_abstains_instead_of_breaking_core_flow() -> None:
    service = SemanticGroupingService(UnavailableEmbeddingProvider())

    result = service.recommend(
        "непонятная проблема",
        (candidate("INC-1", "другая проблема"),),
        occurred_at=NOW,
    )

    assert result.action is SemanticAction.ABSTAIN
    assert result.reason_codes == ("SEMANTIC_MODEL_UNAVAILABLE",)


def test_old_candidates_are_excluded_before_inference() -> None:
    service = SemanticGroupingService(UnavailableEmbeddingProvider())

    result = service.recommend(
        "снова сломана калитка",
        (candidate("INC-OLD", "сломана калитка", age_hours=100),),
        occurred_at=NOW,
    )

    assert result.action is SemanticAction.CREATE
    assert result.reason_codes == ("NO_ELIGIBLE_CANDIDATES",)


def test_candidate_limit_causes_safe_abstention() -> None:
    service = SemanticGroupingService(
        UnavailableEmbeddingProvider(), SemanticGroupingConfig(max_candidates=2)
    )

    result = service.recommend(
        "проблема во дворе",
        tuple(candidate(f"INC-{index}", "двор") for index in range(3)),
        occurred_at=NOW,
    )

    assert result.action is SemanticAction.ABSTAIN
    assert result.reason_codes == ("CANDIDATE_LIMIT_EXCEEDED",)


def test_cluster_title_is_deterministic_and_never_controls_grouping() -> None:
    title = suggest_cluster_title(
        (
            "Во дворе сломана детская площадка",
            "Детская площадка опять сломана",
        )
    )

    assert title == "Другая проблема"
