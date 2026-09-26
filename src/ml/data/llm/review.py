"""Human-review queue for promoting automatically validated candidates to Gold."""

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.ml.data.llm.models import ScenarioFact

REVIEW_FIELDS = (
    "candidate_id",
    "scenario_spec_id",
    "source_dataset_id",
    "locked_problem",
    "locked_context_tags",
    "locked_danger_signals",
    "expected_street",
    "expected_house_number",
    "category_ids",
    "subcategory_id",
    "generation_pass",
    "style_id",
    "generated_text",
    "review_decision",
    "reviewer_note",
)


def load_jsonl_objects(path: Path) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            msg = f"review input contains a non-object record: {path}"
            raise ValueError(msg)
        records.append(payload)
    return tuple(records)


def build_review_rows(
    candidates: tuple[dict[str, Any], ...],
    facts: tuple[ScenarioFact, ...],
) -> tuple[dict[str, str], ...]:
    facts_by_id = {fact.scenario_spec_id: fact for fact in facts}
    rows: list[dict[str, str]] = []
    for candidate in candidates:
        scenario_id = _required_string(candidate, "scenario_spec_id")
        if scenario_id not in facts_by_id:
            msg = f"candidate references unknown scenario: {scenario_id}"
            raise ValueError(msg)
        fact = facts_by_id[scenario_id]
        generation = candidate.get("generation")
        if not isinstance(generation, dict):
            msg = f"candidate has no generation metadata: {candidate.get('candidate_id')}"
            raise ValueError(msg)
        rows.append(
            {
                "candidate_id": _required_string(candidate, "candidate_id"),
                "scenario_spec_id": scenario_id,
                "source_dataset_id": fact.source_dataset_id,
                "locked_problem": fact.problem,
                "locked_context_tags": "|".join(fact.context_tags),
                "locked_danger_signals": "|".join(fact.danger_signals),
                "expected_street": fact.street,
                "expected_house_number": fact.house_number,
                "category_ids": "|".join(fact.category_ids),
                "subcategory_id": fact.subcategory_id,
                "generation_pass": _required_string(generation, "pass_id"),
                "style_id": _required_string(candidate, "style_id"),
                "generated_text": _required_string(candidate, "text"),
                "review_decision": "",
                "reviewer_note": "",
            }
        )
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                item["scenario_spec_id"],
                item["generation_pass"],
                item["style_id"],
                item["candidate_id"],
            ),
        )
    )


def write_review_queue(path: Path, rows: tuple[dict[str, str], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REVIEW_FIELDS, extrasaction="raise")
        writer.writeheader()
        writer.writerows({key: _spreadsheet_safe(value) for key, value in row.items()} for row in rows)


def build_review_summary(rows: tuple[dict[str, str], ...]) -> dict[str, Any]:
    return {
        "status": "HUMAN_REVIEW_REQUIRED",
        "candidate_count": len(rows),
        "scenario_count": len({row["scenario_spec_id"] for row in rows}),
        "counts": {
            "source_dataset_ids": dict(sorted(Counter(row["source_dataset_id"] for row in rows).items())),
            "generation_passes": dict(sorted(Counter(row["generation_pass"] for row in rows).items())),
            "styles": dict(sorted(Counter(row["style_id"] for row in rows).items())),
        },
        "allowed_review_decisions": ["ACCEPT", "REJECT", "EDIT"],
    }


def write_review_summary(path: Path, summary: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        msg = f"review field {key} must be a non-empty string"
        raise ValueError(msg)
    return value


def _spreadsheet_safe(value: str) -> str:
    return f"'{value}" if value.startswith(("=", "+", "-", "@")) else value
