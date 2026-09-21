"""Read locked canonical facts for lexicalization."""

import json
from pathlib import Path
from typing import Any

from maxsmartcity.ml.data.llm.models import ScenarioFact


def load_scenario_facts(path: Path) -> tuple[ScenarioFact, ...]:
    facts = tuple(
        _parse_fact(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    ids = [fact.scenario_spec_id for fact in facts]
    if len(ids) != len(set(ids)):
        msg = "canonical scenario ids must be unique"
        raise ValueError(msg)
    return facts


def _parse_fact(raw: dict[str, Any]) -> ScenarioFact:
    location = _object(raw, "location")
    source = _object(raw, "source")
    source_attributes = _object(raw, "source_attributes")
    return ScenarioFact(
        scenario_spec_id=_string(raw, "scenario_spec_id"),
        taxonomy_version=_string(raw, "taxonomy_version"),
        category_ids=_strings(raw, "category_ids"),
        subcategory_id=_string(raw, "subcategory_id"),
        problem=_string(raw, "problem"),
        object_type=_string(raw, "object_type"),
        severity=_string(raw, "severity"),
        organization_type=_optional_string(raw, "organization_type"),
        street=_string(location, "street"),
        house_number=_string(location, "house_number"),
        source_dataset_id=_string(source, "dataset_id"),
        source_attributes=tuple(sorted((str(key), str(value)) for key, value in source_attributes.items())),
        context_tags=_strings(raw, "context_tags", allow_empty=True),
        danger_signals=_strings(raw, "danger_signals", allow_empty=True),
        needs_clarification=_boolean(raw, "needs_clarification"),
        ambiguity=_boolean(raw, "ambiguity"),
    )


def _object(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        msg = f"canonical {key} must be an object"
        raise ValueError(msg)
    return value


def _string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        msg = f"canonical {key} must be a non-empty string"
        raise ValueError(msg)
    return value


def _optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is not None and not isinstance(value, str):
        msg = f"canonical {key} must be a string or null"
        raise ValueError(msg)
    return value


def _strings(payload: dict[str, Any], key: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    value = payload.get(key)
    if (
        not isinstance(value, list)
        or (not value and not allow_empty)
        or not all(isinstance(item, str) and item for item in value)
    ):
        msg = f"canonical {key} must be a string list"
        raise ValueError(msg)
    return tuple(value)


def _boolean(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        msg = f"canonical {key} must be a boolean"
        raise ValueError(msg)
    return value
