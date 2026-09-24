"""Litestar contracts generated from the notifications domain's SQLAlchemy models."""

from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig

from src.domains.notifications.enums import OrganizationChannelType
from src.domains.notifications.models import Notification, OrganizationChannel


class NotificationReadDTO(SQLAlchemyDTO[Notification]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig()


@dataclass
class NotificationReadAllResponse:
    updated: int


class OrganizationChannelReadDTO(SQLAlchemyDTO[OrganizationChannel]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(exclude={"secret"})


@dataclass
class OrganizationChannelCreateRequest:
    organization_id: UUID
    type: OrganizationChannelType
    target: str | None = None
    secret: str | None = None


@dataclass
class OrganizationChannelTestResult:
    delivered: bool
    error: str | None = None
