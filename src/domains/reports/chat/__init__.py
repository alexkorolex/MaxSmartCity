"""Chat between a resident and the organizations working on their report."""

from src.domains.reports.chat.events import (
    MAX_WAIT_SECONDS,
    ChatEventBus,
    ChatSubscription,
    chat_events_lifespan,
    provide_chat_events,
)
from src.domains.reports.chat.notifier import UNREAD_NOTIFICATION_DELAY, notify_unread_chat_messages
from src.domains.reports.chat.participants import (
    ChatConflictError,
    ChatForbiddenError,
    ChatNotFoundError,
    report_organizations,
)
from src.domains.reports.chat.schemas import (
    ChatConversationSummary,
    ChatMessageView,
    ChatThread,
    ChatUpdates,
    SendChatMessageCommand,
)
from src.domains.reports.chat.service import MAX_MESSAGE_LENGTH, ReportChatService

__all__ = (
    "MAX_MESSAGE_LENGTH",
    "MAX_WAIT_SECONDS",
    "UNREAD_NOTIFICATION_DELAY",
    "ChatConflictError",
    "ChatConversationSummary",
    "ChatEventBus",
    "ChatForbiddenError",
    "ChatMessageView",
    "ChatNotFoundError",
    "ChatSubscription",
    "ChatThread",
    "ChatUpdates",
    "ReportChatService",
    "SendChatMessageCommand",
    "chat_events_lifespan",
    "notify_unread_chat_messages",
    "provide_chat_events",
    "report_organizations",
)
