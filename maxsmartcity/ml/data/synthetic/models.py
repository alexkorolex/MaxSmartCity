"""Synthetic world entities and labelled examples."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScenarioRecord:
    scenario_id: str
    city_id: str
    archetype_id: str
    seed: int
    scenario_kind: str = "STANDARD"


@dataclass(frozen=True, slots=True)
class HouseRecord:
    house_id: str
    scenario_id: str
    fias_guid: str
    street: str
    house_number: str


@dataclass(frozen=True, slots=True)
class OrganizationRecord:
    organization_id: str
    organization_type: str
    name: str


@dataclass(frozen=True, slots=True)
class ExternalEventRecord:
    external_event_id: str
    scenario_id: str
    category_id: str
    affected_fias_guids: tuple[str, ...]
    organization_id: str
    observed_at: str
    authority: str = "SYNTHETIC_OFFICIAL"


@dataclass(frozen=True, slots=True)
class IncidentRecord:
    incident_id: str
    scenario_id: str
    category_id: str
    organization_id: str
    fias_guids: tuple[str, ...]
    started_at: str


@dataclass(frozen=True, slots=True)
class ReportRecord:
    report_id: str
    scenario_id: str
    incident_id: str | None
    text: str
    category_id: str
    organization_id: str | None
    fias_guid: str | None
    timestamp: str
    style_id: str
    generation_seed: int
    source_report_id: str | None = None
    paraphrase_family_id: str | None = None
    needs_clarification: bool = False
    supported_by_context: bool = True


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    decision_id: str
    scenario_id: str
    report_id: str
    candidate_incident_ids: tuple[str, ...]
    target_incident_ids: tuple[str, ...]
    hard_negative_incident_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CounterfactualRecord:
    counterfactual_id: str
    scenario_id: str
    source_report_id: str
    mutated_field: str
    original_value: str
    mutated_value: str
    text: str
    target_incident_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SyntheticBundle:
    scenarios: tuple[ScenarioRecord, ...]
    houses: tuple[HouseRecord, ...]
    organizations: tuple[OrganizationRecord, ...]
    external_events: tuple[ExternalEventRecord, ...]
    incidents: tuple[IncidentRecord, ...]
    reports: tuple[ReportRecord, ...]
    decisions: tuple[DecisionRecord, ...]
    counterfactuals: tuple[CounterfactualRecord, ...]


SyntheticDataRecord = (
    ScenarioRecord
    | HouseRecord
    | OrganizationRecord
    | ExternalEventRecord
    | IncidentRecord
    | ReportRecord
    | DecisionRecord
    | CounterfactualRecord
)
