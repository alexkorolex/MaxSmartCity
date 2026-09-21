"""Load and validate frozen Gold splits for model training."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CategoryExample:
    example_id: str
    scenario_id: str
    text: str
    labels: tuple[str, ...]


def load_split(path: Path, label_field: str = "category_ids") -> list[CategoryExample]:
    examples: list[CategoryExample] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip():
            continue
        payload = json.loads(raw_line)
        if label_field == "primary_category":
            if payload.get("routing_outcome") != "ACCEPT":
                continue
            primary_category = payload.get("primary_category")
            labels = (str(primary_category),) if primary_category is not None else ()
            scenario_id = payload.get("scenario_id")
            example_id = payload.get("record_id")
        else:
            labels = tuple(str(value) for value in payload["category_ids"])
            scenario_id = payload.get("scenario_spec_id")
            example_id = payload.get("example_id")
        if not labels:
            raise ValueError(f"{path}:{line_number}: {label_field} must not be empty")
        if not scenario_id:
            raise ValueError(f"{path}:{line_number}: scenario id is required")
        if not example_id:
            raise ValueError(f"{path}:{line_number}: example id is required")
        examples.append(
            CategoryExample(
                example_id=str(example_id),
                scenario_id=str(scenario_id),
                text=str(payload["text"]),
                labels=labels,
            )
        )
    if not examples:
        raise ValueError(f"Dataset split is empty: {path}")
    return examples


def assert_scenario_disjoint(splits: dict[str, list[CategoryExample]]) -> None:
    split_scenarios = {
        name: {example.scenario_id for example in examples} for name, examples in splits.items()
    }
    names = list(split_scenarios)
    for index, left_name in enumerate(names):
        for right_name in names[index + 1 :]:
            overlap = split_scenarios[left_name] & split_scenarios[right_name]
            if overlap:
                sample = sorted(overlap)[:3]
                raise ValueError(f"Scenario leakage between {left_name} and {right_name}: {sample}")
