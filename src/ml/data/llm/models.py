"""Domain records for offline report-text generation."""

from dataclasses import dataclass
from typing import Literal

AddressRequirement = Literal["REQUIRED", "FORBIDDEN"]


@dataclass(frozen=True, slots=True)
class GenerationPass:
    id: str
    temperature: float
    variants_per_scenario: int
    styles: tuple[str, ...]
    source_dataset_ids: tuple[str, ...]

    def applies_to(self, source_dataset_id: str) -> bool:
        return "*" in self.source_dataset_ids or source_dataset_id in self.source_dataset_ids


@dataclass(frozen=True, slots=True)
class ScenarioFact:
    scenario_spec_id: str
    taxonomy_version: str
    category_ids: tuple[str, ...]
    subcategory_id: str
    problem: str
    object_type: str
    severity: str
    organization_type: str | None
    street: str
    house_number: str
    source_dataset_id: str
    source_attributes: tuple[tuple[str, str], ...]
    context_tags: tuple[str, ...]
    danger_signals: tuple[str, ...]
    needs_clarification: bool
    ambiguity: bool

    @property
    def address_requirement(self) -> AddressRequirement:
        if "non_incident" in self.category_ids:
            return "FORBIDDEN"
        if self.needs_clarification and self.subcategory_id != "address_only":
            return "FORBIDDEN"
        return "REQUIRED"


@dataclass(frozen=True, slots=True)
class GeneratedVariant:
    text: str
    style_id: str
    address_included: bool


@dataclass(frozen=True, slots=True)
class GenerationUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class GenerationResponse:
    response_id: str
    model: str
    scenario_spec_id: str
    variants: tuple[GeneratedVariant, ...]
    usage: GenerationUsage


@dataclass(frozen=True, slots=True)
class VariantValidation:
    variant: GeneratedVariant
    errors: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return not self.errors
