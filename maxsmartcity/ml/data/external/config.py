"""Configuration for building canonical scenarios from external datasets."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from maxsmartcity.ml.data.config import (
    load_json_object,
    required_string,
    required_string_tuple,
)


@dataclass(frozen=True, slots=True)
class CuratedScenario:
    id: str
    category_ids: tuple[str, ...]
    subcategory_id: str
    problem: str
    object_type: str
    severity: str
    organization_type: str | None
    context_tags: tuple[str, ...]
    danger_signals: tuple[str, ...]
    needs_clarification: bool
    ambiguity: bool


@dataclass(frozen=True, slots=True)
class ExternalBuildConfig:
    version: str
    schema_version: str
    taxonomy_version: str
    city_id: str
    seed: int
    sf311_limit: int
    bmc_limit: int
    streets: tuple[str, ...]
    curated: tuple[CuratedScenario, ...]

    @property
    def expected_scenario_count(self) -> int:
        return self.sf311_limit + self.bmc_limit + len(self.curated)


def load_external_build_config(path: Path) -> ExternalBuildConfig:
    payload = load_json_object(path)
    limits = payload.get("source_limits")
    raw_curated = payload.get("curated_scenarios")
    if not isinstance(limits, dict):
        msg = "external source_limits must be an object"
        raise ValueError(msg)
    if not isinstance(raw_curated, list):
        msg = "external curated_scenarios must be a list"
        raise ValueError(msg)
    curated = tuple(_parse_curated(item) for item in raw_curated)
    curated_ids = [item.id for item in curated]
    if len(curated_ids) != len(set(curated_ids)):
        msg = "curated scenario ids must be unique"
        raise ValueError(msg)
    return ExternalBuildConfig(
        version=required_string(payload, "version"),
        schema_version=required_string(payload, "schema_version"),
        taxonomy_version=required_string(payload, "taxonomy_version"),
        city_id=required_string(payload, "city_id"),
        seed=int(payload.get("seed", 42)),
        sf311_limit=_positive_int(limits, "sf311"),
        bmc_limit=_positive_int(limits, "bmc"),
        streets=required_string_tuple(payload, "streets"),
        curated=curated,
    )


def _parse_curated(raw: object) -> CuratedScenario:
    if not isinstance(raw, dict):
        msg = "every curated scenario must be an object"
        raise ValueError(msg)
    organization_type = raw.get("organization_type")
    if organization_type is not None and not isinstance(organization_type, str):
        msg = "curated organization_type must be a string or null"
        raise ValueError(msg)
    return CuratedScenario(
        id=required_string(raw, "id"),
        category_ids=required_string_tuple(raw, "category_ids"),
        subcategory_id=required_string(raw, "subcategory_id"),
        problem=required_string(raw, "problem"),
        object_type=required_string(raw, "object_type"),
        severity=required_string(raw, "severity"),
        organization_type=organization_type,
        context_tags=_optional_string_tuple(raw, "context_tags"),
        danger_signals=_optional_string_tuple(raw, "danger_signals"),
        needs_clarification=bool(raw.get("needs_clarification", False)),
        ambiguity=bool(raw.get("ambiguity", False)),
    )


def _optional_string_tuple(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        msg = f"{key} must be a string list"
        raise ValueError(msg)
    return tuple(value)


def _positive_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        msg = f"{key} must be a positive integer"
        raise ValueError(msg)
    return value
