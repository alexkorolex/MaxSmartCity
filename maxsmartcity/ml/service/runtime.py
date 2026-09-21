"""Runtime assembly and wire/domain conversion for the ML HTTP service."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from maxsmartcity.ml.adapters.baselines import RuleBaselineDecisionModel, RuleIncidentRanker
from maxsmartcity.ml.adapters.extraction import RuleFeatureExtractor
from maxsmartcity.ml.application.decision_service import DecisionService
from maxsmartcity.ml.application.input_policy import InputPolicy
from maxsmartcity.ml.data.config import load_rule_baseline
from maxsmartcity.ml.domain.requests import (
    ActionCandidate,
    DecisionRequest,
    IncidentCandidate,
    OrganizationCandidate,
    ReportInput,
)
from maxsmartcity.ml.domain.results import CONTRACT_VERSION, DecisionResponse, ModelMetadata
from maxsmartcity.ml.inference.category import CategoryArtifact, CategoryPrediction
from maxsmartcity.ml.inference.decision import ArtifactDecisionModel


class RequestValidationError(ValueError):
    """A stable transport error produced before model inference."""


class MLRuntime:
    def __init__(
        self,
        *,
        category: CategoryArtifact | None,
        artifact_error: str | None,
        decision_service: DecisionService,
        model_metadata: tuple[ModelMetadata, ...],
        max_input_characters: int,
    ) -> None:
        self.category = category
        self.artifact_error = artifact_error
        self.decision_service = decision_service
        self.model_metadata = model_metadata
        self.input_policy = InputPolicy(max_input_characters)

    @classmethod
    def load(
        cls,
        *,
        artifact_dir: Path,
        rule_config_path: Path,
        extraction_config_path: Path,
        max_input_characters: int = 4_000,
    ) -> MLRuntime:
        rule_ranker = RuleIncidentRanker(load_rule_baseline(rule_config_path))
        extractor = RuleFeatureExtractor.from_path(extraction_config_path)
        fallback = RuleBaselineDecisionModel(rule_ranker, extractor)
        try:
            category = CategoryArtifact.load(artifact_dir)
            primary = ArtifactDecisionModel(category, rule_ranker, extractor)
            error = None
            metadata = (primary.metadata,)
        except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
            category = None
            primary = fallback
            error = f"CATEGORY_ARTIFACT_UNAVAILABLE:{type(exc).__name__}"
            metadata = ()
        return cls(
            category=category,
            artifact_error=error,
            decision_service=DecisionService(primary, fallback),
            model_metadata=metadata,
            max_input_characters=max_input_characters,
        )

    @property
    def ready(self) -> bool:
        return self.category is not None

    def classify(self, text: str, top_k: int) -> tuple[CategoryPrediction, bool]:
        if self.category is None:
            raise RuntimeError(self.artifact_error or "CATEGORY_ARTIFACT_UNAVAILABLE")
        if top_k < 1 or top_k > 20:
            raise RequestValidationError("top_k must be between 1 and 20")
        truncated = len(text) > self.input_policy.max_characters
        bounded_text = text[: self.input_policy.max_characters]
        return self.category.predict(bounded_text, top_k), truncated

    def decide(self, payload: dict[str, Any]) -> DecisionResponse:
        request = parse_decision_request(payload)
        bounded, truncated = self.input_policy.apply(request)
        response = self.decision_service.decide(bounded)
        return replace(response, input_truncated=truncated)


def parse_decision_request(payload: Mapping[str, Any]) -> DecisionRequest:
    _require_contract(payload)
    report_payload = _mapping(payload, "report")
    report = ReportInput(
        report_id=_string(report_payload, "report_id"),
        text=_string(report_payload, "text", allow_empty=True),
        created_at=_datetime(report_payload, "created_at"),
        address_id=_optional_string(report_payload, "address_id"),
        house_id=_optional_string(report_payload, "house_id"),
        raw_address=_optional_string(report_payload, "raw_address"),
        fias_guid=_optional_string(report_payload, "fias_guid"),
        category_hint=_optional_string(report_payload, "category_hint"),
    )
    incidents = tuple(
        IncidentCandidate(
            id=_string(item, "id"),
            started_at=_datetime(item, "started_at"),
            category_id=_optional_string(item, "category_id"),
            affected_house_ids=_string_tuple(item, "affected_house_ids"),
            fias_guids=_string_tuple(item, "fias_guids"),
            title=_string(item, "title", allow_empty=True),
            status=_string(item, "status"),
            priority=_string(item, "priority"),
            active=_boolean(item, "active"),
        )
        for item in _mapping_list(payload, "candidate_incidents")
    )
    organizations = tuple(
        OrganizationCandidate(id=_string(item, "id"), attributes=_string_dict(item, "attributes"))
        for item in _mapping_list(payload, "candidate_organizations")
    )
    actions = tuple(
        ActionCandidate(id=_string(item, "id"), attributes=_string_dict(item, "attributes"))
        for item in _mapping_list(payload, "allowed_actions")
    )
    external_context = payload.get("external_context", {})
    if not isinstance(external_context, dict):
        raise RequestValidationError("external_context must be an object")
    return DecisionRequest(
        request_id=_string(payload, "request_id"),
        report=report,
        incident_candidates=incidents,
        organization_candidates=organizations,
        action_candidates=actions,
        external_context=dict(external_context),
    )


def decision_response_to_dict(response: DecisionResponse) -> dict[str, Any]:
    return asdict(response)


def metadata_to_dict(metadata: ModelMetadata) -> dict[str, Any]:
    return asdict(metadata)


def _require_contract(payload: Mapping[str, Any]) -> None:
    if payload.get("contract_version") != CONTRACT_VERSION:
        raise RequestValidationError(f"contract_version must equal {CONTRACT_VERSION}")


def _mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise RequestValidationError(f"{key} must be an object")
    return value


def _mapping_list(payload: Mapping[str, Any], key: str) -> tuple[Mapping[str, Any], ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise RequestValidationError(f"{key} must be an array of objects")
    return tuple(value)


def _string(payload: Mapping[str, Any], key: str, *, allow_empty: bool = False) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or (not allow_empty and not value):
        raise RequestValidationError(f"{key} must be a string")
    return value


def _optional_string(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise RequestValidationError(f"{key} must be a string or null")
    return value


def _datetime(payload: Mapping[str, Any], key: str) -> datetime:
    raw = _string(payload, key)
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RequestValidationError(f"{key} must be an ISO 8601 date-time") from exc
    if value.tzinfo is None:
        raise RequestValidationError(f"{key} must include a timezone")
    return value


def _string_tuple(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RequestValidationError(f"{key} must be an array of strings")
    return tuple(value)


def _string_dict(payload: Mapping[str, Any], key: str) -> dict[str, str]:
    value = _mapping(payload, key)
    if not all(isinstance(item, str) for item in value.values()):
        raise RequestValidationError(f"{key} values must be strings")
    return dict(value)  # type: ignore[arg-type]


def _boolean(payload: Mapping[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise RequestValidationError(f"{key} must be a boolean")
    return value
