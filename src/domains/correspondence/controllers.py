from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated
from uuid import UUID

from litestar import Controller, Router, get, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ClientException, NotFoundException, PermissionDeniedException
from litestar.params import FromPath, Parameter
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.correspondence.schemas import (
    ConversationSummary,
    ConversationThread,
    ConversationUpdates,
    CorrespondenceContact,
    SendMessageCommand,
    StartConversationCommand,
)
from src.domains.correspondence.services import (
    CorrespondenceConflictError,
    CorrespondenceForbiddenError,
    CorrespondenceNotFoundError,
    CorrespondenceService,
    side_of,
)
from src.domains.identity.admin_scope import STAFF_ROLES
from src.domains.reports.chat import MAX_WAIT_SECONDS, ChatEventBus, provide_chat_events
from src.security.dependency import provide_principal
from src.security.guards import require_roles
from src.security.principal import Principal


@asynccontextmanager
async def _correspondence_errors() -> AsyncIterator[None]:
    try:
        yield
    except CorrespondenceNotFoundError as exc:
        raise NotFoundException(str(exc)) from exc
    except CorrespondenceForbiddenError as exc:
        raise PermissionDeniedException(str(exc)) from exc
    except CorrespondenceConflictError as exc:
        raise ClientException(status_code=409, detail=str(exc)) from exc


class CorrespondenceController(Controller):
    path = "/correspondence"
    tags = ("correspondence",)
    return_dto = None

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "principal": Provide(provide_principal),
            "chat_events": Provide(provide_chat_events, sync_to_thread=False),
        }

    @get("/contacts", name="correspondence:contacts", guards=[require_roles(*STAFF_ROLES)])
    async def contacts(
        self, db_session: NamedDependency[AsyncSession], principal: NamedDependency[Principal]
    ) -> Sequence[CorrespondenceContact]:
        async with _correspondence_errors():
            with database_action("list", "identity.Organization"):
                return await CorrespondenceService(db_session).contacts(side_of(principal))

    @get("/conversations", name="correspondence:inbox", guards=[require_roles(*STAFF_ROLES)])
    async def inbox(
        self, db_session: NamedDependency[AsyncSession], principal: NamedDependency[Principal]
    ) -> Sequence[ConversationSummary]:
        async with _correspondence_errors():
            with database_action("list", "correspondence.Conversation"):
                return await CorrespondenceService(db_session).inbox(side_of(principal))

    @post("/conversations", name="correspondence:start", guards=[require_roles(*STAFF_ROLES)])
    async def start(
        self,
        data: StartConversationCommand,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> ConversationThread:
        async with _correspondence_errors():
            with database_action("create", "correspondence.Conversation"):
                service = CorrespondenceService(db_session)
                side = side_of(principal)
                conversation = await service.start(
                    side,
                    operator_id=principal.actor_id,
                    target_id=data.organization_id,
                    subject=data.subject,
                    text=data.text,
                )
                thread = await service.thread(side, conversation.id)
                await db_session.commit()
                return thread

    @get(
        "/conversations/{conversation_id:uuid}",
        name="correspondence:thread",
        guards=[require_roles(*STAFF_ROLES)],
    )
    async def thread(
        self,
        conversation_id: FromPath[UUID],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        chat_events: NamedDependency[ChatEventBus],
    ) -> ConversationThread:
        async with _correspondence_errors():
            with database_action("list", "correspondence.Message"):
                service = CorrespondenceService(db_session)
                thread = await service.thread(side_of(principal), conversation_id)
                await db_session.commit()
        if service.marked_read:
            await chat_events.publish(conversation_id)
        return thread

    @post(
        "/conversations/{conversation_id:uuid}/messages",
        name="correspondence:send",
        guards=[require_roles(*STAFF_ROLES)],
    )
    async def send(
        self,
        conversation_id: FromPath[UUID],
        data: SendMessageCommand,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        chat_events: NamedDependency[ChatEventBus],
    ) -> ConversationThread:
        async with _correspondence_errors():
            with database_action("create", "correspondence.Message"):
                service = CorrespondenceService(db_session)
                side = side_of(principal)
                await service.post(side, conversation_id, operator_id=principal.actor_id, text=data.text)
                thread = await service.thread(side, conversation_id)
                await db_session.commit()
        await chat_events.publish(conversation_id)
        return thread

    @get(
        "/conversations/{conversation_id:uuid}/updates",
        name="correspondence:updates",
        guards=[require_roles(*STAFF_ROLES)],
    )
    async def updates(
        self,
        conversation_id: FromPath[UUID],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        chat_events: NamedDependency[ChatEventBus],
        since: Annotated[datetime | None, Parameter()] = None,
    ) -> ConversationUpdates:
        async with _correspondence_errors(), chat_events.subscribe(conversation_id) as subscription:
            changed = await CorrespondenceService(db_session).has_changes_since(
                side_of(principal), conversation_id, since
            )
            await db_session.commit()
            if not changed:
                changed = await subscription.wait(MAX_WAIT_SECONDS)
        return ConversationUpdates(changed=changed)
