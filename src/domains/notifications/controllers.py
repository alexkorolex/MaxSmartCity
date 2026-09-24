from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, delete, get, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ClientException, NotFoundException, PermissionDeniedException
from litestar.params import FromPath, Parameter
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.models import utc_now
from src.database.logging import database_action
from src.domains.identity.admin_scope import is_platform_admin, resolve_organization_scope
from src.domains.identity.models import Organization
from src.domains.notifications.channels import (
    ChannelConfigurationError,
    ChannelDeliveryError,
    ChannelTarget,
    OrganizationMessage,
    strategy_for,
)
from src.domains.notifications.enums import OrganizationChannelType
from src.domains.notifications.models import Notification, OrganizationChannel
from src.domains.notifications.schemas import (
    NotificationReadAllResponse,
    NotificationReadDTO,
    OrganizationChannelCreateRequest,
    OrganizationChannelReadDTO,
    OrganizationChannelTestResult,
)
from src.domains.notifications.services import NotificationService, OrganizationChannelService
from src.security.dependency import provide_principal
from src.security.guards import require_resident, require_roles
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


_STAFF_ADMIN_ROLES = ("admin", "district_admin", "housing_worker")


def provide_organization_channel_service(
    db_session: NamedDependency[AsyncSession],
) -> OrganizationChannelService:
    return OrganizationChannelService(session=db_session, auto_commit=True)


class OrganizationChannelController(Controller):
    """Where an organization (УК/ТСЖ) receives residents' requests - each row is one
    delivery strategy (see ``src.domains.notifications.channels``). ``admin`` manages any
    organization's channels, other staff only their own. ``WEBHOOK`` channels make the
    backend call an arbitrary URL, so only an ``admin`` may create them."""

    path = "/notifications/organization-channels"
    tags = ("notifications",)
    return_dto = OrganizationChannelReadDTO
    guards = (require_roles(*_STAFF_ADMIN_ROLES),)

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "service": Provide(provide_organization_channel_service, sync_to_thread=False),
            "principal": Provide(provide_principal),
        }

    @get("/", name="notifications:OrganizationChannel:list")
    async def list_items(
        self,
        service: NamedDependency[OrganizationChannelService],
        principal: NamedDependency[Principal],
        organization_id: Annotated[UUID | None, Parameter()] = None,
    ) -> Sequence[OrganizationChannel]:
        scope = resolve_organization_scope(principal, organization_id)
        if scope.sees_nothing:
            return []
        with database_action("list", "notifications.OrganizationChannel"):
            criteria = []
            if scope.organization_id is not None:
                criteria.append(OrganizationChannel.organization_id == scope.organization_id)
            return await service.list(*criteria, order_by=("created_at", False))

    @post("/", name="notifications:OrganizationChannel:create")
    async def create_item(
        self,
        data: OrganizationChannelCreateRequest,
        service: NamedDependency[OrganizationChannelService],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> OrganizationChannel:
        resolve_organization_scope(principal, data.organization_id)
        if data.type is OrganizationChannelType.WEBHOOK and not is_platform_admin(principal):
            raise PermissionDeniedException("Only an admin can configure a WEBHOOK channel")
        target = data.target.strip() if data.target and data.target.strip() else None
        try:
            strategy_for(data.type).validate(target, data.secret)
        except ChannelConfigurationError as exc:
            raise ClientException(status_code=400, detail=str(exc)) from exc
        with database_action("create", "notifications.OrganizationChannel"):
            if await db_session.get(Organization, data.organization_id) is None:
                raise NotFoundException(f"Organization {data.organization_id} was not found")
            return await service.create(
                OrganizationChannel(
                    organization_id=data.organization_id,
                    type=data.type,
                    target=target,
                    secret=data.secret or None,
                )
            )

    @post("/{item_id:uuid}/deactivate", status_code=200, name="notifications:OrganizationChannel:deactivate")
    async def deactivate(
        self,
        item_id: FromPath[UUID],
        service: NamedDependency[OrganizationChannelService],
        principal: NamedDependency[Principal],
    ) -> OrganizationChannel:
        await self._get_in_scope(service, principal, item_id)
        with database_action("update", "notifications.OrganizationChannel"):
            return await service.update({"is_active": False}, item_id=item_id)

    @post("/{item_id:uuid}/activate", status_code=200, name="notifications:OrganizationChannel:activate")
    async def activate(
        self,
        item_id: FromPath[UUID],
        service: NamedDependency[OrganizationChannelService],
        principal: NamedDependency[Principal],
    ) -> OrganizationChannel:
        await self._get_in_scope(service, principal, item_id)
        with database_action("update", "notifications.OrganizationChannel"):
            return await service.update({"is_active": True}, item_id=item_id)

    @delete("/{item_id:uuid}", return_dto=None, name="notifications:OrganizationChannel:delete")
    async def delete_item(
        self,
        item_id: FromPath[UUID],
        service: NamedDependency[OrganizationChannelService],
        principal: NamedDependency[Principal],
    ) -> None:
        await self._get_in_scope(service, principal, item_id)
        with database_action("delete", "notifications.OrganizationChannel"):
            await service.delete(item_id)

    @post(
        "/{item_id:uuid}/test",
        status_code=200,
        return_dto=None,
        name="notifications:OrganizationChannel:test",
    )
    async def send_test(
        self,
        item_id: FromPath[UUID],
        service: NamedDependency[OrganizationChannelService],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> OrganizationChannelTestResult:
        """Send a test message right away (bypassing the outbox) so the organization can
        check the channel is wired up correctly."""
        channel = await self._get_in_scope(service, principal, item_id)
        message = OrganizationMessage(
            organization_id=channel.organization_id,
            event_type="CHANNEL_TEST",
            title="Проверка канала уведомлений",
            body="Если вы видите это сообщение, заявки жителей будут приходить сюда.",
        )
        target = ChannelTarget(
            key=str(channel.id), type=channel.type, target=channel.target, secret=channel.secret
        )
        try:
            await strategy_for(channel.type).send(db_session, target, message)
        except ChannelDeliveryError as exc:
            return OrganizationChannelTestResult(delivered=False, error=str(exc))
        return OrganizationChannelTestResult(delivered=True)

    @staticmethod
    async def _get_in_scope(
        service: OrganizationChannelService, principal: Principal, item_id: UUID
    ) -> OrganizationChannel:
        with database_action("get", "notifications.OrganizationChannel"):
            channel = await service.get_one_or_none(id=item_id)
        if channel is None:
            raise NotFoundException(f"Channel {item_id} was not found")
        resolve_organization_scope(principal, channel.organization_id)
        return channel
