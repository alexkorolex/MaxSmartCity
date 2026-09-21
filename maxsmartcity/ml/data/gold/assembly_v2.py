"""Assemble reviewed Gold v2 candidates from migrated v1 and expansion sources."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, cast

from maxsmartcity.ml.data.gold.expansion import ExpansionFrame
from maxsmartcity.ml.data.template_generation.models import LocationScope
from maxsmartcity.ml.data.template_generation.writer import load_template_examples


class GoldV2Assembler:
    def __init__(self, *, split_seed: int, reviewer: str) -> None:
        self._split_seed = split_seed
        self._reviewer = reviewer

    def assemble(
        self,
        *,
        migrated_dir: Path,
        expansion_frames_path: Path,
        expansion_seeds_path: Path,
        candidate_paths: tuple[Path, ...],
    ) -> dict[str, list[dict[str, Any]]]:
        splits = {
            split: self._review_migrated(_read_jsonl(migrated_dir / f"{split}.jsonl"))
            for split in ("train", "validation", "test")
        }
        frames = tuple(_expansion_frame(item) for item in _read_jsonl(expansion_frames_path))
        seeds = load_template_examples(expansion_seeds_path)
        seeds_by_frame: dict[str, list[Any]] = {}
        for seed in seeds:
            seeds_by_frame.setdefault(seed.frame_id, []).append(seed)
        candidates = _load_candidates(candidate_paths)
        normalized = {_normalize(record["text"]) for records in splits.values() for record in records}
        for frame in frames:
            records = self._expansion_records(
                frame,
                seeds_by_frame.get(frame.scenario_id, []),
                candidates.get(frame.scenario_id, []),
                normalized,
            )
            splits[_split_name(frame.scenario_id, self._split_seed)].extend(records)
        _validate(splits)
        return splits

    def _review_migrated(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for record in records:
            record["review_status"] = "REVIEWED"
            record["reviewer"] = self._reviewer
            record["notes"] = "Gold v1 text retained; labels migrated and audited against backend-aligned v2."
        return records

    def _expansion_records(
        self,
        frame: ExpansionFrame,
        seeds: list[Any],
        candidates: list[dict[str, Any]],
        normalized: set[str],
    ) -> list[dict[str, Any]]:
        matching_candidates = [item for item in candidates if item.get("base_problem") == frame.problem]
        matching_candidates.sort(key=lambda item: item.get("style_id") != "neutral")
        sources = [
            *[(seed.text, "SYNTHETIC_TEMPLATE", seed.example_id, None) for seed in seeds[:1]],
            *[
                (item["text"], "LLM_ASSISTED", item["candidate_id"], item.get("style_id"))
                for item in matching_candidates
            ],
            *[(seed.text, "SYNTHETIC_TEMPLATE", seed.example_id, None) for seed in seeds[1:]],
        ]
        selected: list[tuple[str, str, str, str | None]] = []
        for source in sources:
            value = _normalize(source[0])
            if value in normalized:
                continue
            normalized.add(value)
            selected.append(source)
            if len(selected) == 2:
                break
        if len(selected) != 2:
            msg = f"could not select two unique texts for {frame.scenario_id}"
            raise ValueError(msg)
        return [self._expansion_record(frame, source, index) for index, source in enumerate(selected)]

    def _expansion_record(
        self,
        frame: ExpansionFrame,
        source: tuple[str, str, str, str | None],
        index: int,
    ) -> dict[str, Any]:
        text, source_kind, source_id, style = source
        return {
            "record_id": f"GOLDV2-{_short_hash(f'{frame.scenario_id}:{source_id}:{index}')}",
            "scenario_id": frame.scenario_id,
            "text": text,
            "subcategory_ids": [frame.subcategory_id],
            "ambiguity": frame.routing_outcome != "ACCEPT",
            "primary_category": frame.primary_category,
            "routing_outcome": frame.routing_outcome,
            "danger_signals": list(frame.danger_signals),
            "extracted_features": {},
            "provenance": {
                "source_kind": source_kind,
                "parent_record_id": source_id,
                "generator_model": "mistral-medium-3-5" if source_kind == "LLM_ASSISTED" else None,
                "prompt_version": "controlled-template-paraphrase-v4"
                if source_kind == "LLM_ASSISTED"
                else None,
            },
            "review_status": "REVIEWED",
            "reviewer": self._reviewer,
            "notes": (
                f"Gold v2 expansion; selected style={style}."
                if style
                else "Gold v2 deterministic grounded seed."
            ),
        }


class GoldV2AssemblyWriter:
    def write(
        self,
        splits: dict[str, list[dict[str, Any]]],
        output_dir: Path,
        *,
        input_paths: tuple[Path, ...],
    ) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, dict[str, Any]] = {}
        all_records: list[dict[str, Any]] = []
        for split in ("train", "validation", "test"):
            records = sorted(splits[split], key=lambda item: str(item["record_id"]))
            all_records.extend(records)
            files[f"{split}.jsonl"] = _write_jsonl(output_dir / f"{split}.jsonl", records)
        files["reports.jsonl"] = _write_jsonl(
            output_dir / "reports.jsonl",
            sorted(all_records, key=lambda item: str(item["record_id"])),
        )
        manifest = {
            "dataset_name": "maxsmartcity-backend-aligned-report-texts",
            "dataset_version": "gold-v2-reviewed-candidate-v1",
            "annotation_version": "gold-report-v2",
            "taxonomy_version": "city-incidents-backend-aligned-v2",
            "status": "REVIEWED_PENDING_TEAM_SIGNOFF",
            "record_count": len(all_records),
            "scenario_count": len({str(item["scenario_id"]) for item in all_records}),
            "source_counts": dict(
                sorted(Counter(item["provenance"]["source_kind"] for item in all_records).items())
            ),
            "routing_counts": dict(
                sorted(Counter(str(item["routing_outcome"]) for item in all_records).items())
            ),
            "primary_category_counts": dict(
                sorted(Counter(str(item["primary_category"]) for item in all_records).items())
            ),
            "split_counts": {name: len(records) for name, records in splits.items()},
            "files": files,
            "inputs": {
                str(path).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in input_paths
            },
            "required_next_step": "team sign-off before setting records and manifest to FROZEN",
            "limitations": [
                "No real anonymized resident messages are included.",
                "Extraction targets remain empty and require a separate annotation pass.",
                "Routing and rare categories are deliberately oversampled in the v2 expansion.",
            ],
        }
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return manifest


def write_candidate_snapshot(
    *, frames_path: Path, candidate_paths: tuple[Path, ...], output_path: Path
) -> Path:
    """Persist only candidates that belong to the versioned expansion frames."""
    expected_problem = {str(item["scenario_id"]): str(item["problem"]) for item in _read_jsonl(frames_path)}
    selected: dict[str, dict[str, Any]] = {}
    for path in candidate_paths:
        for item in _read_jsonl(path):
            frame_id = str(item["frame_id"])
            if expected_problem.get(frame_id) != item.get("base_problem"):
                continue
            selected[str(item["candidate_id"])] = item
    records = sorted(selected.values(), key=lambda item: str(item["candidate_id"]))
    covered = {str(item["frame_id"]) for item in records}
    missing = sorted(set(expected_problem) - covered)
    if missing:
        raise ValueError(f"candidate snapshot misses expansion frames: {missing[:3]}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path, records)
    return output_path


def _load_candidates(paths: tuple[Path, ...]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for path in paths:
        for item in _read_jsonl(path):
            result.setdefault(str(item["frame_id"]), []).append(item)
    return result


def _expansion_frame(payload: dict[str, Any]) -> ExpansionFrame:
    return ExpansionFrame(
        scenario_id=str(payload["scenario_id"]),
        primary_category=(
            str(payload["primary_category"]) if payload["primary_category"] is not None else None
        ),
        routing_outcome=str(payload["routing_outcome"]),
        subcategory_id=str(payload["subcategory_id"]),
        danger_signals=tuple(payload["danger_signals"]),
        context_tags=tuple(payload["context_tags"]),
        location_scope=cast(LocationScope, payload["location_scope"]),
        address_required=bool(payload["address_required"]),
        street=str(payload["street"]),
        house_number=str(payload["house_number"]),
        problem=str(payload["problem"]),
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    content = "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)
    path.write_text(content, encoding="utf-8", newline="\n")
    return {"record_count": len(records), "sha256": hashlib.sha256(content.encode()).hexdigest()}


def _validate(splits: dict[str, list[dict[str, Any]]]) -> None:
    records = [record for values in splits.values() for record in values]
    ids = [str(item["record_id"]) for item in records]
    texts = [_normalize(str(item["text"])) for item in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Gold v2 record ids are not unique")
    if len(texts) != len(set(texts)):
        raise ValueError("Gold v2 normalized texts are not unique")
    scenario_splits: dict[str, str] = {}
    for split, values in splits.items():
        for record in values:
            scenario_id = str(record["scenario_id"])
            previous = scenario_splits.setdefault(scenario_id, split)
            if previous != split:
                raise ValueError(f"scenario leakage detected: {scenario_id}")
            accepted = record["routing_outcome"] == "ACCEPT"
            if accepted != (record["primary_category"] is not None):
                raise ValueError(f"category/routing invariant failed: {record['record_id']}")


def _split_name(scenario_id: str, seed: int) -> str:
    value = int.from_bytes(hashlib.sha256(f"{seed}:{scenario_id}".encode()).digest()[:8]) % 100
    return "train" if value < 70 else "validation" if value < 85 else "test"


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[а-яёa-z0-9]+", value.casefold()))


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]
