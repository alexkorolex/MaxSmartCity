"""Semantic validation beyond JSON Schema for manually annotated records."""

import json
from pathlib import Path
from typing import Any, cast

from maxsmartcity.ml.data.config import TaxonomyConfig
from maxsmartcity.ml.data.gold.models import (
    AnnotationSource,
    EntityAnnotation,
    GoldReportAnnotation,
)


class GoldDatasetValidator:
    def __init__(self, taxonomy: TaxonomyConfig) -> None:
        self.taxonomy = taxonomy

    def load_and_validate(self, path: Path) -> tuple[GoldReportAnnotation, ...]:
        records = tuple(
            self._parse(json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        self.validate(records)
        return records

    def validate(self, records: tuple[GoldReportAnnotation, ...]) -> None:
        ids = [record.example_id for record in records]
        if len(ids) != len(set(ids)):
            msg = "Gold example_id values must be unique"
            raise ValueError(msg)
        for record in records:
            if record.annotation_version != "gold-report-v1":
                msg = f"{record.example_id}: unsupported annotation version"
                raise ValueError(msg)
            if record.review_status not in {"DRAFT", "REVIEWED", "FROZEN"}:
                msg = f"{record.example_id}: unsupported review status"
                raise ValueError(msg)
            if record.source not in {
                "HUMAN_AUTHORED",
                "REAL_ANONYMIZED",
                "SYNTHETIC_TEMPLATE",
                "LLM_ASSISTED",
            }:
                msg = f"{record.example_id}: unsupported source"
                raise ValueError(msg)
            if record.source in {"SYNTHETIC_TEMPLATE", "LLM_ASSISTED"} and not (
                record.scenario_spec_id and record.generation_source_id
            ):
                msg = f"{record.example_id}: synthetic sources require provenance ids"
                raise ValueError(msg)
            if not record.category_ids:
                msg = f"{record.example_id}: at least one category is required"
                raise ValueError(msg)
            unknown = set(record.category_ids) - self.taxonomy.category_ids
            if unknown:
                msg = f"{record.example_id}: unknown category ids: {sorted(unknown)}"
                raise ValueError(msg)
            if not record.text.strip():
                msg = f"{record.example_id}: text must not be empty"
                raise ValueError(msg)
            if record.review_status in {"REVIEWED", "FROZEN"} and not record.reviewer:
                msg = f"{record.example_id}: reviewed records require reviewer"
                raise ValueError(msg)
            if record.needs_clarification and "needs_clarification" not in record.category_ids:
                msg = f"{record.example_id}: clarification flag requires its category"
                raise ValueError(msg)
            for entity in record.entities:
                if not 0 <= entity.start < entity.end <= len(record.text):
                    msg = f"{record.example_id}: invalid entity span"
                    raise ValueError(msg)
                if record.text[entity.start : entity.end] != entity.value:
                    msg = f"{record.example_id}: entity value does not match its span"
                    raise ValueError(msg)

    @staticmethod
    def _parse(payload: dict[str, Any]) -> GoldReportAnnotation:
        entities = tuple(EntityAnnotation(**entity) for entity in payload.get("entities", []))
        return GoldReportAnnotation(
            annotation_version=payload["annotation_version"],
            example_id=payload["example_id"],
            text=payload["text"],
            category_ids=tuple(payload["category_ids"]),
            subcategory_ids=tuple(payload.get("subcategory_ids", [])),
            entities=entities,
            danger_signals=tuple(payload.get("danger_signals", [])),
            needs_clarification=payload["needs_clarification"],
            ambiguity=payload["ambiguity"],
            source=cast(AnnotationSource, payload["source"]),
            review_status=payload["review_status"],
            annotator=payload["annotator"],
            reviewer=payload.get("reviewer"),
            notes=payload.get("notes"),
            scenario_spec_id=payload.get("scenario_spec_id"),
            generation_source_id=payload.get("generation_source_id"),
        )
