"""Input snapshot and allow-listed candidate domain objects."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ReportInput:
    report_id: str
    text: str
    created_at: datetime
    address_id: str | None = None
    house_id: str | None = None
    raw_address: str | None = None
    fias_guid: str | None = None
    category_hint: str | None = None


@dataclass(frozen=True, slots=True)
class IncidentCandidate:
    id: str
    started_at: datetime
    category_id: str | None = None
    affected_house_ids: tuple[str, ...] = ()
    fias_guids: tuple[str, ...] = ()
    title: str = ""
    status: str = "NEW"
    priority: str = "NORMAL"
    active: bool = True


@dataclass(frozen=True, slots=True)
class OrganizationCandidate:
    id: str
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ActionCandidate:
    id: str
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DecisionRequest:
    request_id: str
    report: ReportInput
    incident_candidates: tuple[IncidentCandidate, ...] = ()
    organization_candidates: tuple[OrganizationCandidate, ...] = ()
    action_candidates: tuple[ActionCandidate, ...] = ()
    external_context: dict[str, object] = field(default_factory=dict)
