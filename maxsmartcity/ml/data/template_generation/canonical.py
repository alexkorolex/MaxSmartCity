"""Convert canonical scenario facts into grounded deterministic text seeds."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from maxsmartcity.ml.data.config import load_json_object, required_string
from maxsmartcity.ml.data.llm.models import ScenarioFact
from maxsmartcity.ml.data.template_generation.models import LocationScope, TemplateExample


@dataclass(frozen=True, slots=True)
class CanonicalSeedOverride:
    scenario_spec_id: str
    location_scope: LocationScope
    address_required: bool
    seed_texts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CanonicalSeedConfig:
    version: str
    building_object_types: tuple[str, ...]
    outdoor_subcategories: tuple[str, ...]
    overrides: tuple[CanonicalSeedOverride, ...]


def load_canonical_seed_config(path: Path) -> CanonicalSeedConfig:
    payload = load_json_object(path)
    raw_overrides = payload.get("overrides")
    if not isinstance(raw_overrides, list):
        msg = "canonical seed overrides must be a list"
        raise ValueError(msg)
    overrides = tuple(_parse_override(item) for item in raw_overrides)
    ids = [item.scenario_spec_id for item in overrides]
    if len(ids) != len(set(ids)):
        msg = "canonical seed override scenario ids must be unique"
        raise ValueError(msg)
    return CanonicalSeedConfig(
        version=required_string(payload, "version"),
        building_object_types=_string_tuple(payload, "building_object_types"),
        outdoor_subcategories=_string_tuple(payload, "outdoor_subcategories"),
        overrides=overrides,
    )


class CanonicalTemplateSeedGenerator:
    def __init__(self, config: CanonicalSeedConfig) -> None:
        self._config = config

    def generate(self, facts: tuple[ScenarioFact, ...]) -> tuple[TemplateExample, ...]:
        overrides = {item.scenario_spec_id: item for item in self._config.overrides}
        fact_ids = {fact.scenario_spec_id for fact in facts}
        unknown_overrides = set(overrides) - fact_ids
        if unknown_overrides:
            msg = f"seed overrides reference unknown facts: {sorted(unknown_overrides)}"
            raise ValueError(msg)
        curated_ids = {
            fact.scenario_spec_id for fact in facts if fact.source_dataset_id == "ml-data-curated-facts"
        }
        missing_overrides = curated_ids - set(overrides)
        if missing_overrides:
            msg = f"curated facts require explicit seed overrides: {sorted(missing_overrides)}"
            raise ValueError(msg)
        examples: list[TemplateExample] = []
        for fact in sorted(facts, key=lambda item: item.scenario_spec_id):
            override = overrides.get(fact.scenario_spec_id)
            if override is not None:
                examples.extend(self._override_examples(fact, override))
            else:
                examples.extend(self._automatic_examples(fact))
        return tuple(examples)

    def _override_examples(
        self,
        fact: ScenarioFact,
        override: CanonicalSeedOverride,
    ) -> tuple[TemplateExample, ...]:
        street = fact.street if override.address_required else ""
        house_number = fact.house_number if override.address_required else ""
        return tuple(
            self._example(
                fact,
                index,
                text.format(street=fact.street, house_number=fact.house_number),
                location_scope=override.location_scope,
                address_required=override.address_required,
                street=street,
                house_number=house_number,
                template_id=f"curated-override-{index + 1}",
            )
            for index, text in enumerate(override.seed_texts)
        )

    def _automatic_examples(self, fact: ScenarioFact) -> tuple[TemplateExample, ...]:
        address_required = fact.address_requirement == "REQUIRED"
        if not address_required:
            msg = f"non-curated fact unexpectedly forbids address: {fact.scenario_spec_id}"
            raise ValueError(msg)
        location_scope: LocationScope = (
            "OUTDOOR"
            if fact.subcategory_id in self._config.outdoor_subcategories
            else "BUILDING"
            if fact.object_type in self._config.building_object_types
            else "OUTDOOR"
        )
        problem = fact.problem.strip().rstrip(".!?")
        if "requires_verification" in fact.context_tags and not _has_uncertainty(problem):
            problem = f"предположительно {problem}"
        texts = (
            f"{fact.street}, дом {fact.house_number}: {problem}.",
            f"По адресу: {fact.street}, дом {fact.house_number}, {problem}.",
        )
        return tuple(
            self._example(
                fact,
                index,
                text,
                location_scope=location_scope,
                address_required=True,
                street=fact.street,
                house_number=fact.house_number,
                template_id=f"canonical-template-{index + 1}",
            )
            for index, text in enumerate(texts)
        )

    def _example(
        self,
        fact: ScenarioFact,
        index: int,
        text: str,
        *,
        location_scope: LocationScope,
        address_required: bool,
        street: str,
        house_number: str,
        template_id: str,
    ) -> TemplateExample:
        identity = f"{self._config.version}:{fact.scenario_spec_id}:{index}"
        return TemplateExample(
            example_id=f"CSEED-{hashlib.sha256(identity.encode()).hexdigest()[:16]}",
            config_version=self._config.version,
            frame_id=fact.scenario_spec_id,
            category_ids=fact.category_ids,
            subcategory_id=fact.subcategory_id,
            context_tags=fact.context_tags,
            danger_signals=fact.danger_signals,
            location_scope=location_scope,
            address_required=address_required,
            street=street,
            house_number=house_number,
            template_id=template_id,
            base_problem=fact.problem,
            text=text,
        )


def _parse_override(raw: object) -> CanonicalSeedOverride:
    if not isinstance(raw, dict):
        msg = "every canonical seed override must be an object"
        raise ValueError(msg)
    scope = raw.get("location_scope")
    if scope not in ("BUILDING", "OUTDOOR", "NONE"):
        msg = "override location_scope must be BUILDING, OUTDOOR or NONE"
        raise ValueError(msg)
    address_required = raw.get("address_required")
    if not isinstance(address_required, bool):
        msg = "override address_required must be a boolean"
        raise ValueError(msg)
    seed_texts = _string_tuple(raw, "seed_texts")
    if len(seed_texts) != 2:
        msg = "every canonical seed override must contain exactly two seed_texts"
        raise ValueError(msg)
    return CanonicalSeedOverride(
        scenario_spec_id=required_string(raw, "scenario_spec_id"),
        location_scope=cast(LocationScope, scope),
        address_required=address_required,
        seed_texts=seed_texts,
    )


def _string_tuple(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        msg = f"{key} must be a string list"
        raise ValueError(msg)
    return tuple(value)


def _has_uncertainty(text: str) -> bool:
    lowered = text.casefold()
    return any(marker in lowered for marker in ("предполож", "возмож", "похож", "кажется"))
