"""Litestar contracts generated from the report domain's SQLAlchemy models."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar
from uuid import UUID

from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig

from src.common.enums import Priority
from src.domains.incidents.schemas import GroupReportResult
from src.domains.reports.models import ProblemCategory, Report


class ProblemCategoryCreateDTO(SQLAlchemyDTO[ProblemCategory]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"id", "created_at", "updated_at"}, forbid_unknown_fields=True
    )


class ProblemCategoryReadDTO(SQLAlchemyDTO[ProblemCategory]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig()


class ProblemCategoryUpdateDTO(SQLAlchemyDTO[ProblemCategory]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"id", "created_at", "updated_at"}, partial=True, forbid_unknown_fields=True
    )


class ReportCreateDTO(SQLAlchemyDTO[Report]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"id", "created_at", "updated_at", "status", "received_at"},
        forbid_unknown_fields=True,
    )


class ReportReadDTO(SQLAlchemyDTO[Report]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig()


class ReportUpdateDTO(SQLAlchemyDTO[Report]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"id", "created_at", "updated_at", "status", "received_at"},
        partial=True,
        forbid_unknown_fields=True,
    )


@dataclass(slots=True)
class CreateReportCommand:
    source_external_id: str
    house_id: UUID
    category_code: str
    text: str
    urgency: Priority | None = None
    problem_continues: bool | None = None
    occurred_at: datetime | None = None
    request_id: UUID | None = None


@dataclass(slots=True)
class CreateReportResult:
    report_id: UUID
    grouping: GroupReportResult


@dataclass
class ReportAttachmentRead:
    """Response shape for an uploaded attachment - ``download_url`` is a freshly generated
    presigned GET URL, never the bare ``storage_key`` (the bucket is private)."""

    id: str
    original_name: str | None
    mime_type: str
    size_bytes: int
    created_at: datetime
    download_url: str
