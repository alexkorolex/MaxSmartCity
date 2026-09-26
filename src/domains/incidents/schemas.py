"""Litestar contracts generated from the incident aggregate."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar
from uuid import UUID

from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig

from src.domains.incidents.enums import (
    GroupingMode,
    GroupingOutcome,
    IncidentStatus,
    ResolutionFeedback,
)
from src.domains.incidents.models import Incident, ResolutionDispute


class IncidentCreateDTO(SQLAlchemyDTO[Incident]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={
            "id",
            "created_at",
            "updated_at",
            "version",
            "status",
            "first_report_at",
            "last_report_at",
            "resolved_at",
            "closed_at",
        },
        forbid_unknown_fields=True,
    )


class IncidentReadDTO(SQLAlchemyDTO[Incident]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig()


class IncidentUpdateDTO(SQLAlchemyDTO[Incident]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={
            "id",
            "created_at",
            "updated_at",
            "version",
            "status",
            "first_report_at",
            "last_report_at",
            "resolved_at",
            "closed_at",
        },
        partial=True,
        forbid_unknown_fields=True,
    )


@dataclass(slots=True)
class GroupReportCommand:
    mode: GroupingMode = GroupingMode.AUTO
    confirmed_incident_id: UUID | None = None
    request_id: UUID | None = None


@dataclass(slots=True)
class GroupingCandidate:
    incident_id: UUID
    title: str
    description: str | None
    score: float | None = None


@dataclass(slots=True)
class GroupReportResult:
    report_id: UUID
    outcome: GroupingOutcome
    incident_id: UUID | None
    score: float | None
    candidate_incident_ids: list[UUID] = field(default_factory=list)
    candidate_incidents: list[GroupingCandidate] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    policy_version: str = ""
    scorer_version: str = ""


@dataclass(slots=True)
class TransitionIncidentCommand:
    target_status: IncidentStatus
    expected_version: int
    reason: str | None = None


@dataclass(slots=True)
class TransitionIncidentResult:
    incident_id: UUID
    status: IncidentStatus
    version: int


@dataclass(slots=True)
class CompleteIncidentCommand:
    """A staff member reports the work as done - see ``IncidentCoreService.complete_by_staff``."""

    comment: str | None = None


@dataclass(slots=True)
class CloseReportCommand:
    """A resident closes their own report because the problem went away."""

    comment: str | None = None


@dataclass(slots=True)
class CloseReportResult:
    report_id: UUID
    report_status: str
    incident_id: UUID | None
    incident_status: IncidentStatus | None


@dataclass(slots=True)
class ResolutionFeedbackCommand:
    report_id: UUID
    feedback: ResolutionFeedback
    comment: str | None = None


@dataclass(slots=True)
class ResolutionFeedbackResult:
    incident_id: UUID
    report_id: UUID
    incident_status: IncidentStatus
    feedback: ResolutionFeedback


@dataclass(slots=True)
class ResidentIncidentReportResult:
    report_id: UUID
    has_open_dispute: bool


@dataclass(slots=True)
class IncidentHouseSummary:
    house_id: UUID
    address: str


@dataclass(slots=True)
class IncidentReportSummary:
    report_id: UUID
    text: str | None
    status: str
    received_at: datetime
    problem_continues: bool | None


@dataclass(slots=True)
class IncidentAssignmentSummary:
    assignment_id: UUID
    organization_id: UUID
    role: str
    status: str
    due_at: datetime | None


@dataclass(slots=True)
class IncidentHistorySummary:
    from_status: str | None
    to_status: str
    reason: str | None
    created_at: datetime


@dataclass(slots=True)
class IncidentDisputeSummary:
    dispute_id: UUID
    report_id: UUID | None
    status: str
    comment: str | None
    created_at: datetime


@dataclass(slots=True)
class IncidentCardResult:
    incident_id: UUID
    title: str
    description: str | None
    category_id: UUID
    status: IncidentStatus
    priority: str
    version: int
    first_report_at: datetime | None
    last_report_at: datetime | None
    houses: list[IncidentHouseSummary] = field(default_factory=list)
    reports: list[IncidentReportSummary] = field(default_factory=list)
    assignments: list[IncidentAssignmentSummary] = field(default_factory=list)
    disputes: list[IncidentDisputeSummary] = field(default_factory=list)
    history: list[IncidentHistorySummary] = field(default_factory=list)


@dataclass(slots=True)
class IncidentDisputeRequest:
    comment: str


class ResolutionDisputeReadDTO(SQLAlchemyDTO[ResolutionDispute]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig()
