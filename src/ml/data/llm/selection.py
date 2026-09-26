"""Deterministic, quota-based selection of canonical facts for LLM generation."""

import hashlib
import json
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.ml.data.config import load_json_object, required_string
from src.ml.data.llm.models import ScenarioFact


@dataclass(frozen=True, slots=True)
class SelectionQuota:
    source_dataset_id: str
    category_id: str
    count: int


@dataclass(frozen=True, slots=True)
class SelectionConfig:
    version: str
    seed: str
    include_all_source_dataset_ids: tuple[str, ...]
    exclude_scenario_ids: tuple[str, ...]
    quotas: tuple[SelectionQuota, ...]


def load_selection_config(path: Path) -> SelectionConfig:
    payload = load_json_object(path)
    include_all = _string_tuple(payload, "include_all_source_dataset_ids")
    raw_quotas = payload.get("quotas")
    if not isinstance(raw_quotas, list) or not raw_quotas:
        msg = "selection quotas must be a non-empty list"
        raise ValueError(msg)
    quotas = tuple(_parse_quota(item) for item in raw_quotas)
    keys = [(item.source_dataset_id, item.category_id) for item in quotas]
    if len(keys) != len(set(keys)):
        msg = "selection quota source/category pairs must be unique"
        raise ValueError(msg)
    return SelectionConfig(
        version=required_string(payload, "version"),
        seed=required_string(payload, "seed"),
        include_all_source_dataset_ids=include_all,
        exclude_scenario_ids=_optional_string_tuple(payload, "exclude_scenario_ids"),
        quotas=quotas,
    )


def select_facts(
    facts: tuple[ScenarioFact, ...],
    config: SelectionConfig,
) -> tuple[ScenarioFact, ...]:
    selected: dict[str, ScenarioFact] = {
        fact.scenario_spec_id: fact
        for fact in facts
        if fact.source_dataset_id in config.include_all_source_dataset_ids
        and fact.scenario_spec_id not in config.exclude_scenario_ids
    }
    for quota in config.quotas:
        candidates = tuple(
            fact
            for fact in facts
            if fact.source_dataset_id == quota.source_dataset_id
            and fact.category_ids
            and fact.category_ids[0] == quota.category_id
        )
        chosen = _diverse_sample(candidates, quota.count, config.seed)
        for fact in chosen:
            if fact.scenario_spec_id in selected:
                msg = f"selection contains duplicate scenario: {fact.scenario_spec_id}"
                raise ValueError(msg)
            selected[fact.scenario_spec_id] = fact
    return tuple(selected[key] for key in sorted(selected))


def build_selection_manifest(
    selected: tuple[ScenarioFact, ...],
    *,
    config: SelectionConfig,
    canonical_path: Path,
) -> dict[str, Any]:
    scenario_ids = [fact.scenario_spec_id for fact in selected]
    source_counts = Counter(fact.source_dataset_id for fact in selected)
    category_counts = Counter(fact.category_ids[0] for fact in selected)
    subcategory_counts = Counter(fact.subcategory_id for fact in selected)
    return {
        "schema_version": "llm-scenario-selection-v1",
        "selection_version": config.version,
        "seed": config.seed,
        "canonical_input": {
            "name": canonical_path.name,
            "sha256": hashlib.sha256(canonical_path.read_bytes()).hexdigest(),
        },
        "scenario_count": len(selected),
        "scenario_ids": scenario_ids,
        "selection_sha256": hashlib.sha256("\n".join(scenario_ids).encode()).hexdigest(),
        "counts": {
            "source_dataset_ids": dict(sorted(source_counts.items())),
            "primary_category_ids": dict(sorted(category_counts.items())),
            "subcategory_ids": dict(sorted(subcategory_counts.items())),
        },
        "quotas": [
            {
                "source_dataset_id": quota.source_dataset_id,
                "category_id": quota.category_id,
                "count": quota.count,
            }
            for quota in config.quotas
        ],
    }


def write_selection_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def load_selection_ids(path: Path) -> tuple[str, ...]:
    payload = load_json_object(path)
    scenario_ids = payload.get("scenario_ids")
    if (
        not isinstance(scenario_ids, list)
        or not scenario_ids
        or not all(isinstance(item, str) and item for item in scenario_ids)
    ):
        msg = f"selection manifest has no non-empty scenario_ids list: {path}"
        raise ValueError(msg)
    if len(scenario_ids) != len(set(scenario_ids)):
        msg = f"selection manifest contains duplicate scenario ids: {path}"
        raise ValueError(msg)
    return tuple(scenario_ids)


def _diverse_sample(
    candidates: tuple[ScenarioFact, ...],
    count: int,
    seed: str,
) -> tuple[ScenarioFact, ...]:
    if len(candidates) < count:
        msg = f"selection quota requests {count} facts, but only {len(candidates)} are available"
        raise ValueError(msg)
    buckets: dict[str, deque[ScenarioFact]] = {}
    grouped: dict[str, list[ScenarioFact]] = defaultdict(list)
    for fact in candidates:
        grouped[fact.subcategory_id].append(fact)
    for subcategory, items in grouped.items():
        buckets[subcategory] = deque(sorted(items, key=lambda item: _stable_key(seed, item.scenario_spec_id)))
    subcategories = sorted(buckets, key=lambda item: _stable_key(seed, item))
    selected: list[ScenarioFact] = []
    while len(selected) < count:
        progressed = False
        for subcategory in subcategories:
            if buckets[subcategory] and len(selected) < count:
                selected.append(buckets[subcategory].popleft())
                progressed = True
        if not progressed:
            break
    return tuple(selected)


def _stable_key(seed: str, value: str) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode()).hexdigest()


def _parse_quota(raw: object) -> SelectionQuota:
    if not isinstance(raw, dict):
        msg = "every selection quota must be an object"
        raise ValueError(msg)
    count = raw.get("count")
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        msg = "selection quota count must be a positive integer"
        raise ValueError(msg)
    return SelectionQuota(
        source_dataset_id=required_string(raw, "source_dataset_id"),
        category_id=required_string(raw, "category_id"),
        count=count,
    )


def _string_tuple(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        msg = f"{key} must be a non-empty string list"
        raise ValueError(msg)
    return tuple(value)


def _optional_string_tuple(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        msg = f"{key} must be a string list"
        raise ValueError(msg)
    return tuple(value)
