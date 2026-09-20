"""Replaceable model interfaces."""

from collections.abc import Sequence
from typing import Protocol

from maxsmartcity.ml.domain.requests import DecisionRequest
from maxsmartcity.ml.domain.results import (
    DecisionResponse,
    ExtractedFeatures,
    LabelPrediction,
    RankingResult,
)


class ComponentUnavailableError(RuntimeError):
    """A model or upstream integration is not configured or temporarily unavailable."""


class DecisionModel(Protocol):
    def decide(self, request: DecisionRequest) -> DecisionResponse: ...


class CategoryPredictor(Protocol):
    def predict(self, request: DecisionRequest) -> LabelPrediction | None: ...


class FeatureExtractor(Protocol):
    def extract(self, request: DecisionRequest) -> ExtractedFeatures: ...


class IncidentRanker(Protocol):
    def rank(self, request: DecisionRequest) -> RankingResult: ...


class TextPairModel(Protocol):
    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> Sequence[float]: ...
