"""Domain records for template-first report generation."""

from dataclasses import dataclass
from typing import Literal

LocationScope = Literal["BUILDING", "OUTDOOR", "NONE"]


@dataclass(frozen=True, slots=True)
class IssueFrame:
    id: str
    category_ids: tuple[str, ...]
    subcategory_id: str
    problem_variants: tuple[str, ...]
    context_tags: tuple[str, ...]
    danger_signals: tuple[str, ...]
    location_scope: LocationScope
    allowed_template_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TextTemplate:
    id: str
    text: str


@dataclass(frozen=True, slots=True)
class TemplateGenerationConfig:
    version: str
    seed: int
    variants_per_frame: int
    templates: tuple[TextTemplate, ...]
    frames: tuple[IssueFrame, ...]


@dataclass(frozen=True, slots=True)
class RussianAddress:
    street: str
    street_sentence: str
    house_number: str
    at_street: str


@dataclass(frozen=True, slots=True)
class TemplateExample:
    example_id: str
    config_version: str
    frame_id: str
    category_ids: tuple[str, ...]
    subcategory_id: str
    context_tags: tuple[str, ...]
    danger_signals: tuple[str, ...]
    location_scope: LocationScope
    address_required: bool
    street: str
    house_number: str
    template_id: str
    base_problem: str
    text: str
