from typing import ClassVar

from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig

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
