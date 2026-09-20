from datetime import UTC, datetime

import pytest

from maxsmartcity.ml.application.decision_service import DecisionService
from maxsmartcity.ml.domain.requests import DecisionRequest, IncidentCandidate, ReportInput
from maxsmartcity.ml.domain.results import (
    DecisionResponse,
    ExtractedFeatures,
    RankingResult,
    ScoredCandidate,
    validate_allowed_candidates,
)
from maxsmartcity.ml.ports.models import ComponentUnavailableError


class UnavailableModel:
    def decide(self, request: DecisionRequest) -> DecisionResponse:
        del request
        raise ComponentUnavailableError


class AbstainingFallback:
    def decide(self, request: DecisionRequest) -> DecisionResponse:
        return DecisionResponse(
            request_id=request.request_id,
            category=None,
            features=ExtractedFeatures(),
        )


def make_request() -> DecisionRequest:
    return DecisionRequest(
        request_id="REQ-1",
        report=ReportInput("REP-1", "текст", datetime(2026, 9, 20, tzinfo=UTC)),
        incident_candidates=(IncidentCandidate("INC-ALLOWED", datetime(2026, 9, 20, tzinfo=UTC)),),
    )


def test_unavailable_primary_uses_abstaining_fallback() -> None:
    response = DecisionService(UnavailableModel(), AbstainingFallback()).decide(make_request())

    assert response.requires_manual_review is True


def test_forbidden_candidate_is_rejected() -> None:
    request = make_request()
    response = DecisionResponse(
        request_id=request.request_id,
        category=None,
        features=ExtractedFeatures(),
        incident_ranking=RankingResult(
            candidates=(ScoredCandidate("INC-INVENTED", 0.99),),
            abstain=False,
            abstain_reason=None,
        ),
    )

    with pytest.raises(ValueError, match="forbidden candidate"):
        validate_allowed_candidates(request, response)
