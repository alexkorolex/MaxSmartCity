from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, get, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import NotFoundException
from litestar.params import FromPath, Parameter
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.models import utc_now
from src.database.logging import database_action
from src.domains.notifications.models import Notification
from src.domains.notifications.schemas import NotificationReadAllResponse, NotificationReadDTO
from src.domains.notifications.services import NotificationService
from src.security.dependency import provide_principal
from src.security.guards import require_resident
from src.security.principal import Principal


def provide_notification_service(db_session: NamedDependency[AsyncSession]) -> NotificationService:
    return NotificationService(session=db_session, auto_commit=True)


class NotificationController(Controller):
    path = "/notifications"
    tags = ("notifications",)
    return_dto = NotificationReadDTO
    guards = (require_resident(),)

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "service": Provide(provide_notification_service, sync_to_thread=False),
            "principal": Provide(provide_principal),
        }

    @get("/", name="notifications:Notification:list")
    async def list_items(
        self,
        service: NamedDependency[NotificationService],
        principal: NamedDependency[Principal],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Notification]:
        with database_action("list", "notifications.Notification"):
            return await service.get_many(
                LimitOffset(limit=limit, offset=offset),
                Notification.resident_id == principal.actor_id,
                order_by=("created_at", True),
            )

    @post("/{item_id:uuid}/read", name="notifications:Notification:read")
    async def mark_read(
        self,
        item_id: FromPath[UUID],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> Notification:
        with database_action("update", "notifications.Notification"):
            notification = (
                await db_session.execute(
                    select(Notification).where(
                        Notification.id == item_id,
                        Notification.resident_id == principal.actor_id,
                    )
                )
            ).scalar_one_or_none()
            if notification is None:
                raise NotFoundException("Notification not found")

            notification.is_read = True
            notification.read_at = utc_now()
            await db_session.commit()
            return notification

    @post("/read-all", name="notifications:Notification:read-all", return_dto=None)
    async def mark_all_read(
        self,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> NotificationReadAllResponse:
        with database_action("update", "notifications.Notification"):
            result = await db_session.execute(
                update(Notification)
                .where(
                    Notification.resident_id == principal.actor_id,
                    Notification.is_read.is_(False),
                )
                .values(is_read=True, read_at=utc_now())
            )
            await db_session.commit()
            return NotificationReadAllResponse(updated=result.rowcount)  # ty: ignore[unresolved-attribute]
