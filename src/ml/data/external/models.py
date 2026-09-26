"""Domain records for the external dataset preparation pipeline."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceReference:
    dataset_id: str
    record_ids: tuple[str, ...]
    semantic_key: str
    occurrence_count: int


@dataclass(frozen=True, slots=True)
class CanonicalLocation:
    city_id: str
    house_id: str
    street: str
    house_number: str
    synthetic: bool = True


@dataclass(frozen=True, slots=True)
class CanonicalScenarioSpec:
    schema_version: str
    scenario_spec_id: str
    taxonomy_version: str
    category_ids: tuple[str, ...]
    subcategory_id: str
    problem: str
    object_type: str
    severity: str
    organization_type: str | None
    location: CanonicalLocation
    source: SourceReference
    source_attributes: tuple[tuple[str, str], ...]
    context_tags: tuple[str, ...] = ()
    danger_signals: tuple[str, ...] = ()
    needs_clarification: bool = False
    ambiguity: bool = False


@dataclass(frozen=True, slots=True)
class Sf311Record:
    case_id: str
    category: str
    type: str
    details: str
    agency: str

    @property
    def semantic_key(self) -> str:
        return "|".join((self.category, self.type, self.details))


@dataclass(frozen=True, slots=True)
class BmcRecord:
    complaint_id: str
    complaint_category: str
    department_assigned: str
    severity: str
    property_type: str
    complaint_channel: str

    @property
    def semantic_key(self) -> str:
        return "|".join(
            (
                self.complaint_category,
                self.department_assigned,
                self.severity,
                self.property_type,
                self.complaint_channel,
            )
        )
