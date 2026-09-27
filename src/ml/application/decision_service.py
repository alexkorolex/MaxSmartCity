"""Model orchestration, allow-list validation and graceful fallback."""

from src.ml.domain.requests import DecisionRequest
from src.ml.domain.results import DecisionResponse, validate_allowed_candidates
from src.ml.ports.models import ComponentUnavailableError, DecisionModel


class DecisionService:
    """Run the configured model and validate that it cannot escape Backend allow-lists.

    A component failure switches to the deterministic fallback. Domain or contract errors
    are deliberately not swallowed because accepting an invalid recommendation would be
    less safe than returning an explicit API error.
    """

    def __init__(self, primary: DecisionModel, fallback: DecisionModel) -> None:
        self.primary = primary
        self.fallback = fallback

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        """Return one validated recommendation without changing Backend state."""

        try:
            response = self.primary.decide(request)
        except ComponentUnavailableError:
            response = self.fallback.decide(request)
        validate_allowed_candidates(request, response)
        return response
