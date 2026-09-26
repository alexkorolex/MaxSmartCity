"""Dependency placeholders with an owner in every TODO."""

from typing import Never

from src.ml.domain.requests import DecisionRequest
from src.ml.domain.results import DecisionResponse
from src.ml.ports.models import ComponentUnavailableError


class AwaitingBackendContextProvider:
    """TODO[backend]: provide allowed incidents, organizations, actions and policy context."""

    def enrich(self, request: DecisionRequest) -> Never:
        del request
        raise ComponentUnavailableError("awaiting backend candidate contract")


class AwaitingIngestionContextProvider:
    """TODO[ingestion]: provide FIAS, organizations and versioned external events."""

    def enrich(self, request: DecisionRequest) -> Never:
        del request
        raise ComponentUnavailableError("awaiting ingestion dataset export")


class UntrainedDecisionModel:
    """TODO[model]: train only after synthetic and Gold datasets are validated."""

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        del request
        raise ComponentUnavailableError("no validated trained decision artifact")
