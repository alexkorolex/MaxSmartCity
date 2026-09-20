"""Model orchestration, allow-list validation and graceful fallback."""

from maxsmartcity.ml.domain.requests import DecisionRequest
from maxsmartcity.ml.domain.results import DecisionResponse, validate_allowed_candidates
from maxsmartcity.ml.ports.models import ComponentUnavailableError, DecisionModel


class DecisionService:
    def __init__(self, primary: DecisionModel, fallback: DecisionModel) -> None:
        self.primary = primary
        self.fallback = fallback

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        try:
            response = self.primary.decide(request)
        except ComponentUnavailableError:
            response = self.fallback.decide(request)
        validate_allowed_candidates(request, response)
        return response
