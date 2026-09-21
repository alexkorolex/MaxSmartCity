"""Versioned configuration for offline LLM augmentation."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from maxsmartcity.ml.data.config import load_json_object, required_string
from maxsmartcity.ml.data.llm.models import GenerationPass


@dataclass(frozen=True, slots=True)
class LlmGenerationConfig:
    version: str
    prompt_version: str
    prompt_file: Path
    model: str
    base_url: str
    timeout_seconds: float
    max_retries: int
    max_output_tokens: int
    top_p: float
    min_text_length: int
    max_text_length: int
    forbidden_terms: tuple[str, ...]
    input_rubles_per_million: float
    output_rubles_per_million: float
    passes: tuple[GenerationPass, ...]
    pilot_scenario_ids: tuple[str, ...]


def load_llm_generation_config(path: Path) -> LlmGenerationConfig:
    payload = load_json_object(path)
    validation = _required_object(payload, "validation")
    pricing = _required_object(payload, "pricing_rub_per_million_tokens")
    raw_passes = payload.get("passes")
    pilot_ids = payload.get("pilot_scenario_ids")
    if not isinstance(raw_passes, list) or not raw_passes:
        msg = "llm generation passes must be a non-empty list"
        raise ValueError(msg)
    if (
        not isinstance(pilot_ids, list)
        or not pilot_ids
        or not all(isinstance(item, str) and item for item in pilot_ids)
    ):
        msg = "pilot_scenario_ids must be a non-empty string list"
        raise ValueError(msg)
    passes = tuple(_parse_pass(item) for item in raw_passes)
    pass_ids = [item.id for item in passes]
    if len(pass_ids) != len(set(pass_ids)):
        msg = "llm generation pass ids must be unique"
        raise ValueError(msg)
    return LlmGenerationConfig(
        version=required_string(payload, "version"),
        prompt_version=required_string(payload, "prompt_version"),
        prompt_file=Path(required_string(payload, "prompt_file")),
        model=required_string(payload, "model"),
        base_url=required_string(payload, "base_url"),
        timeout_seconds=_positive_number(payload, "timeout_seconds"),
        max_retries=_nonnegative_int(payload, "max_retries"),
        max_output_tokens=_positive_int(payload, "max_output_tokens"),
        top_p=_probability(payload, "top_p"),
        min_text_length=_positive_int(validation, "min_text_length"),
        max_text_length=_positive_int(validation, "max_text_length"),
        forbidden_terms=_string_tuple(validation, "forbidden_terms"),
        input_rubles_per_million=_positive_number(pricing, "input"),
        output_rubles_per_million=_positive_number(pricing, "output"),
        passes=passes,
        pilot_scenario_ids=tuple(pilot_ids),
    )


def _parse_pass(raw: object) -> GenerationPass:
    if not isinstance(raw, dict):
        msg = "every generation pass must be an object"
        raise ValueError(msg)
    return GenerationPass(
        id=required_string(raw, "id"),
        temperature=_probability(raw, "temperature"),
        variants_per_scenario=_positive_int(raw, "variants_per_scenario"),
        styles=_string_tuple(raw, "styles"),
        source_dataset_ids=_string_tuple(raw, "source_dataset_ids"),
    )


def _required_object(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        msg = f"{key} must be an object"
        raise ValueError(msg)
    return value


def _string_tuple(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item for item in value)
    ):
        msg = f"{key} must be a non-empty string list"
        raise ValueError(msg)
    return tuple(value)


def _positive_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        msg = f"{key} must be a positive integer"
        raise ValueError(msg)
    return value


def _nonnegative_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        msg = f"{key} must be a non-negative integer"
        raise ValueError(msg)
    return value


def _positive_number(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool) or value <= 0:
        msg = f"{key} must be a positive number"
        raise ValueError(msg)
    return float(value)


def _probability(payload: dict[str, Any], key: str) -> float:
    value = _positive_number(payload, key)
    if value > 1:
        msg = f"{key} must be in the interval (0, 1]"
        raise ValueError(msg)
    return value
