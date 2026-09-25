"""HTTP API of the resident <-> organization chat on a report."""

from collections.abc import Sequence
from datetime import datetime
from typing import Annotated
from uuid import UUID

from litestar import Controller, Router, get, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ClientException, NotFoundException, PermissionDeniedException
from litestar.params import FromPath, Parameter
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.enums import ActorType
from src.database.logging import database_action
from src.domains.identity.admin_scope import STAFF_ROLES, resolve_organization_scope
from src.domains.reports.chat import (
    MAX_WAIT_SECONDS,
    ChatConflictError,
    ChatConversationSummary,
    ChatEventBus,
    ChatMessageView,
    ChatNotFoundError,
    ChatThread,
    ChatUpdates,
    ReportChatService,
    SendChatMessageCommand,
    provide_chat_events,
)
from src.domains.reports.chat.participants import resident_report, staff_report
from src.security.dependency import provide_principal
from src.security.guards import require_roles
from src.security.principal import Principal


def _staff_organization(principal: Principal) -> UUID | None:
    """Which organization a staff member chats for: ``None`` for the platform admin (every
    chat), their own one otherwise. 404 for staff outside any organization - not 403, so a
    report's existence isn't revealed."""
    if not principal.has_role(*STAFF_ROLES):
        raise PermissionDeniedException("Staff or resident authentication required")
    scope = resolve_organization_scope(principal)
    if scope.sees_nothing:
        raise NotFoundException("Report was not found")
    return scope.organization_id


class ReportChatController(Controller):
    """One chat per report: the resident who filed it on one side, the organizations
    working on it (its house's УК/ТСЖ, assigned executors) on the other. The same endpoints
    serve both - the token says which side the caller is on. Reading marks the other side's
    messages read; anything left unread for a minute is announced out of the app."""

    path = "/reports/{report_id:uuid}/messages"
    tags = ("reports",)
    return_dto = None

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "principal": Provide(provide_principal),
            "chat_events": Provide(provide_chat_events, sync_to_thread=False),
        }

    @get("/", name="reports:ReportChat:thread")
    async def thread(
        self,
        report_id: FromPath[UUID],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        chat_events: NamedDependency[ChatEventBus],
    ) -> ChatThread:
        service = ReportChatService(db_session)
        try:
            with database_action("list", "reports.ReportMessage"):
                if principal.actor_type is ActorType.RESIDENT:
                    thread = await service.resident_thread(report_id, resident_id=principal.actor_id)
                else:
                    organization_id = _staff_organization(principal)
                    thread = await service.staff_thread(report_id, organization_id=organization_id)
        except ChatNotFoundError as exc:
            raise NotFoundException(str(exc)) from exc
        await db_session.commit()
        if service.marked_read:
            await chat_events.publish(report_id)  # the writer's "прочитано" appears right away
        return thread

    @get("/updates", name="reports:ReportChat:updates")
    async def updates(
        self,
        report_id: FromPath[UUID],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        chat_events: NamedDependency[ChatEventBus],
        since: Annotated[datetime | None, Parameter()] = None,
    ) -> ChatUpdates:
        """Long poll: answers as soon as the chat changes after ``since`` (the latest
        ``created_at``/``read_at`` the client has), or with ``changed=false`` after
        ``MAX_WAIT_SECONDS`` - the client then simply asks again. Holds no database
        connection while waiting."""
        try:
            if principal.actor_type is ActorType.RESIDENT:
                await resident_report(db_session, report_id, principal.actor_id)
            else:
                await staff_report(db_session, report_id, _staff_organization(principal))
        except ChatNotFoundError as exc:
            raise NotFoundException(str(exc)) from exc
        async with chat_events.subscribe(report_id) as subscription:
            changed = await ReportChatService(db_session).has_changes_since(report_id, since)
            await db_session.commit()
            if not changed:
                changed = await subscription.wait(MAX_WAIT_SECONDS)
        return ChatUpdates(changed=changed)

    @post("/", name="reports:ReportChat:send")
    async def send(
        self,
        report_id: FromPath[UUID],
        data: SendChatMessageCommand,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        chat_events: NamedDependency[ChatEventBus],
    ) -> ChatMessageView:
        service = ReportChatService(db_session)
        try:
            with database_action("create", "reports.ReportMessage"):
                if principal.actor_type is ActorType.RESIDENT:
                    message = await service.post_as_resident(
                        report_id, data.text, resident_id=principal.actor_id
                    )
                else:
                    message = await service.post_as_staff(
                        report_id,
                        data.text,
                        operator_id=principal.actor_id,
                        organization_id=_staff_organization(principal),
                    )
        except ChatNotFoundError as exc:
            raise NotFoundException(str(exc)) from exc
        except ChatConflictError as exc:
            raise ClientException(status_code=409, detail=str(exc)) from exc
        await db_session.commit()
        await chat_events.publish(report_id)
        return message


class ChatInboxController(Controller):
    """The staff inbox: report chats of the caller's organization (every chat for the admin)."""

    path = "/chat"
    tags = ("reports",)
    return_dto = None

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "principal": Provide(provide_principal),
            "chat_events": Provide(provide_chat_events, sync_to_thread=False),
        }

    @get("/conversations", name="reports:ReportChat:conversations", guards=[require_roles(*STAFF_ROLES)])
    async def conversations(
        self,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        limit: Annotated[int, Parameter(ge=1, le=200)] = 50,
    ) -> Sequence[ChatConversationSummary]:
        scope = resolve_organization_scope(principal)
        if scope.sees_nothing:
            return []
        with database_action("list", "reports.ReportMessage"):
            return await ReportChatService(db_session).staff_conversations(
                organization_id=scope.organization_id, limit=limit
            )
