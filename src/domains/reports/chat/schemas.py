"""Contracts of the resident <-> organization chat on a report."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class SendChatMessageCommand:
    text: str


@dataclass(slots=True)
class ChatMessageView:
    id: UUID
    author_type: str
    """``RESIDENT`` or ``OPERATOR`` (a staff member writing for their organization)."""
    author_name: str
    organization_name: str | None
    text: str
    created_at: datetime
    read_at: datetime | None
    is_mine: bool
    """Written by the caller's side - the resident, or the caller's organization."""


@dataclass(slots=True)
class ChatThread:
    report_id: UUID
    report_text: str | None
    counterparts: list[str]
    """Who is on the other side: organizations working on the report (for the resident), or
    the resident's name (for staff)."""
    can_write: bool
    messages: list[ChatMessageView]


@dataclass(slots=True)
class ChatConversationSummary:
    """One report's chat in the staff inbox."""

    report_id: UUID
    report_text: str | None
    address: str | None
    resident_name: str | None
    last_message_text: str
    last_message_at: datetime
    last_message_from_resident: bool
    unread_count: int


@dataclass(slots=True)
class ChatUpdates:
    changed: bool
    """Something happened in the chat since the given moment - refetch the thread."""
