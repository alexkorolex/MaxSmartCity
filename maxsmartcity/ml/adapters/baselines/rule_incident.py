"""Config-driven benchmark using only structured evidence."""

from datetime import timedelta

from maxsmartcity.ml.data.config import RuleBaselineConfig
from maxsmartcity.ml.domain.requests import DecisionRequest
from maxsmartcity.ml.domain.results import (
    DecisionResponse,
    ExtractedFeatures,
    LabelPrediction,
    ModelMetadata,
    RankingResult,
    ScoredCandidate,
)
from maxsmartcity.ml.ports.models import FeatureExtractor


class RuleIncidentRanker:
    def __init__(self, config: RuleBaselineConfig) -> None:
        self.config = config

    def rank(self, request: DecisionRequest) -> RankingResult:
        positive_total = sum(
            (
                self.config.same_location_weight,
                self.config.same_category_weight,
                self.config.close_in_time_weight,
            )
        )
        if positive_total <= 0:
            msg = "positive rule weights must have a sum greater than zero"
            raise ValueError(msg)
        ranked: list[ScoredCandidate] = []
        for candidate in request.incident_candidates:
            raw_score = 0.0
            reasons: list[str] = []
            if request.report.house_id and request.report.house_id in candidate.affected_house_ids:
                raw_score += self.config.same_location_weight
                reasons.append("SAME_HOUSE_ID")
            elif request.report.house_id and candidate.affected_house_ids:
                reasons.append("DIFFERENT_HOUSE_ID")
            elif request.report.fias_guid and request.report.fias_guid in candidate.fias_guids:
                raw_score += self.config.same_location_weight
                reasons.append("SAME_FIAS_GUID_FALLBACK")
            elif request.report.fias_guid and candidate.fias_guids:
                reasons.append("DIFFERENT_FIAS_GUID_FALLBACK")
            if (
                request.report.category_hint
                and candidate.category_id == request.report.category_hint
            ):
                raw_score += self.config.same_category_weight
                reasons.append("SAME_CATEGORY_HINT")
            if abs(request.report.created_at - candidate.started_at) <= timedelta(
                seconds=self.config.close_in_time_seconds
            ):
                raw_score += self.config.close_in_time_weight
                reasons.append("CLOSE_IN_TIME")
            if not candidate.active:
                raw_score += self.config.inactive_penalty
                reasons.append("INACTIVE_INCIDENT")
            score = max(0.0, min(1.0, raw_score / positive_total))
            ranked.append(ScoredCandidate(candidate.id, score, tuple(reasons)))
        ranked.sort(key=lambda item: (-item.score, item.id))
        return RankingResult(
            candidates=tuple(ranked),
            abstain=not self.config.automation_enabled,
            abstain_reason=(
                None if self.config.automation_enabled else "BASELINE_NOT_CALIBRATED_FOR_AUTOMATION"
            ),
            model=ModelMetadata(
                name="rule_incident_baseline",
                version=self.config.version,
                score_kind="normalized_heuristic_not_probability",
                taxonomy_version=self.config.taxonomy_version,
            ),
        )


class RuleBaselineDecisionModel:
    def __init__(
        self,
        incident_ranker: RuleIncidentRanker,
        feature_extractor: FeatureExtractor | None = None,
    ) -> None:
        self.incident_ranker = incident_ranker
        self.feature_extractor = feature_extractor

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        category = (
            LabelPrediction(
                label_id=request.report.category_hint,
                score=None,
                score_kind="unscored_hint",
                source="backend_or_fixture",
            )
            if request.report.category_hint
            else None
        )
        features = (
            self.feature_extractor.extract(request)
            if self.feature_extractor
            else ExtractedFeatures(
                missing_fields=("raw_address", "entrance", "floor", "duration", "danger_signals"),
                extractor_version="not-configured",
            )
        )
        return DecisionResponse(
            request_id=request.request_id,
            category=category,
            features=features,
            incident_ranking=self.incident_ranker.rank(request),
            organization_ranking=RankingResult(
                abstain_reason="TODO[backend]:organization-candidate-contract"
            ),
            action_ranking=RankingResult(abstain_reason="TODO[backend]:allowed-action-contract"),
            requires_manual_review=True,
            warnings=("RULE_BASELINE_IS_NOT_CALIBRATED",),
        )
