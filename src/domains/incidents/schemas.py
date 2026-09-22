"""Litestar contracts generated from the incident aggregate."""

from dataclasses import dataclass
from typing import ClassVar

from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig

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


@dataclass
class IncidentDisputeRequest:
    comment: str


class ResolutionDisputeReadDTO(SQLAlchemyDTO[ResolutionDispute]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig()
