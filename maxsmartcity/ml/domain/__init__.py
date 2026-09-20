"""Stable domain objects shared by ML application services and adapters."""

from maxsmartcity.ml.domain.requests import (
    ActionCandidate,
    DecisionRequest,
    IncidentCandidate,
    OrganizationCandidate,
    ReportInput,
)
from maxsmartcity.ml.domain.results import DecisionResponse

__all__ = [
    "ActionCandidate",
    "DecisionRequest",
    "DecisionResponse",
    "IncidentCandidate",
    "OrganizationCandidate",
    "ReportInput",
]
