from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.models import utc_now
from src.domains.correspondence.models import Conversation, ConversationMessage
from src.domains.correspondence.schemas import (
    ConversationMessageView,
    ConversationSummary,
    ConversationThread,
    CorrespondenceContact,
)
from src.domains.identity.admin_scope import AUTHORITY_ROLE, is_platform_admin
from src.domains.identity.models import OperatorUser, Organization
from src.domains.identity.validation import HOUSING_ORGANIZATION_TYPES
from src.domains.incidents.scope import visible_organization_ids
from src.security.principal import Principal

PLATFORM_NAME = "Администрация платформы"
MAX_SUBJECT_LENGTH = 255
MAX_TEXT_LENGTH = 4000


class CorrespondenceNotFoundError(RuntimeError):
    pass


class CorrespondenceForbiddenError(RuntimeError):
    pass


class CorrespondenceConflictError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Side:
    organization_id: UUID | None
    is_authority: bool

    @property
    def is_platform(self) -> bool:
        return self.organization_id is None


def side_of(principal: Principal) -> Side:
    if is_platform_admin(principal):
        return Side(organization_id=None, is_authority=False)
    if principal.organization_id is None:
        raise CorrespondenceForbiddenError("No active organization membership")
    return Side(organization_id=principal.organization_id, is_authority=principal.has_role(AUTHORITY_ROLE))


def _clean(text: str, limit: int, what: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        raise CorrespondenceConflictError(f"{what} is empty")
    if len(cleaned) > limit:
        raise CorrespondenceConflictError(f"{what} is longer than {limit} characters")
    return cleaned


def _participates(side: Side) -> ColumnElement[bool]:
    if side.is_platform:
        return Conversation.counterpart_organization_id.is_(None)
    return or_(
        Conversation.organization_id == side.organization_id,
        Conversation.counterpart_organization_id == side.organization_id,
    )


def _from_other_side(side: Side) -> ColumnElement[bool]:
    if side.is_platform:
        return ConversationMessage.author_organization_id.is_not(None)
    return or_(
        ConversationMessage.author_organization_id.is_(None),
        ConversationMessage.author_organization_id != side.organization_id,
    )


def _is_first_side(conversation: Conversation, side: Side) -> bool:
    return not side.is_platform and conversation.organization_id == side.organization_id


class CorrespondenceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.marked_read = False

    async def contacts(self, side: Side) -> list[CorrespondenceContact]:
        if side.is_platform:
            rows = (
                await self.session.execute(
                    select(Organization.id, Organization.name, Organization.type)
                    .where(Organization.enabled.is_(True))
                    .order_by(Organization.name)
                )
            ).all()
            return [
                CorrespondenceContact(organization_id=row.id, name=row.name, kind=row.type.value)
                for row in rows
            ]
        if not side.is_authority:
            return []
        assert side.organization_id is not None
        rows = (
            await self.session.execute(
                select(Organization.id, Organization.name, Organization.type)
                .where(
                    Organization.id.in_(visible_organization_ids(side.organization_id)),
                    Organization.id != side.organization_id,
                    Organization.type.in_(HOUSING_ORGANIZATION_TYPES),
                )
                .order_by(Organization.name)
            )
        ).all()
        return [
            CorrespondenceContact(organization_id=None, name=PLATFORM_NAME, kind="PLATFORM"),
            *(
                CorrespondenceContact(organization_id=row.id, name=row.name, kind=row.type.value)
                for row in rows
            ),
        ]

    async def start(
        self, side: Side, *, operator_id: UUID, target_id: UUID | None, subject: str, text: str
    ) -> Conversation:
        subject = _clean(subject, MAX_SUBJECT_LENGTH, "Subject")
        text = _clean(text, MAX_TEXT_LENGTH, "Message")
        allowed = {contact.organization_id for contact in await self.contacts(side)}
        if target_id not in allowed or (side.is_platform and target_id is None):
            raise CorrespondenceForbiddenError("You cannot start a conversation with this organization")
        if side.is_platform:
            first, counterpart = target_id, None
        else:
            first, counterpart = side.organization_id, target_id
        assert first is not None
        now = utc_now()
        conversation = Conversation(
            organization_id=first,
            counterpart_organization_id=counterpart,
            subject=subject,
            created_by=operator_id,
            last_message_at=now,
        )
        self._set_read(conversation, side, now)
        self.session.add(conversation)
        await self.session.flush()
        self.session.add(
            ConversationMessage(
                conversation_id=conversation.id,
                author_operator_id=operator_id,
                author_organization_id=side.organization_id,
                text=text,
            )
        )
        await self.session.flush()
        return conversation

    async def post(self, side: Side, conversation_id: UUID, *, operator_id: UUID, text: str) -> None:
        conversation = await self._get(side, conversation_id)
        text = _clean(text, MAX_TEXT_LENGTH, "Message")
        now = utc_now()
        self.session.add(
            ConversationMessage(
                conversation_id=conversation.id,
                author_operator_id=operator_id,
                author_organization_id=side.organization_id,
                text=text,
            )
        )
        conversation.last_message_at = now
        self._set_read(conversation, side, now)
        await self.session.flush()

    async def thread(self, side: Side, conversation_id: UUID) -> ConversationThread:
        conversation = await self._get(side, conversation_id)
        await self._mark_read(conversation, side)
        names = await self._organization_names(conversation)
        rows = (
            await self.session.execute(
                select(ConversationMessage, OperatorUser.display_name)
                .join(OperatorUser, OperatorUser.id == ConversationMessage.author_operator_id)
                .where(ConversationMessage.conversation_id == conversation.id)
                .order_by(ConversationMessage.created_at, ConversationMessage.id)
            )
        ).all()
        return ConversationThread(
            id=conversation.id,
            subject=conversation.subject,
            counterpart_name=self._counterpart_name(conversation, side, names),
            counterpart_read_at=(
                conversation.counterpart_read_at
                if _is_first_side(conversation, side)
                else conversation.organization_read_at
            ),
            messages=[
                ConversationMessageView(
                    id=message.id,
                    text=message.text,
                    created_at=message.created_at,
                    author_name=author,
                    organization_name=names.get(message.author_organization_id, PLATFORM_NAME),
                    is_mine=message.author_organization_id == side.organization_id,
                )
                for message, author in rows
            ],
        )

    async def inbox(self, side: Side) -> list[ConversationSummary]:
        conversations = (
            await self.session.scalars(
                select(Conversation).where(_participates(side)).order_by(Conversation.last_message_at.desc())
            )
        ).all()
        summaries = []
        for conversation in conversations:
            own_read_at = (
                conversation.organization_read_at
                if _is_first_side(conversation, side)
                else conversation.counterpart_read_at
            )
            unread_filter = [ConversationMessage.conversation_id == conversation.id, _from_other_side(side)]
            if own_read_at is not None:
                unread_filter.append(ConversationMessage.created_at > own_read_at)
            unread = await self.session.scalar(
                select(func.count()).select_from(ConversationMessage).where(and_(*unread_filter))
            )
            last_text = await self.session.scalar(
                select(ConversationMessage.text)
                .where(ConversationMessage.conversation_id == conversation.id)
                .order_by(ConversationMessage.created_at.desc())
                .limit(1)
            )
            summaries.append(
                ConversationSummary(
                    id=conversation.id,
                    subject=conversation.subject,
                    counterpart_name=self._counterpart_name(
                        conversation, side, await self._organization_names(conversation)
                    ),
                    last_message_text=last_text,
                    last_message_at=conversation.last_message_at,
                    unread_count=unread or 0,
                )
            )
        return summaries

    async def has_changes_since(self, side: Side, conversation_id: UUID, since: datetime | None) -> bool:
        conversation = await self._get(side, conversation_id)
        if since is None:
            return True
        other_read_at = (
            conversation.counterpart_read_at
            if _is_first_side(conversation, side)
            else conversation.organization_read_at
        )
        if other_read_at is not None and other_read_at > since:
            return True
        newer = await self.session.scalar(
            select(ConversationMessage.id)
            .where(
                ConversationMessage.conversation_id == conversation.id, ConversationMessage.created_at > since
            )
            .limit(1)
        )
        return newer is not None

    async def _mark_read(self, conversation: Conversation, side: Side) -> None:
        own_read_at = (
            conversation.organization_read_at
            if _is_first_side(conversation, side)
            else conversation.counterpart_read_at
        )
        unread = [
            ConversationMessage.conversation_id == conversation.id,
            _from_other_side(side),
        ]
        if own_read_at is not None:
            unread.append(ConversationMessage.created_at > own_read_at)
        if await self.session.scalar(select(ConversationMessage.id).where(*unread).limit(1)) is None:
            return
        self._set_read(conversation, side, utc_now())
        self.marked_read = True
        await self.session.flush()

    async def _get(self, side: Side, conversation_id: UUID) -> Conversation:
        conversation = await self.session.scalar(
            select(Conversation).where(Conversation.id == conversation_id, _participates(side))
        )
        if conversation is None:
            raise CorrespondenceNotFoundError(f"Conversation {conversation_id} was not found")
        return conversation

    async def _organization_names(self, conversation: Conversation) -> dict[UUID | None, str]:
        ids = [conversation.organization_id, conversation.counterpart_organization_id]
        rows = (
            await self.session.execute(
                select(Organization.id, Organization.name).where(Organization.id.in_([i for i in ids if i]))
            )
        ).all()
        return {None: PLATFORM_NAME, **{row.id: row.name for row in rows}}

    @staticmethod
    def _counterpart_name(conversation: Conversation, side: Side, names: dict[UUID | None, str]) -> str:
        if _is_first_side(conversation, side):
            return names.get(conversation.counterpart_organization_id, PLATFORM_NAME)
        return names.get(conversation.organization_id, PLATFORM_NAME)

    @staticmethod
    def _set_read(conversation: Conversation, side: Side, moment: datetime) -> None:
        if _is_first_side(conversation, side):
            conversation.organization_read_at = moment
        else:
            conversation.counterpart_read_at = moment
