"""Litestar contracts generated from the notifications domain's SQLAlchemy models."""

from dataclasses import dataclass
from typing import ClassVar

from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig

from src.domains.notifications.models import Notification


class NotificationReadDTO(SQLAlchemyDTO[Notification]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig()


@dataclass
class NotificationReadAllResponse:
    updated: int
