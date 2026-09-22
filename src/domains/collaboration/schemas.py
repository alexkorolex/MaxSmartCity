from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig

from src.domains.collaboration.enums import AssignmentStatus
from src.domains.collaboration.models import Assignment, WorkItem


class AssignmentCreateDTO(SQLAlchemyDTO[Assignment]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={
            "accepted_at",
            "completed_at",
            "created_at",
            "id",
            "started_at",
            "status",
            "updated_at",
            "version",
        },
        forbid_unknown_fields=True,
    )


class AssignmentUpdateDTO(SQLAlchemyDTO[Assignment]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={
            "accepted_at",
            "completed_at",
            "created_at",
            "id",
            "started_at",
            "status",
            "updated_at",
            "version",
        },
        forbid_unknown_fields=True,
        partial=True,
    )


class AssignmentReadDTO(SQLAlchemyDTO[Assignment]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig()


@dataclass(slots=True)
class TransitionAssignmentCommand:
    target_status: AssignmentStatus
    expected_version: int
    reason: str | None = None


@dataclass(slots=True)
class TransitionAssignmentResult:
    assignment_id: UUID
    status: AssignmentStatus
    version: int


class WorkItemCreateDTO(SQLAlchemyDTO[WorkItem]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"completed_at", "created_at", "id", "status", "updated_at", "version"},
        forbid_unknown_fields=True,
    )


class WorkItemUpdateDTO(SQLAlchemyDTO[WorkItem]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"completed_at", "created_at", "id", "status", "updated_at", "version"},
        forbid_unknown_fields=True,
        partial=True,
    )


class WorkItemReadDTO(SQLAlchemyDTO[WorkItem]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig()
