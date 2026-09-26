from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class StartConversationCommand:
    subject: str
    text: str
    organization_id: UUID | None = None


@dataclass
class SendMessageCommand:
    text: str


@dataclass(slots=True)
class CorrespondenceContact:
    organization_id: UUID | None
    name: str
    kind: str


@dataclass(slots=True)
class ConversationSummary:
    id: UUID
    subject: str
    counterpart_name: str
    last_message_text: str | None
    last_message_at: datetime
    unread_count: int


@dataclass(slots=True)
class ConversationMessageView:
    id: UUID
    text: str
    created_at: datetime
    author_name: str
    organization_name: str
    is_mine: bool


@dataclass(slots=True)
class ConversationThread:
    id: UUID
    subject: str
    counterpart_name: str
    counterpart_read_at: datetime | None
    messages: list[ConversationMessageView]


@dataclass(slots=True)
class ConversationUpdates:
    changed: bool
