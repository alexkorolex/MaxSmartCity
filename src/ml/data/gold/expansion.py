"""Generate balanced, deterministic Gold v2 scenario frames and grounded seeds."""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from src.ml.data.config import load_json_object, required_string
from src.ml.data.template_generation.models import LocationScope, TemplateExample


@dataclass(frozen=True, slots=True)
class ExpansionProfile:
    id: str
    primary_category: str | None
    routing_outcome: str
    subcategory_id: str
    location_scope: LocationScope
    address_required: bool
    problem_variants: tuple[str, ...]
    danger_signals: tuple[str, ...]
    context_tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExpansionConfig:
    version: str
    seed: int
    scenarios_per_profile: int
    addresses: tuple[tuple[str, str], ...]
    profiles: tuple[ExpansionProfile, ...]

    @classmethod
    def load(cls, path: Path) -> ExpansionConfig:
        payload = load_json_object(path)
        raw_profiles = payload.get("profiles")
        if not isinstance(raw_profiles, list) or not raw_profiles:
            msg = "profiles must be a non-empty object list"
            raise ValueError(msg)
        profiles = tuple(_profile(item) for item in raw_profiles)
        ids = [item.id for item in profiles]
        if len(ids) != len(set(ids)):
            msg = "expansion profile ids must be unique"
            raise ValueError(msg)
        return cls(
            version=required_string(payload, "version"),
            seed=_positive_int(payload, "seed"),
            scenarios_per_profile=_positive_int(payload, "scenarios_per_profile"),
            addresses=_addresses(payload),
            profiles=profiles,
        )


@dataclass(frozen=True, slots=True)
class ExpansionFrame:
    scenario_id: str
    primary_category: str | None
    routing_outcome: str
    subcategory_id: str
    danger_signals: tuple[str, ...]
    context_tags: tuple[str, ...]
    location_scope: LocationScope
    address_required: bool
    street: str
    house_number: str
    problem: str


class GoldV2ExpansionGenerator:
    def __init__(self, config: ExpansionConfig) -> None:
        self._config = config

    def generate(self) -> tuple[tuple[ExpansionFrame, ...], tuple[TemplateExample, ...]]:
        frames: list[ExpansionFrame] = []
        examples: list[TemplateExample] = []
        for profile in self._config.profiles:
            rng = random.Random(f"{self._config.seed}:{profile.id}")
            addresses = list(self._config.addresses)
            rng.shuffle(addresses)
            for index in range(self._config.scenarios_per_profile):
                problem = profile.problem_variants[index % len(profile.problem_variants)]
                street, house_number = addresses[index % len(addresses)]
                if not profile.address_required:
                    street = house_number = ""
                scenario_id = f"V2-{profile.id}-{index + 1:02d}"
                frame = ExpansionFrame(
                    scenario_id=scenario_id,
                    primary_category=profile.primary_category,
                    routing_outcome=profile.routing_outcome,
                    subcategory_id=profile.subcategory_id,
                    danger_signals=profile.danger_signals,
                    context_tags=profile.context_tags,
                    location_scope=profile.location_scope,
                    address_required=profile.address_required,
                    street=street,
                    house_number=house_number,
                    problem=problem,
                )
                frames.append(frame)
                examples.extend(self._examples(frame))
        return tuple(frames), tuple(examples)

    def _examples(self, frame: ExpansionFrame) -> tuple[TemplateExample, ...]:
        texts = _seed_texts(frame)
        return tuple(
            TemplateExample(
                example_id=f"V2SEED-{_short_hash(f'{self._config.version}:{frame.scenario_id}:{index}')}",
                config_version=self._config.version,
                frame_id=frame.scenario_id,
                category_ids=(frame.primary_category,) if frame.primary_category else (),
                subcategory_id=frame.subcategory_id,
                context_tags=frame.context_tags,
                danger_signals=frame.danger_signals,
                location_scope=frame.location_scope,
                address_required=frame.address_required,
                street=frame.street,
                house_number=frame.house_number,
                template_id=f"gold-v2-grounded-{index + 1}",
                base_problem=frame.problem,
                text=text,
            )
            for index, text in enumerate(texts)
        )


class GoldV2ExpansionWriter:
    def write(
        self,
        frames: tuple[ExpansionFrame, ...],
        examples: tuple[TemplateExample, ...],
        output_dir: Path,
        *,
        config_path: Path,
    ) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        frame_path = output_dir / "frames.jsonl"
        seed_path = output_dir / "examples.jsonl"
        frame_content = "".join(
            json.dumps(asdict(frame), ensure_ascii=False, sort_keys=True) + "\n" for frame in frames
        )
        seed_content = "".join(
            json.dumps(asdict(example), ensure_ascii=False, sort_keys=True) + "\n" for example in examples
        )
        frame_path.write_text(frame_content, encoding="utf-8", newline="\n")
        seed_path.write_text(seed_content, encoding="utf-8", newline="\n")
        manifest = {
            "status": "LOCAL_GROUNDED_FRAMES_REQUIRE_REVIEW",
            "frame_count": len(frames),
            "example_count": len(examples),
            "profile_count": len({frame.scenario_id.rsplit("-", 1)[0] for frame in frames}),
            "routing_counts": _counts(frame.routing_outcome for frame in frames),
            "primary_category_counts": _counts(frame.primary_category or "NONE" for frame in frames),
            "files": {
                "frames.jsonl": _hash(frame_content.encode()),
                "examples.jsonl": _hash(seed_content.encode()),
            },
            "config_sha256": _hash(config_path.read_bytes()),
        }
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return manifest


def _seed_texts(frame: ExpansionFrame) -> tuple[str, str]:
    problem = frame.problem.strip().rstrip(".!?")
    if not frame.address_required:
        return (f"{problem.capitalize()}.", f"Сообщение жителя: {problem}.")
    first = f"{frame.street}, дом {frame.house_number}: {problem}."
    second = f"По адресу {frame.street}, дом {frame.house_number}, {problem}."
    return first, second


def _profile(raw: object) -> ExpansionProfile:
    if not isinstance(raw, dict):
        msg = "every profile must be an object"
        raise ValueError(msg)
    scope = raw.get("location_scope")
    if scope not in ("BUILDING", "OUTDOOR", "NONE"):
        msg = "location_scope must be BUILDING, OUTDOOR or NONE"
        raise ValueError(msg)
    primary = raw.get("primary_category")
    if primary is not None and not isinstance(primary, str):
        msg = "primary_category must be a string or null"
        raise ValueError(msg)
    address_required = raw.get("address_required")
    if not isinstance(address_required, bool):
        msg = "address_required must be a boolean"
        raise ValueError(msg)
    if scope == "NONE" and address_required:
        msg = "NONE location_scope cannot require an address"
        raise ValueError(msg)
    routing = required_string(raw, "routing_outcome")
    if (routing == "ACCEPT") != (primary is not None):
        msg = "ACCEPT requires primary_category; other routing outcomes forbid it"
        raise ValueError(msg)
    return ExpansionProfile(
        id=required_string(raw, "id"),
        primary_category=primary,
        routing_outcome=routing,
        subcategory_id=required_string(raw, "subcategory_id"),
        location_scope=cast(LocationScope, scope),
        address_required=address_required,
        problem_variants=_strings(raw, "problem_variants"),
        danger_signals=_strings(raw, "danger_signals", allow_empty=True),
        context_tags=_strings(raw, "context_tags", allow_empty=True),
    )


def _addresses(payload: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    raw = payload.get("addresses")
    if not isinstance(raw, list) or not raw:
        msg = "addresses must be a non-empty list"
        raise ValueError(msg)
    result: list[tuple[str, str]] = []
    for item in raw:
        if not isinstance(item, list) or len(item) != 2 or not all(isinstance(x, str) for x in item):
            msg = "every address must contain street and house number"
            raise ValueError(msg)
        result.append((item[0], item[1]))
    return tuple(result)


def _strings(payload: dict[str, Any], key: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    value = payload.get(key)
    if (
        not isinstance(value, list)
        or (not value and not allow_empty)
        or not all(isinstance(item, str) and item for item in value)
    ):
        msg = f"{key} must be a string list"
        raise ValueError(msg)
    return tuple(value)


def _positive_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        msg = f"{key} must be a positive integer"
        raise ValueError(msg)
    return value


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
