"""Build a reviewed MVP text dataset from canonical facts and selected lexicalizations."""

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from maxsmartcity.ml.data.config import TaxonomyConfig, load_json_object, required_string
from maxsmartcity.ml.data.gold.models import AnnotationSource, GoldReportAnnotation
from maxsmartcity.ml.data.gold.validator import GoldDatasetValidator
from maxsmartcity.ml.data.llm.input import load_scenario_facts
from maxsmartcity.ml.data.llm.models import ScenarioFact
from maxsmartcity.ml.data.template_generation.canonical import (
    CanonicalTemplateSeedGenerator,
    load_canonical_seed_config,
)
from maxsmartcity.ml.data.template_generation.models import TemplateExample


@dataclass(frozen=True, slots=True)
class TextOverride:
    scenario_spec_id: str
    text: str
    reason: str


@dataclass(frozen=True, slots=True)
class ReviewedDatasetConfig:
    version: str
    annotation_version: str
    taxonomy_version: str
    preferred_style: str
    split_seed: int
    annotator: str
    reviewer: str
    overrides: tuple[TextOverride, ...]
    split_overrides: tuple[tuple[str, str], ...]


def load_reviewed_dataset_config(path: Path) -> ReviewedDatasetConfig:
    payload = load_json_object(path)
    raw_overrides = payload.get("text_overrides", [])
    if not isinstance(raw_overrides, list):
        msg = "text_overrides must be a list"
        raise ValueError(msg)
    overrides = tuple(_parse_override(item) for item in raw_overrides)
    ids = [item.scenario_spec_id for item in overrides]
    if len(ids) != len(set(ids)):
        msg = "text override scenario ids must be unique"
        raise ValueError(msg)
    split_seed = payload.get("split_seed")
    if not isinstance(split_seed, int) or isinstance(split_seed, bool):
        msg = "split_seed must be an integer"
        raise ValueError(msg)
    raw_split_overrides = payload.get("split_overrides", {})
    if not isinstance(raw_split_overrides, dict) or not all(
        isinstance(key, str) and key and value in {"train", "validation", "test"}
        for key, value in raw_split_overrides.items()
    ):
        msg = "split_overrides must map scenario ids to train, validation or test"
        raise ValueError(msg)
    return ReviewedDatasetConfig(
        version=required_string(payload, "version"),
        annotation_version=required_string(payload, "annotation_version"),
        taxonomy_version=required_string(payload, "taxonomy_version"),
        preferred_style=required_string(payload, "preferred_style"),
        split_seed=split_seed,
        annotator=required_string(payload, "annotator"),
        reviewer=required_string(payload, "reviewer"),
        overrides=overrides,
        split_overrides=tuple(sorted(raw_split_overrides.items())),
    )


class ReviewedDatasetBuilder:
    def __init__(self, config: ReviewedDatasetConfig, taxonomy: TaxonomyConfig) -> None:
        self._config = config
        self._taxonomy = taxonomy
        if config.taxonomy_version != taxonomy.version:
            msg = "reviewed dataset and taxonomy versions differ"
            raise ValueError(msg)

    def build(
        self,
        *,
        canonical_path: Path,
        seed_config_path: Path,
        candidate_paths: tuple[Path, ...],
    ) -> tuple[GoldReportAnnotation, ...]:
        facts = load_scenario_facts(canonical_path)
        seeds = CanonicalTemplateSeedGenerator(
            load_canonical_seed_config(seed_config_path)
        ).generate(facts)
        first_seeds: dict[str, TemplateExample] = {}
        for seed in seeds:
            first_seeds.setdefault(seed.frame_id, seed)
        candidates = _load_candidates(candidate_paths, self._config.preferred_style)
        overrides = {item.scenario_spec_id: item for item in self._config.overrides}
        fact_ids = {fact.scenario_spec_id for fact in facts}
        if set(overrides) - fact_ids:
            msg = f"text overrides reference unknown scenarios: {sorted(set(overrides) - fact_ids)}"
            raise ValueError(msg)

        records: list[GoldReportAnnotation] = []
        for fact in sorted(facts, key=lambda item: item.scenario_spec_id):
            seed = first_seeds[fact.scenario_spec_id]
            records.append(
                self._record(
                    fact,
                    text=seed.text,
                    source="SYNTHETIC_TEMPLATE",
                    source_id=seed.example_id,
                    notes="Reviewed deterministic canonical template seed.",
                )
            )
            override = overrides.get(fact.scenario_spec_id)
            if override is not None:
                text = override.text
                source_id = f"MANUAL-{_short_hash(fact.scenario_spec_id)}"
                notes = f"Manually corrected after LLM audit: {override.reason}"
            else:
                candidate = candidates.get(fact.scenario_spec_id)
                if candidate is None:
                    msg = (
                        f"missing {self._config.preferred_style} candidate: {fact.scenario_spec_id}"
                    )
                    raise ValueError(msg)
                text = required_string(candidate, "text")
                source_id = required_string(candidate, "candidate_id")
                notes = "LLM-assisted lexicalization selected after deterministic and manual audit."
            records.append(
                self._record(
                    fact,
                    text=text,
                    source="LLM_ASSISTED",
                    source_id=source_id,
                    notes=notes,
                )
            )

        result = tuple(records)
        GoldDatasetValidator(self._taxonomy).validate(result)
        _assert_two_records_per_scenario(result, len(facts))
        _assert_unique_texts(result)
        return result

    def _record(
        self,
        fact: ScenarioFact,
        *,
        text: str,
        source: AnnotationSource,
        source_id: str,
        notes: str,
    ) -> GoldReportAnnotation:
        return GoldReportAnnotation(
            annotation_version=self._config.annotation_version,
            example_id=f"GOLD-{_short_hash(f'{fact.scenario_spec_id}:{source}')}",
            text=text,
            category_ids=fact.category_ids,
            subcategory_ids=(fact.subcategory_id,),
            entities=(),
            danger_signals=fact.danger_signals,
            needs_clarification=fact.needs_clarification,
            ambiguity=fact.ambiguity,
            source=source,
            review_status="REVIEWED",
            annotator=self._config.annotator,
            reviewer=self._config.reviewer,
            notes=notes,
            scenario_spec_id=fact.scenario_spec_id,
            generation_source_id=source_id,
        )


class ReviewedDatasetWriter:
    def write(
        self,
        records: tuple[GoldReportAnnotation, ...],
        output_dir: Path,
        *,
        config: ReviewedDatasetConfig,
        input_paths: tuple[Path, ...],
    ) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        split_records: dict[str, list[GoldReportAnnotation]] = {
            "train": [],
            "validation": [],
            "test": [],
        }
        split_overrides = dict(config.split_overrides)
        scenario_ids = {
            record.scenario_spec_id for record in records if record.scenario_spec_id is not None
        }
        if set(split_overrides) - scenario_ids:
            unknown = sorted(set(split_overrides) - scenario_ids)
            msg = f"split overrides reference unknown scenarios: {unknown}"
            raise ValueError(msg)
        for record in records:
            if record.scenario_spec_id is None:
                msg = f"reviewed record lacks scenario id: {record.example_id}"
                raise ValueError(msg)
            split = split_overrides.get(
                record.scenario_spec_id,
                _split_name(record.scenario_spec_id, config.split_seed),
            )
            split_records[split].append(record)
        files: dict[str, dict[str, Any]] = {}
        for name, values in (("reports", records), *split_records.items()):
            path = output_dir / f"{name}.jsonl"
            content = "".join(
                json.dumps(_record_payload(item), ensure_ascii=False, sort_keys=True) + "\n"
                for item in values
            )
            path.write_text(content, encoding="utf-8", newline="\n")
            files[path.name] = {
                "record_count": len(values),
                "sha256": hashlib.sha256(content.encode()).hexdigest(),
            }
        _assert_split_isolation(split_records)
        manifest: dict[str, Any] = {
            "dataset_name": "maxsmartcity-reviewed-report-texts",
            "dataset_version": config.version,
            "annotation_version": config.annotation_version,
            "taxonomy_version": config.taxonomy_version,
            "status": "REVIEWED_MVP_PENDING_HUMAN_SIGNOFF",
            "record_count": len(records),
            "scenario_count": len({item.scenario_spec_id for item in records}),
            "source_counts": dict(sorted(Counter(item.source for item in records).items())),
            "split_seed": config.split_seed,
            "split_overrides": dict(config.split_overrides),
            "files": files,
            "inputs": {
                str(path).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in input_paths
            },
            "excluded_scope": [
                "report-to-incident reranking pairs",
                "hard negatives",
                "production or real anonymized reports",
            ],
            "required_next_step": "human sign-off before changing review_status to FROZEN",
        }
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return manifest


def _load_candidates(paths: tuple[Path, ...], style: str) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                msg = f"candidate file contains a non-object record: {path}"
                raise ValueError(msg)
            if payload.get("style_id") != style:
                continue
            frame_id = required_string(payload, "frame_id")
            if frame_id in selected:
                msg = f"duplicate {style} candidate for {frame_id}"
                raise ValueError(msg)
            selected[frame_id] = payload
    return selected


def _parse_override(raw: object) -> TextOverride:
    if not isinstance(raw, dict):
        msg = "every text override must be an object"
        raise ValueError(msg)
    return TextOverride(
        scenario_spec_id=required_string(raw, "scenario_spec_id"),
        text=required_string(raw, "text"),
        reason=required_string(raw, "reason"),
    )


def _assert_two_records_per_scenario(
    records: tuple[GoldReportAnnotation, ...], scenario_count: int
) -> None:
    counts = Counter(item.scenario_spec_id for item in records)
    if len(counts) != scenario_count or set(counts.values()) != {2}:
        msg = "reviewed dataset must contain exactly two texts per scenario"
        raise ValueError(msg)


def _assert_unique_texts(records: tuple[GoldReportAnnotation, ...]) -> None:
    normalized = [_normalize(item.text) for item in records]
    duplicates = [text for text, count in Counter(normalized).items() if count > 1]
    if duplicates:
        msg = f"reviewed dataset contains normalized duplicate texts: {duplicates[:3]}"
        raise ValueError(msg)


def _assert_split_isolation(splits: dict[str, list[GoldReportAnnotation]]) -> None:
    groups = [
        {record.scenario_spec_id for record in splits[name]}
        for name in ("train", "validation", "test")
    ]
    if groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2]:
        msg = "scenario leakage detected in reviewed dataset splits"
        raise ValueError(msg)


def _record_payload(record: GoldReportAnnotation) -> dict[str, Any]:
    return {
        "annotation_version": record.annotation_version,
        "example_id": record.example_id,
        "scenario_spec_id": record.scenario_spec_id,
        "text": record.text,
        "category_ids": list(record.category_ids),
        "subcategory_ids": list(record.subcategory_ids),
        "entities": [
            {"start": item.start, "end": item.end, "type": item.type, "value": item.value}
            for item in record.entities
        ],
        "danger_signals": list(record.danger_signals),
        "needs_clarification": record.needs_clarification,
        "ambiguity": record.ambiguity,
        "source": record.source,
        "generation_source_id": record.generation_source_id,
        "review_status": record.review_status,
        "annotator": record.annotator,
        "reviewer": record.reviewer,
        "notes": record.notes,
    }


def _split_name(scenario_id: str, seed: int) -> str:
    digest = hashlib.sha256(f"{seed}:{scenario_id}".encode()).digest()
    value = int.from_bytes(digest[:8]) % 100
    return "train" if value < 70 else "validation" if value < 85 else "test"


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[а-яёa-z0-9]+", value.casefold()))


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]
