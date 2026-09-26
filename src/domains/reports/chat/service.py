"""The chat between a resident and the organizations working on their report."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Row, and_, func, or_, select, true, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.enums import ActorType
from src.common.models import utc_now
from src.domains.geo.models import Address, House
from src.domains.identity.models import OperatorUser, Organization, Resident
from src.domains.incidents.scope import organization_report_ids
from src.domains.notifications.enums import NotificationType
from src.domains.notifications.models import Notification
from src.domains.reports.chat.participants import (
    ChatConflictError,
    ChatForbiddenError,
    report_organizations,
    resident_report,
    staff_report,
)
from src.domains.reports.chat.schemas import ChatConversationSummary, ChatMessageView, ChatThread
from src.domains.reports.models import Report, ReportMessage

MAX_MESSAGE_LENGTH = 4000
PLATFORM_NAME = "Администрация платформы"


def _clean_text(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        raise ChatConflictError("Message text is empty")
    if len(cleaned) > MAX_MESSAGE_LENGTH:
        raise ChatConflictError(f"Message is longer than {MAX_MESSAGE_LENGTH} characters")
    return cleaned


class ReportChatService:
    """Reading a thread marks the other side's messages read - that is what tells the
    notifier (``notifier.notify_unread_chat_messages``) the recipient is in the chat."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.marked_read = False
        """Whether this call marked any message read - the other side's "прочитано" changed,
        so the controller publishes a chat event once the transaction is committed."""

    async def has_changes_since(self, report_id: UUID, since: datetime | None) -> bool:
        """A message was written, or read, after ``since`` (any message, when ``None``)."""
        condition = true()
        if since is not None:
            condition = or_(ReportMessage.created_at > since, ReportMessage.read_at > since)
        found = await self.session.scalar(
            select(ReportMessage.id).where(ReportMessage.report_id == report_id, condition).limit(1)
        )
        return found is not None

    async def resident_thread(self, report_id: UUID, *, resident_id: UUID) -> ChatThread:
        report = await resident_report(self.session, report_id, resident_id)
        await self._mark_read(report.id, sent_by=ActorType.OPERATOR)
        await self._mark_chat_notifications_read(report.id, resident_id)
        organizations = await report_organizations(self.session, report)
        return ChatThread(
            report_id=report.id,
            report_text=report.text,
            counterparts=[name for _id, name in organizations],
            can_write=bool(organizations),
            messages=await self._messages(report.id, own_side=ActorType.RESIDENT),
        )

    async def staff_thread(self, report_id: UUID, *, organization_id: UUID | None) -> ChatThread:
        """``organization_id=None`` is the platform admin: an observer of every chat, who
        neither writes nor reads for the organization - looking doesn't mark anything read."""
        report = await staff_report(self.session, report_id, organization_id)
        if organization_id is not None:
            await self._mark_read(report.id, sent_by=ActorType.RESIDENT)
        resident_name = await self.session.scalar(
            select(Resident.display_name).where(Resident.id == report.resident_id)
        )
        return ChatThread(
            report_id=report.id,
            report_text=report.text,
            counterparts=[resident_name or "Житель"],
            can_write=organization_id is not None,
            messages=await self._messages(report.id, own_side=ActorType.OPERATOR),
        )

    async def post_as_resident(self, report_id: UUID, text: str, *, resident_id: UUID) -> ChatMessageView:
        report = await resident_report(self.session, report_id, resident_id)
        if not await report_organizations(self.session, report):
            raise ChatConflictError("No organization is working on this report yet")
        message = ReportMessage(
            report_id=report.id,
            author_type=ActorType.RESIDENT,
            author_resident_id=resident_id,
            text=_clean_text(text),
        )
        return await self._save(message, own_side=ActorType.RESIDENT)

    async def post_as_staff(
        self, report_id: UUID, text: str, *, operator_id: UUID, organization_id: UUID | None
    ) -> ChatMessageView:
        if organization_id is None:
            raise ChatForbiddenError("The platform admin only observes report chats")
        report = await staff_report(self.session, report_id, organization_id)
        message = ReportMessage(
            report_id=report.id,
            author_type=ActorType.OPERATOR,
            author_operator_id=operator_id,
            organization_id=organization_id,
            text=_clean_text(text),
        )
        # Answering implies having read what the resident wrote.
        await self._mark_read(report.id, sent_by=ActorType.RESIDENT)
        return await self._save(message, own_side=ActorType.OPERATOR)

    async def staff_conversations(
        self, *, organization_id: UUID | None, limit: int = 50
    ) -> list[ChatConversationSummary]:
        """The staff inbox: every report chat in scope, most recent first, with how many
        resident messages nobody on the organization's side has read yet."""
        unread = func.count().filter(
            and_(ReportMessage.author_type == ActorType.RESIDENT, ReportMessage.read_at.is_(None))
        )
        latest = (
            select(
                ReportMessage.report_id,
                func.max(ReportMessage.created_at).label("last_at"),
                unread.label("unread"),
            )
            .group_by(ReportMessage.report_id)
            .subquery()
        )
        statement = (
            select(
                Report.id,
                Report.text.label("report_text"),
                Address.formatted,
                Resident.display_name,
                ReportMessage.text.label("last_text"),
                ReportMessage.author_type,
                latest.c.last_at,
                latest.c.unread,
            )
            .join(latest, latest.c.report_id == Report.id)
            .join(
                ReportMessage,
                and_(ReportMessage.report_id == Report.id, ReportMessage.created_at == latest.c.last_at),
            )
            .outerjoin(Resident, Resident.id == Report.resident_id)
            .outerjoin(House, House.id == Report.house_id)
            .outerjoin(Address, Address.id == House.address_id)
            .order_by(latest.c.last_at.desc())
            .limit(limit)
        )
        if organization_id is not None:
            statement = statement.where(Report.id.in_(organization_report_ids(organization_id)))
        rows = (await self.session.execute(statement)).all()
        return [
            ChatConversationSummary(
                report_id=row.id,
                report_text=row.report_text,
                address=row.formatted,
                resident_name=row.display_name,
                last_message_text=row.last_text,
                last_message_at=row.last_at,
                last_message_from_resident=row.author_type is ActorType.RESIDENT,
                unread_count=row.unread,
            )
            for row in rows
        ]

    async def _mark_read(self, report_id: UUID, *, sent_by: ActorType) -> None:
        result = await self.session.execute(
            update(ReportMessage)
            .where(
                ReportMessage.report_id == report_id,
                ReportMessage.author_type == sent_by,
                ReportMessage.read_at.is_(None),
            )
            .values(read_at=utc_now())
        )
        if result.rowcount:  # ty: ignore[unresolved-attribute]
            self.marked_read = True

    async def _mark_chat_notifications_read(self, report_id: UUID, resident_id: UUID) -> None:
        """The resident is in the chat now - the "new message" notifications about it are
        read too, so the app's notification badge doesn't keep counting them."""
        await self.session.execute(
            update(Notification)
            .where(
                Notification.resident_id == resident_id,
                Notification.report_id == report_id,
                Notification.type == NotificationType.CHAT_MESSAGE,
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=utc_now())
        )

    async def _save(self, message: ReportMessage, *, own_side: ActorType) -> ChatMessageView:
        self.session.add(message)
        await self.session.flush()
        (view,) = [
            view
            for view in await self._messages(message.report_id, own_side=own_side)
            if view.id == message.id
        ]
        return view

    async def _messages(self, report_id: UUID, *, own_side: ActorType) -> list[ChatMessageView]:
        rows = (
            await self.session.execute(
                select(
                    ReportMessage,
                    Resident.display_name.label("resident_name"),
                    OperatorUser.display_name.label("operator_name"),
                    Organization.name.label("organization_name"),
                )
                .outerjoin(Resident, Resident.id == ReportMessage.author_resident_id)
                .outerjoin(OperatorUser, OperatorUser.id == ReportMessage.author_operator_id)
                .outerjoin(Organization, Organization.id == ReportMessage.organization_id)
                .where(ReportMessage.report_id == report_id)
                .order_by(ReportMessage.created_at, ReportMessage.id)
            )
        ).all()
        return [_view(row, own_side) for row in rows]


def _view(row: Row[Any], own_side: ActorType) -> ChatMessageView:
    message = row[0]
    if message.author_type is ActorType.RESIDENT:
        author_name, organization_name = row.resident_name or "Житель", None
    else:
        author_name = row.operator_name or "Сотрудник"
        organization_name = row.organization_name or PLATFORM_NAME
    return ChatMessageView(
        id=message.id,
        author_type=message.author_type.value,
        author_name=author_name,
        organization_name=organization_name,
        text=message.text,
        created_at=message.created_at,
        read_at=message.read_at,
        is_mine=message.author_type is own_side,
    )
