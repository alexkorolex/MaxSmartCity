"""Synthetic generator configuration."""

from dataclasses import dataclass
from pathlib import Path

from maxsmartcity.ml.data.config import (
    load_json_object,
    required_string,
    required_string_tuple,
)


@dataclass(frozen=True, slots=True)
class SyntheticArchetype:
    id: str
    category_id: str
    organization_id: str
    organization_type: str
    phrases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SyntheticConfig:
    version: str
    schema_version: int
    taxonomy_version: str
    city_id: str
    streets: tuple[str, ...]
    styles: tuple[str, ...]
    noise_phrases: tuple[str, ...]
    archetypes: tuple[SyntheticArchetype, ...]


def load_synthetic_config(path: Path) -> SyntheticConfig:
    payload = load_json_object(path)
    raw_archetypes = payload.get("archetypes")
    if not isinstance(raw_archetypes, list):
        msg = "synthetic.archetypes must be a list"
        raise ValueError(msg)
    archetypes: list[SyntheticArchetype] = []
    for raw in raw_archetypes:
        if not isinstance(raw, dict):
            msg = "every synthetic archetype must be an object"
            raise ValueError(msg)
        archetypes.append(
            SyntheticArchetype(
                id=required_string(raw, "id"),
                category_id=required_string(raw, "category_id"),
                organization_id=required_string(raw, "organization_id"),
                organization_type=required_string(raw, "organization_type"),
                phrases=required_string_tuple(raw, "phrases"),
            )
        )
    return SyntheticConfig(
        version=required_string(payload, "version"),
        schema_version=int(payload.get("schema_version", 1)),
        taxonomy_version=required_string(payload, "taxonomy_version"),
        city_id=required_string(payload, "city_id"),
        streets=required_string_tuple(payload, "streets"),
        styles=required_string_tuple(payload, "styles"),
        noise_phrases=required_string_tuple(payload, "noise_phrases"),
        archetypes=tuple(archetypes),
    )
