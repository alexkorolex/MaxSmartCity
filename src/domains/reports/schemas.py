"""Litestar contracts generated from the report domain's SQLAlchemy models."""

from typing import ClassVar

from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig

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
