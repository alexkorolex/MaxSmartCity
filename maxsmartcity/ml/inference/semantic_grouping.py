"""Advisory semantic grouping for reports in the ``other`` category."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Final

import numpy as np

from maxsmartcity.ml.ports.embeddings import TextEmbeddingProvider
from maxsmartcity.ml.ports.models import ComponentUnavailableError

SEMANTIC_SCORER_VERSION: Final = "exact-text-or-multilingual-e5-cosine-v3"


class SemanticAction(StrEnum):
    ATTACH = "ATTACH"
    CREATE = "CREATE"
    CLARIFY = "CLARIFY"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True, slots=True)
class SemanticGroupingConfig:
    attach_threshold: float = 0.92
    clarify_threshold: float = 0.88
    minimum_margin: float = 0.02
    candidate_window: timedelta = timedelta(days=3)
    max_candidates: int = 16
    max_profile_characters: int = 4_000

    def __post_init__(self) -> None:
        if not 0 <= self.clarify_threshold <= self.attach_threshold <= 1:
            raise ValueError("thresholds must satisfy 0 <= clarify <= attach <= 1")
        if not 0 <= self.minimum_margin <= 1:
            raise ValueError("minimum_margin must be between 0 and 1")
        if self.candidate_window <= timedelta(0):
            raise ValueError("candidate_window must be positive")
        if self.max_candidates < 1 or self.max_profile_characters < 1:
            raise ValueError("candidate and profile limits must be positive")


@dataclass(frozen=True, slots=True)
class SemanticIncidentCandidate:
    incident_id: str
    title: str
    representative_texts: tuple[str, ...]
    last_activity_at: datetime


@dataclass(frozen=True, slots=True)
class SemanticScoredCandidate:
    incident_id: str
    score: float


@dataclass(frozen=True, slots=True)
class SemanticGroupingRecommendation:
    action: SemanticAction
    selected_incident_id: str | None
    candidates: tuple[SemanticScoredCandidate, ...]
    suggested_title: str | None
    reason_codes: tuple[str, ...]
    model_name: str | None
    scorer_version: str = SEMANTIC_SCORER_VERSION


class SemanticGroupingService:
    """Ranks a bounded candidate set; it never writes incidents or overrides the user."""

    def __init__(
        self,
        embedding_provider: TextEmbeddingProvider | None,
        config: SemanticGroupingConfig | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.config = config or SemanticGroupingConfig()

    def recommend(
        self,
        text: str,
        candidates: tuple[SemanticIncidentCandidate, ...],
        *,
        occurred_at: datetime,
    ) -> SemanticGroupingRecommendation:
        normalized_text = " ".join(text.split())
        if not normalized_text:
            return self._abstain("EMPTY_TEXT")
        oldest_allowed_activity = occurred_at - self.config.candidate_window
        eligible = tuple(
            candidate for candidate in candidates if candidate.last_activity_at >= oldest_allowed_activity
        )
        if len(eligible) > self.config.max_candidates:
            return self._abstain("CANDIDATE_LIMIT_EXCEEDED")
        if not eligible:
            return SemanticGroupingRecommendation(
                action=SemanticAction.CREATE,
                selected_incident_id=None,
                candidates=(),
                suggested_title=suggest_cluster_title((normalized_text,)),
                reason_codes=("NO_ELIGIBLE_CANDIDATES",),
                model_name=self.embedding_provider.model_name if self.embedding_provider else None,
            )

        exact_matches = tuple(
            candidate
            for candidate in eligible
            if normalized_text.casefold()
            in {
                _normalize_text(candidate.title),
                *(_normalize_text(value) for value in candidate.representative_texts),
            }
        )
        if exact_matches:
            ranked = tuple(
                SemanticScoredCandidate(candidate.incident_id, 1.0)
                for candidate in sorted(exact_matches, key=lambda item: item.incident_id)
            )
            return SemanticGroupingRecommendation(
                action=SemanticAction.ATTACH if len(ranked) == 1 else SemanticAction.CLARIFY,
                selected_incident_id=ranked[0].incident_id,
                candidates=ranked,
                suggested_title=None,
                reason_codes=(
                    ("EXACT_TEXT_MATCH",)
                    if len(ranked) == 1
                    else ("EXACT_TEXT_MATCH", "DUPLICATE_EXACT_CANDIDATES")
                ),
                model_name=self.embedding_provider.model_name if self.embedding_provider else None,
            )
        if self.embedding_provider is None:
            return self._abstain("SEMANTIC_MODEL_DISABLED")

        profiles = tuple(self._profile(candidate) for candidate in eligible)
        try:
            query_vectors = self.embedding_provider.embed_queries((normalized_text,))
            document_vectors = self.embedding_provider.embed_documents(profiles)
            if query_vectors.shape[0] != 1 or document_vectors.shape[0] != len(eligible):
                raise ComponentUnavailableError("SEMANTIC_MODEL_OUTPUT_INVALID")
            query = _normalize(query_vectors[0])
            document_vectors = np.asarray([_normalize(vector) for vector in document_vectors])
        except ComponentUnavailableError:
            return self._abstain("SEMANTIC_MODEL_UNAVAILABLE")
        scores = document_vectors @ query
        ranked = tuple(
            sorted(
                (
                    SemanticScoredCandidate(candidate.incident_id, round(float(score), 6))
                    for candidate, score in zip(eligible, scores, strict=True)
                ),
                key=lambda item: (-item.score, item.incident_id),
            )
        )
        best = ranked[0]
        runner_up = ranked[1].score if len(ranked) > 1 else 0.0
        margin = best.score - runner_up
        if best.score >= self.config.attach_threshold and margin >= self.config.minimum_margin:
            return SemanticGroupingRecommendation(
                SemanticAction.ATTACH,
                best.incident_id,
                ranked,
                None,
                ("SEMANTIC_MATCH", "SUFFICIENT_MARGIN"),
                self.embedding_provider.model_name,
            )
        if best.score >= self.config.clarify_threshold:
            reasons = ["POSSIBLE_SEMANTIC_MATCH"]
            reasons.append(
                "AMBIGUOUS_TOP_CANDIDATES"
                if margin < self.config.minimum_margin
                else "BELOW_AUTO_ATTACH_THRESHOLD"
            )
            return SemanticGroupingRecommendation(
                SemanticAction.CLARIFY,
                best.incident_id,
                ranked,
                None,
                tuple(reasons),
                self.embedding_provider.model_name,
            )
        return SemanticGroupingRecommendation(
            SemanticAction.CREATE,
            None,
            ranked,
            suggest_cluster_title((normalized_text,)),
            ("CANDIDATES_BELOW_SEMANTIC_THRESHOLD",),
            self.embedding_provider.model_name,
        )

    def _profile(self, candidate: SemanticIncidentCandidate) -> str:
        parts = (candidate.title, *candidate.representative_texts)
        return "\n".join(part for part in parts if part)[: self.config.max_profile_characters]

    def _abstain(self, reason: str) -> SemanticGroupingRecommendation:
        return SemanticGroupingRecommendation(
            SemanticAction.ABSTAIN,
            None,
            (),
            None,
            (reason,),
            self.embedding_provider.model_name if self.embedding_provider else None,
        )


def suggest_cluster_title(texts: tuple[str, ...]) -> str:
    """Use stable presentation metadata without interpreting free-form text."""

    del texts
    return "Другая проблема"


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).casefold()


def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm) or norm == 0:
        raise ComponentUnavailableError("SEMANTIC_MODEL_OUTPUT_ZERO_VECTOR")
    return np.asarray(vector, dtype=np.float32) / norm
