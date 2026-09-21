"""Migrate reviewed v1 report texts to backend-aligned v2 annotation candidates."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from maxsmartcity.ml.data.config import load_json_object, required_string


@dataclass(frozen=True, slots=True)
class GoldV2MigrationConfig:
    version: str
    annotation_version: str
    taxonomy_version: str
    primary_categories: frozenset[str]
    routing_labels: dict[str, str]
    routing_overrides: dict[str, str]
    danger_aliases: dict[str, str]
    secondary_category_priority: tuple[str, ...]

    @classmethod
    def load(cls, path: Path) -> GoldV2MigrationConfig:
        payload = load_json_object(path)
        return cls(
            version=required_string(payload, "version"),
            annotation_version=required_string(payload, "annotation_version"),
            taxonomy_version=required_string(payload, "taxonomy_version"),
            primary_categories=frozenset(_strings(payload, "primary_categories")),
            routing_labels=_string_map(payload, "routing_labels"),
            routing_overrides=_string_map(payload, "routing_overrides"),
            danger_aliases=_string_map(payload, "danger_aliases"),
            secondary_category_priority=_strings(payload, "secondary_category_priority"),
        )


class GoldV2Migrator:
    """Perform a conservative label migration; transformed records require renewed review."""

    def __init__(self, config: GoldV2MigrationConfig) -> None:
        self._config = config

    def migrate(self, record: dict[str, Any]) -> dict[str, Any]:
        category_ids = _strings(record, "category_ids")
        scenario_id = required_string(record, "scenario_spec_id")
        routing_outcome = self._routing_outcome(category_ids, scenario_id)
        primary_category = self._primary_category(category_ids, routing_outcome)
        danger_signals = self._danger_signals(_strings(record, "danger_signals"))
        source = required_string(record, "source")
        example_id = required_string(record, "example_id")
        return {
            "record_id": f"GOLDV2-{_short_hash(example_id)}",
            "scenario_id": scenario_id,
            "text": required_string(record, "text"),
            "subcategory_ids": list(_strings(record, "subcategory_ids")),
            "ambiguity": _boolean(record, "ambiguity"),
            "primary_category": primary_category,
            "routing_outcome": routing_outcome,
            "danger_signals": list(danger_signals),
            "extracted_features": {},
            "provenance": {
                "source_kind": source,
                "parent_record_id": example_id,
                "generator_model": None,
                "prompt_version": None,
            },
            "review_status": "CANDIDATE",
            "notes": "Automatically migrated from Gold v1; requires v2 semantic review.",
        }

    def _routing_outcome(self, category_ids: tuple[str, ...], scenario_id: str) -> str:
        override = self._config.routing_overrides.get(scenario_id)
        if override is not None:
            return override
        outcomes = {
            outcome for label, outcome in self._config.routing_labels.items() if label in category_ids
        }
        if len(outcomes) > 1:
            msg = f"conflicting routing labels: {sorted(outcomes)}"
            raise ValueError(msg)
        return next(iter(outcomes), "ACCEPT")

    def _primary_category(self, category_ids: tuple[str, ...], routing_outcome: str) -> str | None:
        if routing_outcome != "ACCEPT":
            return None
        candidates = [item for item in category_ids if item in self._config.primary_categories]
        if len(candidates) == 1:
            return candidates[0]
        for secondary in self._config.secondary_category_priority:
            if secondary in candidates and len(candidates) > 1:
                candidates.remove(secondary)
        if len(candidates) != 1:
            msg = f"cannot select one primary category from {category_ids}"
            raise ValueError(msg)
        return candidates[0]

    def _danger_signals(self, signals: tuple[str, ...]) -> tuple[str, ...]:
        unknown = set(signals) - set(self._config.danger_aliases)
        if unknown:
            msg = f"danger aliases are missing for: {sorted(unknown)}"
            raise ValueError(msg)
        return tuple(dict.fromkeys(self._config.danger_aliases[item] for item in signals))


class GoldV2Writer:
    def write(
        self,
        *,
        source_dir: Path,
        output_dir: Path,
        migrator: GoldV2Migrator,
        config: GoldV2MigrationConfig,
        config_path: Path,
    ) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, dict[str, Any]] = {}
        all_records: list[dict[str, Any]] = []
        split_scenarios: dict[str, set[str]] = {}
        for filename in ("train.jsonl", "validation.jsonl", "test.jsonl"):
            source_records = _read_jsonl(source_dir / filename)
            records = [migrator.migrate(record) for record in source_records]
            all_records.extend(records)
            split_scenarios[filename] = {str(record["scenario_id"]) for record in records}
            files[filename] = _write_jsonl(output_dir / filename, records)
        _assert_split_isolation(split_scenarios)
        files["reports.jsonl"] = _write_jsonl(
            output_dir / "reports.jsonl",
            sorted(all_records, key=lambda item: str(item["record_id"])),
        )
        manifest = {
            "dataset_version": "gold-v2-migration-candidates-v1",
            "annotation_version": config.annotation_version,
            "taxonomy_version": config.taxonomy_version,
            "status": "CANDIDATE_REQUIRES_V2_SEMANTIC_REVIEW",
            "record_count": len(all_records),
            "scenario_count": len({str(item["scenario_id"]) for item in all_records}),
            "routing_counts": _counts(all_records, "routing_outcome"),
            "primary_category_counts": _counts(all_records, "primary_category"),
            "files": files,
            "inputs": {
                str(config_path).replace("\\", "/"): _hash_file(config_path),
                str(source_dir / "manifest.json").replace("\\", "/"): _hash_file(
                    source_dir / "manifest.json"
                ),
            },
            "limitations": [
                "Labels were deterministically migrated from Gold v1.",
                "Extracted feature targets are intentionally empty pending human annotation.",
                "No record is FROZEN; v2 semantic review is mandatory.",
            ],
        }
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return manifest


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not all(isinstance(record, dict) for record in records):
        msg = f"non-object record in {path}"
        raise ValueError(msg)
    return records


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    content = "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)
    path.write_text(content, encoding="utf-8", newline="\n")
    return {"record_count": len(records), "sha256": hashlib.sha256(content.encode()).hexdigest()}


def _assert_split_isolation(splits: dict[str, set[str]]) -> None:
    values = list(splits.values())
    if values[0] & values[1] or values[0] & values[2] or values[1] & values[2]:
        msg = "scenario leakage detected while migrating Gold v2"
        raise ValueError(msg)


def _counts(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for record in records:
        value = str(record[key])
        values[value] = values.get(value, 0) + 1
    return dict(sorted(values.items()))


def _strings(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        msg = f"{key} must be a string list"
        raise ValueError(msg)
    return tuple(value)


def _string_map(payload: dict[str, Any], key: str) -> dict[str, str]:
    value = payload.get(key)
    if not isinstance(value, dict) or not all(
        isinstance(name, str) and isinstance(item, str) for name, item in value.items()
    ):
        msg = f"{key} must map strings to strings"
        raise ValueError(msg)
    return value


def _boolean(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean"
        raise ValueError(msg)
    return value


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
