"""Versioned report annotation records for human-reviewed Gold data."""

from dataclasses import dataclass
from typing import Literal

ReviewStatus = Literal["DRAFT", "REVIEWED", "FROZEN"]
AnnotationSource = Literal[
    "HUMAN_AUTHORED",
    "REAL_ANONYMIZED",
    "SYNTHETIC_TEMPLATE",
    "LLM_ASSISTED",
]


@dataclass(frozen=True, slots=True)
class EntityAnnotation:
    start: int
    end: int
    type: str
    value: str


@dataclass(frozen=True, slots=True)
class GoldReportAnnotation:
    annotation_version: str
    example_id: str
    text: str
    category_ids: tuple[str, ...]
    subcategory_ids: tuple[str, ...]
    entities: tuple[EntityAnnotation, ...]
    danger_signals: tuple[str, ...]
    needs_clarification: bool
    ambiguity: bool
    source: AnnotationSource
    review_status: ReviewStatus
    annotator: str
    reviewer: str | None
    notes: str | None = None
    scenario_spec_id: str | None = None
    generation_source_id: str | None = None
