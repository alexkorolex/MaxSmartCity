"""Deterministic ``other``-category matching dataset with optional LLM wording.

Houses, event identities, labels, candidate sets and splits are deterministic. The
LLM may only rewrite locked event facts; it never chooses a house or a label.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final

DATASET_VERSION: Final = "other-incident-matching-v1"
DEFAULT_SEED: Final = 20260926


@dataclass(frozen=True, slots=True)
class IssueBlueprint:
    code: str
    family: str
    fact: str
    reference_subcategories: tuple[str, ...]


ISSUE_PAIRS: Final[tuple[tuple[IssueBlueprint, IssueBlueprint], ...]] = (
    (
        IssueBlueprint("night_music", "noise", "По ночам из квартиры слышна громкая музыка.", ("noise",)),
        IssueBlueprint(
            "renovation_noise", "noise", "В доме регулярно шумят ремонтными инструментами.", ("noise",)
        ),
    ),
    (
        IssueBlueprint(
            "stray_dogs", "animals", "У входа в дом собираются безнадзорные собаки.", ("stray_animals",)
        ),
        IssueBlueprint(
            "basement_cats",
            "animals",
            "В подвале дома постоянно находятся бездомные кошки.",
            ("stray_animals",),
        ),
    ),
    (
        IssueBlueprint(
            "cockroaches", "pests", "В общих помещениях дома появились тараканы.", ("public_health",)
        ),
        IssueBlueprint("rodents", "pests", "В общих помещениях дома замечены крысы.", ("public_health",)),
    ),
    (
        IssueBlueprint(
            "tobacco_smell",
            "odour",
            "В подъезде постоянно ощущается запах табачного дыма.",
            ("noise_or_air_pollution", "public_health"),
        ),
        IssueBlueprint(
            "unknown_odour",
            "odour",
            "В подъезде появился устойчивый неприятный запах неизвестного происхождения.",
            ("noise_or_air_pollution", "public_health"),
        ),
    ),
    (
        IssueBlueprint(
            "blocked_ramp",
            "access",
            "Подход к пандусу перекрыт посторонними предметами.",
            ("unknown_problem",),
        ),
        IssueBlueprint(
            "blocked_exit", "access", "Проход к общему выходу загромождён вещами.", ("unknown_problem",)
        ),
    ),
    (
        IssueBlueprint(
            "graffiti",
            "vandalism",
            "На стенах общего помещения появились надписи и рисунки.",
            ("unknown_problem",),
        ),
        IssueBlueprint(
            "mailboxes",
            "vandalism",
            "В общем помещении повреждены несколько почтовых ящиков.",
            ("unknown_problem",),
        ),
    ),
    (
        IssueBlueprint(
            "stored_furniture",
            "obstruction",
            "В общем коридоре жильцы оставили крупную мебель.",
            ("unknown_problem",),
        ),
        IssueBlueprint(
            "stored_bicycles",
            "obstruction",
            "В общем проходе постоянно хранят велосипеды и самокаты.",
            ("unknown_problem",),
        ),
    ),
    (
        IssueBlueprint(
            "illegal_ads",
            "nuisance",
            "В общих помещениях расклеивают объявления без согласования.",
            ("unknown_problem",),
        ),
        IssueBlueprint(
            "door_to_door_trade",
            "nuisance",
            "По квартирам регулярно ходят навязчивые продавцы.",
            ("unknown_problem",),
        ),
    ),
)


def select_houses(source_path: Path, *, per_city: int = 10, seed: int = DEFAULT_SEED) -> list[dict[str, Any]]:
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    raw_houses = payload.get("houses") if isinstance(payload, dict) else None
    if not isinstance(raw_houses, list):
        raise ValueError("house source must contain a houses list")
    by_city: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in raw_houses:
        if not isinstance(item, dict):
            continue
        city = item.get("city")
        key = item.get("key")
        if city in {"Брянск", "Бахчисарай"} and isinstance(key, str):
            by_city[city].append(item)
    selected: list[dict[str, Any]] = []
    for city in ("Брянск", "Бахчисарай"):
        ranked = sorted(
            by_city[city],
            key=lambda item: (_digest(f"{seed}:{item['key']}"), str(item["key"])),
        )
        if len(ranked) < per_city:
            raise ValueError(f"not enough houses for {city}: {len(ranked)}")
        selected.extend(ranked[:per_city])
    return [
        {
            "house_id": str(item["key"]),
            "external_id": item.get("external_id"),
            "fias_id": item.get("fias_id"),
            "city": item["city"],
            "street": item.get("street"),
            "house_number": item.get("house_number"),
            "formatted": item.get("formatted"),
        }
        for item in selected
    ]


def load_other_references(gold_path: Path) -> dict[str, tuple[str, ...]]:
    references: dict[str, list[str]] = defaultdict(list)
    for line in gold_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if item.get("primary_category") != "other":
            continue
        for subcategory in item.get("subcategory_ids", []):
            text = item.get("text")
            if isinstance(subcategory, str) and isinstance(text, str):
                references[subcategory].append(text)
    return {key: tuple(values) for key, values in references.items()}


def build_generation_tasks(
    houses: list[dict[str, Any]], references: dict[str, tuple[str, ...]], *, seed: int = DEFAULT_SEED
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for house_index, house in enumerate(houses):
        first_pair = house_index % len(ISSUE_PAIRS)
        second_pair = (house_index * 3 + 1) % len(ISSUE_PAIRS)
        if second_pair == first_pair:
            second_pair = (second_pair + 1) % len(ISSUE_PAIRS)
        blueprints = (*ISSUE_PAIRS[first_pair], *ISSUE_PAIRS[second_pair])
        events = []
        for event_index, blueprint in enumerate(blueprints):
            reference_pool = tuple(
                text
                for subcategory in blueprint.reference_subcategories
                for text in references.get(subcategory, ())
            )
            reference_rank = sorted(
                reference_pool,
                key=lambda text: (_digest(f"{seed}:{blueprint.code}:{text}"), text),
            )
            events.append(
                {
                    "event_id": f"OTHER-{house_index:03d}-{event_index}",
                    "issue_code": blueprint.code,
                    "issue_family": blueprint.family,
                    "locked_fact": blueprint.fact,
                    "reference_texts": reference_rank[:2],
                    "is_active_candidate": event_index < 3,
                }
            )
        tasks.append(
            {
                "task_id": f"OTHER-HOUSE-{house_index:03d}",
                "house": house,
                "events": events,
            }
        )
    return tasks


def materialize_dataset(
    tasks: list[dict[str, Any]], generations: dict[str, dict[str, dict[str, str]]], output_dir: Path
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    houses: list[dict[str, Any]] = []
    incidents: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    candidate_sets: list[dict[str, Any]] = []
    base_time = datetime(2026, 9, 26, 9, tzinfo=UTC)
    for house_index, task in enumerate(tasks):
        house = dict(task["house"])
        house["split"] = _split(house_index, len(tasks))
        houses.append(house)
        task_generations = generations.get(str(task["task_id"]), {})
        active_incidents: list[dict[str, Any]] = []
        event_reports: dict[str, list[dict[str, Any]]] = {}
        for event_index, event in enumerate(task["events"]):
            event_id = str(event["event_id"])
            generated = task_generations.get(event_id)
            if generated is None or set(generated) != {"neutral", "natural"}:
                raise ValueError(f"missing neutral/natural generation for {event_id}")
            texts = {
                "seed": str(event["locked_fact"]),
                "neutral": generated["neutral"].strip(),
                "natural": generated["natural"].strip(),
            }
            if not all(8 <= len(text) <= 500 for text in texts.values()):
                raise ValueError(f"invalid generated text length for {event_id}")
            occurred_at = base_time + timedelta(days=house_index, hours=event_index * 4)
            rows = []
            for style, text in texts.items():
                report = {
                    "report_id": f"{event_id}-{style.upper()}",
                    "event_id": event_id,
                    "house_id": house["house_id"],
                    "category_code": "other",
                    "issue_code": event["issue_code"],
                    "issue_family": event["issue_family"],
                    "style": style,
                    "text": text,
                    "occurred_at": occurred_at.isoformat(),
                    "split": house["split"],
                }
                rows.append(report)
                reports.append(report)
            event_reports[event_id] = rows
            if event["is_active_candidate"]:
                incident = {
                    "incident_id": f"INC-{event_id}",
                    "event_id": event_id,
                    "house_id": house["house_id"],
                    "category_code": "other",
                    "issue_code": event["issue_code"],
                    "issue_family": event["issue_family"],
                    "title": event["issue_code"],
                    "representative_texts": [texts["seed"]],
                    "last_activity_at": (base_time + timedelta(days=house_index)).isoformat(),
                    "split": house["split"],
                }
                active_incidents.append(incident)
                incidents.append(incident)
        candidate_ids = [item["incident_id"] for item in active_incidents]
        for event in task["events"]:
            event_id = str(event["event_id"])
            target = f"INC-{event_id}" if event["is_active_candidate"] else None
            candidate_sets.extend(
                {
                    "query_id": report["report_id"],
                    "event_id": event_id,
                    "house_id": house["house_id"],
                    "text": report["text"],
                    "candidate_incident_ids": candidate_ids,
                    "target_incident_id": target,
                    "expected_action": "RECOMMEND" if target else "CREATE_NEW",
                    "hard_negative": True,
                    "split": house["split"],
                }
                for report in event_reports[event_id][1:]
            )
    files = {
        "houses.jsonl": _write_jsonl(output_dir / "houses.jsonl", houses),
        "incidents.jsonl": _write_jsonl(output_dir / "incidents.jsonl", incidents),
        "reports.jsonl": _write_jsonl(output_dir / "reports.jsonl", reports),
        "candidate_sets.jsonl": _write_jsonl(output_dir / "candidate_sets.jsonl", candidate_sets),
    }
    manifest = {
        "dataset_version": DATASET_VERSION,
        "status": "SYNTHETIC_LLM_ASSISTED_REQUIRES_TEAM_REVIEW",
        "house_count": len(houses),
        "incident_count": len(incidents),
        "report_count": len(reports),
        "candidate_set_count": len(candidate_sets),
        "match_query_count": sum(item["target_incident_id"] is not None for item in candidate_sets),
        "create_new_query_count": sum(item["target_incident_id"] is None for item in candidate_sets),
        "split_counts": {
            split: sum(item["split"] == split for item in candidate_sets)
            for split in ("train", "validation", "test")
        },
        "files": files,
        "limitations": [
            "Houses are deterministic real registry references; report texts are synthetic.",
            "Labels derive from locked event ids, not from an LLM judgment.",
            "A small human review of hard negatives is still required before production calibration.",
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def _split(index: int, total: int) -> str:
    validation_start = max(1, total * 3 // 5)
    test_start = max(validation_start + 1, total * 4 // 5)
    if index < validation_start:
        return "train"
    if index < test_start:
        return "validation"
    return "test"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    content = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    path.write_text(content, encoding="utf-8", newline="\n")
    return hashlib.sha256(content.encode()).hexdigest()
