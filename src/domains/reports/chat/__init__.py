"""Chat between a resident and the organizations working on their report."""

from src.domains.reports.chat.events import MAX_WAIT_SECONDS, ChatSubscription, publish_chat_event
from src.domains.reports.chat.notifier import UNREAD_NOTIFICATION_DELAY, notify_unread_chat_messages
from src.domains.reports.chat.participants import ChatConflictError, ChatNotFoundError, report_organizations
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
    "ChatMessageView",
    "ChatNotFoundError",
    "ChatSubscription",
    "ChatThread",
    "ChatUpdates",
    "ReportChatService",
    "SendChatMessageCommand",
    "notify_unread_chat_messages",
    "publish_chat_event",
    "report_organizations",
)
