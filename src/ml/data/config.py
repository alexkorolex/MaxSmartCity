"""Load versioned, data-driven ML configuration."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class TaxonomyEntry:
    id: str
    title: str
    parent_id: str | None = None


@dataclass(frozen=True, slots=True)
class TaxonomyConfig:
    version: str
    categories: tuple[TaxonomyEntry, ...]

    @property
    def category_ids(self) -> frozenset[str]:
        return frozenset(item.id for item in self.categories)


@dataclass(frozen=True, slots=True)
class RuleBaselineConfig:
    version: str
    taxonomy_version: str
    same_location_weight: float
    same_category_weight: float
    close_in_time_weight: float
    inactive_penalty: float
    close_in_time_seconds: int
    automation_enabled: bool


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"configuration must be a JSON object: {path}"
        raise ValueError(msg)
    return payload


def load_taxonomy(path: Path) -> TaxonomyConfig:
    payload = load_json_object(path)
    raw_categories = payload.get("categories")
    if not isinstance(raw_categories, list):
        msg = "taxonomy.categories must be a list"
        raise ValueError(msg)
    categories: list[TaxonomyEntry] = []
    for item in raw_categories:
        if not isinstance(item, dict):
            msg = "each taxonomy category must be an object"
            raise ValueError(msg)
        categories.append(
            TaxonomyEntry(
                id=required_string(item, "id"),
                title=required_string(item, "title"),
                parent_id=item.get("parent_id"),
            )
        )
    ids = [item.id for item in categories]
    if len(ids) != len(set(ids)):
        msg = "taxonomy category ids must be unique"
        raise ValueError(msg)
    return TaxonomyConfig(
        version=required_string(payload, "version"),
        categories=tuple(categories),
    )


def load_rule_baseline(path: Path) -> RuleBaselineConfig:
    payload = load_json_object(path)
    weights = payload.get("weights")
    if not isinstance(weights, dict):
        msg = "rule baseline weights must be an object"
        raise ValueError(msg)
    return RuleBaselineConfig(
        version=required_string(payload, "version"),
        taxonomy_version=required_string(payload, "taxonomy_version"),
        same_location_weight=required_number(weights, "same_location"),
        same_category_weight=required_number(weights, "same_category"),
        close_in_time_weight=required_number(weights, "close_in_time"),
        inactive_penalty=required_number(weights, "inactive_penalty"),
        close_in_time_seconds=int(required_number(payload, "close_in_time_seconds")),
        automation_enabled=bool(payload.get("automation_enabled", False)),
    )


def required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        msg = f"{key} must be a non-empty string"
        raise ValueError(msg)
    return value


def required_number(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, int | float):
        msg = f"{key} must be a number"
        raise ValueError(msg)
    return float(value)


def required_string_tuple(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        msg = f"{key} must be a non-empty string list"
        raise ValueError(msg)
    return tuple(value)
