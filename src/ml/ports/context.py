"""Interfaces owned by backend and ingestion adapters."""

from typing import Protocol

from src.ml.domain.requests import DecisionRequest


class CandidateContextProvider(Protocol):
    def enrich(self, request: DecisionRequest) -> DecisionRequest: ...
