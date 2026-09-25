"""Announcing chat messages the recipient hasn't read - they're not in the chat, so they
get told where they are: the resident in MAX (plus an in-app notification), the
organization through its notification channels. Runs as a background job
(``src.background``)."""

from collections import defaultdict
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.enums import ActorType
from src.common.models import utc_now
from src.domains.identity.models import Resident
from src.domains.notifications.dispatcher import OrganizationMessage, enqueue_organization_notification
from src.domains.notifications.enums import NotificationType
from src.domains.notifications.models import Notification
from src.domains.reports.chat.participants import report_organizations
from src.domains.reports.models import Report, ReportMessage
from src.max_bot.links import max_profile_url
from src.settings import admin_panel_url

UNREAD_NOTIFICATION_DELAY = timedelta(minutes=1)
"""How long a message may stay unread before the recipient is assumed not to be in the chat
(an open chat reads new messages within seconds)."""
PREVIEW_MESSAGES = 3
REPLY_HINT = "Ответить можно в приложении Smart City - в чате по обращению."


def _preview(messages: list[ReportMessage]) -> str:
    shown = messages[-PREVIEW_MESSAGES:]
    text = "\n".join(f"— {message.text}" for message in shown)
    if len(messages) > len(shown):
        text = f"(и ещё {len(messages) - len(shown)})\n" + text
    return text


async def notify_unread_chat_messages(session: AsyncSession, *, limit: int = 200) -> int:
    """One notification per report and direction, however many messages piled up. The
    caller owns the transaction (commits afterwards)."""
    messages = (
        await session.scalars(
            select(ReportMessage)
            .where(
                ReportMessage.read_at.is_(None),
                ReportMessage.notified_at.is_(None),
                ReportMessage.created_at <= utc_now() - UNREAD_NOTIFICATION_DELAY,
            )
            .order_by(ReportMessage.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    ).all()
    grouped: dict[tuple[UUID, ActorType], list[ReportMessage]] = defaultdict(list)
    for message in messages:
        grouped[(message.report_id, message.author_type)].append(message)

    for (report_id, author_type), batch in grouped.items():
        report = await session.get(Report, report_id)
        if report is None or report.resident_id is None:
            continue
        resident = await session.get(Resident, report.resident_id)
        if author_type is ActorType.RESIDENT:
            await _notify_organizations(session, report, resident, batch)
        elif resident is not None:
            await _notify_resident(session, report, resident, batch)
    now = utc_now()
    for message in messages:
        message.notified_at = now
    await session.flush()
    return len(messages)


async def _notify_organizations(
    session: AsyncSession, report: Report, resident: Resident | None, batch: list[ReportMessage]
) -> None:
    name = (resident.display_name if resident else None) or "Житель"
    lines = [f"Обращение: {report.text}" if report.text else None, f"От: {name}"]
    profile = max_profile_url(resident.username) if resident else None
    if profile:
        lines.append(f"Профиль MAX: {profile}")
    lines.append("")
    lines.append(_preview(batch))
    panel = admin_panel_url()
    if panel:
        lines.append(f"\nОтветить: {panel}/reports/{report.id}/chat")
    for organization_id, _name in await report_organizations(session, report):
        enqueue_organization_notification(
            session,
            OrganizationMessage(
                organization_id=organization_id,
                event_type="CHAT_MESSAGE",
                title="Новое сообщение от жителя",
                body="\n".join(line for line in lines if line is not None),
                report_id=report.id,
                house_id=report.house_id,
            ),
        )


async def _notify_resident(
    session: AsyncSession, report: Report, resident: Resident, batch: list[ReportMessage]
) -> None:
    """In-app; the push job (``src.domains.notifications.resident_push``) also sends it to
    the resident in MAX, unless they turned that off."""
    subject = f" «{report.text[:60]}»" if report.text else ""
    session.add(
        Notification(
            resident_id=resident.id,
            type=NotificationType.CHAT_MESSAGE,
            title=f"Новое сообщение по обращению{subject}"[:255],
            body=f"{_preview(batch)}\n\n{REPLY_HINT}",
            report_id=report.id,
        )
    )
