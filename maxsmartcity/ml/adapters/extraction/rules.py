"""Config-driven MVP extraction aligned with backend Report fields."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from maxsmartcity.ml.data.config import load_json_object, required_string
from maxsmartcity.ml.domain.requests import DecisionRequest
from maxsmartcity.ml.domain.results import ExtractedFeatures


@dataclass(frozen=True, slots=True)
class ExtractionRules:
    version: str
    address_patterns: tuple[str, ...]
    integer_fields: dict[str, tuple[str, ...]]
    duration_patterns: tuple[str, ...]
    number_words: dict[str, float]
    duration_units_seconds: dict[str, int]
    scale_hints: dict[str, tuple[str, ...]]
    danger_signals: dict[str, tuple[str, ...]]
    continues_true: tuple[str, ...]
    continues_false: tuple[str, ...]

    @classmethod
    def load(cls, path: Path) -> ExtractionRules:
        payload = load_json_object(path)
        continues = _object(payload, "problem_continues")
        return cls(
            version=required_string(payload, "version"),
            address_patterns=_strings(payload, "address_patterns"),
            integer_fields=_string_map(payload, "integer_fields"),
            duration_patterns=_strings(payload, "duration_patterns"),
            number_words=_number_map(payload, "number_words"),
            duration_units_seconds=_integer_map(payload, "duration_units_seconds"),
            scale_hints=_string_map(payload, "scale_hints"),
            danger_signals=_string_map(payload, "danger_signals"),
            continues_true=_strings(continues, "true"),
            continues_false=_strings(continues, "false"),
        )


class RuleFeatureExtractor:
    """Extract observable text features; never resolve canonical address IDs."""

    def __init__(self, rules: ExtractionRules) -> None:
        self._rules = rules

    @classmethod
    def from_path(cls, path: Path) -> RuleFeatureExtractor:
        return cls(ExtractionRules.load(path))

    def extract(self, request: DecisionRequest) -> ExtractedFeatures:
        text = request.report.text.strip()
        values: dict[str, object] = {}

        address = self._first_group(text, self._rules.address_patterns)
        if address:
            values["raw_address"] = address
        elif request.report.raw_address:
            values["raw_address"] = request.report.raw_address

        for field_name, patterns in self._rules.integer_fields.items():
            raw_value = self._first_group(text, patterns)
            if raw_value:
                values[field_name] = int(raw_value)

        duration = self._duration(text)
        if duration:
            values["duration"] = duration

        scale_hint = self._first_lexicon_match(text, self._rules.scale_hints)
        if scale_hint:
            values["scale_hint"] = scale_hint

        danger_signals = self._all_pattern_matches(text, self._rules.danger_signals)
        values["danger_signals"] = danger_signals

        continues = self._problem_continues(text)
        if continues is not None:
            values["problem_continues"] = continues

        missing = tuple(
            field for field in ("raw_address", "entrance", "floor", "duration") if field not in values
        )
        return ExtractedFeatures(
            values=values,
            missing_fields=missing,
            extractor_version=self._rules.version,
        )

    @staticmethod
    def _first_group(text: str, patterns: tuple[str, ...]) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group("value").strip(" ,.")
        return None

    def _duration(self, text: str) -> dict[str, object] | None:
        for pattern in self._rules.duration_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            amount_text = match.group("amount").lower()
            amount = (
                float(amount_text) if amount_text.isdigit() else self._rules.number_words.get(amount_text)
            )
            if amount is None:
                continue
            unit_text = match.group("unit").lower()
            unit_seconds = next(
                (
                    seconds
                    for prefix, seconds in self._rules.duration_units_seconds.items()
                    if unit_text.startswith(prefix)
                ),
                None,
            )
            if unit_seconds is None:
                continue
            return {
                "text": match.group(0),
                "seconds": int(amount * unit_seconds),
            }
        return None

    @staticmethod
    def _first_lexicon_match(text: str, lexicon: dict[str, tuple[str, ...]]) -> str | None:
        lowered = text.lower()
        for label, phrases in lexicon.items():
            if any(phrase.lower() in lowered for phrase in phrases):
                return label
        return None

    @staticmethod
    def _all_pattern_matches(text: str, lexicon: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
        return tuple(
            label
            for label, patterns in lexicon.items()
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
        )

    def _problem_continues(self, text: str) -> bool | None:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in self._rules.continues_false):
            return False
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in self._rules.continues_true):
            return True
        return None


def _object(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def _strings(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a string list")
    return tuple(value)


def _string_map(payload: dict[str, Any], key: str) -> dict[str, tuple[str, ...]]:
    value = _object(payload, key)
    return {name: _strings(value, name) for name in value}


def _number_map(payload: dict[str, Any], key: str) -> dict[str, float]:
    value = _object(payload, key)
    if not all(isinstance(item, int | float) for item in value.values()):
        raise ValueError(f"{key} values must be numbers")
    return {name: float(item) for name, item in value.items()}


def _integer_map(payload: dict[str, Any], key: str) -> dict[str, int]:
    value = _object(payload, key)
    if not all(isinstance(item, int) for item in value.values()):
        raise ValueError(f"{key} values must be integers")
    return {name: int(item) for name, item in value.items()}
