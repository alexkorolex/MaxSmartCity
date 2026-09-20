"""Versioned report annotation records for human-reviewed Gold data."""

from dataclasses import dataclass
from typing import Literal

ReviewStatus = Literal["DRAFT", "REVIEWED", "FROZEN"]


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
    source: str
    review_status: ReviewStatus
    annotator: str
    reviewer: str | None
    notes: str | None = None
