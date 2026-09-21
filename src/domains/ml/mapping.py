"""Map backend-owned entities into the versioned ML request contract."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import TypedDict
from uuid import UUID

from src.domains.incidents.enums import IncidentStatus
from src.domains.incidents.models import Incident
from src.domains.reports.models import Report

ML_CONTRACT_VERSION = "2.0.0-draft"
INACTIVE_INCIDENT_STATUSES = frozenset(
    {
        IncidentStatus.CLOSED,
        IncidentStatus.REJECTED,
        IncidentStatus.CANCELLED,
        IncidentStatus.MERGED,
    }
)


class MLReportPayload(TypedDict):
    report_id: str
    text: str
    created_at: str
    address_id: str | None
    house_id: str | None
    raw_address: str | None
    fias_guid: str | None
    category_hint: str | None


class MLIncidentCandidatePayload(TypedDict):
    id: str
    started_at: str
    category_id: str | None
    affected_house_ids: list[str]
    fias_guids: list[str]
    title: str
    status: str
    priority: str
    active: bool


class MLDecisionRequestPayload(TypedDict):
    contract_version: str
    request_id: str
    deadline_ms: int
    report: MLReportPayload
    candidate_incidents: list[MLIncidentCandidatePayload]
    candidate_organizations: list[dict[str, object]]
    allowed_actions: list[dict[str, object]]
    external_context: dict[str, object]


def build_decision_request(
    *,
    request_id: str,
    report: Report,
    incidents: Sequence[Incident],
    category_codes: Mapping[UUID, str],
    incident_house_ids: Mapping[UUID, Sequence[UUID]],
    deadline_ms: int = 5_000,
) -> MLDecisionRequestPayload:
    """Build a read-only candidate snapshot; this function never links or updates entities."""
    if deadline_ms < 1:
        raise ValueError("deadline_ms must be positive")
    report_created_at = _timestamp(report.occurred_at or report.created_at)
    candidates: list[MLIncidentCandidatePayload] = [
        {
            "id": str(incident.id),
            "started_at": _timestamp(incident.first_report_at or incident.created_at),
            "category_id": category_codes.get(incident.category_id),
            "affected_house_ids": [str(house_id) for house_id in incident_house_ids.get(incident.id, ())],
            "fias_guids": [],
            "title": incident.title,
            "status": incident.status.value,
            "priority": incident.priority.value,
            "active": incident.status not in INACTIVE_INCIDENT_STATUSES,
        }
        for incident in incidents
    ]
    return {
        "contract_version": ML_CONTRACT_VERSION,
        "request_id": request_id,
        "deadline_ms": deadline_ms,
        "report": {
            "report_id": str(report.id),
            "text": report.text or "",
            "created_at": report_created_at,
            "address_id": str(report.address_id) if report.address_id else None,
            "house_id": str(report.house_id) if report.house_id else None,
            "raw_address": None,
            "fias_guid": None,
            "category_hint": category_codes.get(report.category_id),
        },
        "candidate_incidents": candidates,
        "candidate_organizations": [],
        "allowed_actions": [],
        "external_context": {"source": "backend-candidate-snapshot-v1"},
    }


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("ML snapshot timestamps must include a timezone")
    return value.isoformat()
