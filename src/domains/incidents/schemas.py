"""Litestar contracts generated from the incident aggregate."""

from dataclasses import dataclass, field
from typing import ClassVar
from uuid import UUID

from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig

from src.domains.incidents.enums import GroupingMode, GroupingOutcome, IncidentStatus
from src.domains.incidents.models import Incident


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
class GroupReportResult:
    report_id: UUID
    outcome: GroupingOutcome
    incident_id: UUID | None
    score: float | None
    candidate_incident_ids: list[UUID] = field(default_factory=list)
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
