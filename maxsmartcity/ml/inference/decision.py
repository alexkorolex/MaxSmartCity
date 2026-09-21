"""Compose the trained category artifact with safe MVP decision components."""

from __future__ import annotations

from dataclasses import replace

from maxsmartcity.ml.domain.requests import DecisionRequest
from maxsmartcity.ml.domain.results import (
    DecisionResponse,
    LabelPrediction,
    ModelMetadata,
    RankingResult,
)
from maxsmartcity.ml.inference.category import CategoryArtifact
from maxsmartcity.ml.ports.models import FeatureExtractor, IncidentRanker


class ArtifactDecisionModel:
    """Inference-only model that never mutates backend state or invents candidate IDs."""

    def __init__(
        self,
        category: CategoryArtifact,
        incident_ranker: IncidentRanker,
        feature_extractor: FeatureExtractor,
    ) -> None:
        self.category = category
        self.incident_ranker = incident_ranker
        self.feature_extractor = feature_extractor

    @property
    def metadata(self) -> ModelMetadata:
        return ModelMetadata(
            name="category-tfidf-logreg",
            version=self.category.model_version,
            score_kind="uncalibrated_probability_with_validation_threshold",
            taxonomy_version=self.category.taxonomy_version,
            dataset_version=self.category.dataset_version,
            dataset_hash=self.category.dataset_hash,
            calibration_version=self.category.calibration_version,
        )

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        prediction = self.category.predict(request.report.text, top_k=1)
        best = prediction.labels[0] if prediction.labels else None
        category = (
            LabelPrediction(
                label_id=best.label_id,
                score=best.score,
                score_kind="uncalibrated_probability",
                source=self.category.model_version,
            )
            if best is not None
            else None
        )

        ranking_request = request
        if request.report.category_hint is None and best is not None and not prediction.abstain:
            ranking_request = replace(
                request,
                report=replace(request.report, category_hint=best.label_id),
            )
        incident_ranking = self.incident_ranker.rank(ranking_request)
        warnings: list[str] = []
        if prediction.abstain:
            warnings.append(f"CATEGORY_ABSTAIN:{prediction.abstain_reason}")
        if incident_ranking.abstain:
            warnings.append("INCIDENT_RANKING_RECOMMENDATION_ONLY")

        return DecisionResponse(
            request_id=request.request_id,
            category=category,
            features=self.feature_extractor.extract(request),
            incident_ranking=incident_ranking,
            organization_ranking=RankingResult(
                abstain_reason=(
                    "NO_ORGANIZATION_CANDIDATES"
                    if not request.organization_candidates
                    else "ORGANIZATION_MODEL_NOT_CONFIGURED"
                )
            ),
            action_ranking=RankingResult(
                abstain_reason=(
                    "NO_ACTION_CANDIDATES" if not request.action_candidates else "ACTION_MODEL_NOT_CONFIGURED"
                )
            ),
            requires_manual_review=prediction.abstain or incident_ranking.abstain,
            warnings=tuple(warnings),
        )
