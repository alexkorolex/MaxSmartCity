"""Vocabulary owned by the notifications domain."""

from enum import StrEnum


class NotificationType(StrEnum):
    REPORT_STATUS_CHANGED = "REPORT_STATUS_CHANGED"
    INCIDENT_STATUS_CHANGED = "INCIDENT_STATUS_CHANGED"
    RESOLUTION_REQUESTED = "RESOLUTION_REQUESTED"
    NEWS = "NEWS"
    CHAT_MESSAGE = "CHAT_MESSAGE"
    GENERIC = "GENERIC"


class OrganizationChannelType(StrEnum):
    """How an organization (УК/ТСЖ) wants to hear about residents' requests - each value
    maps to one delivery strategy in ``src.domains.notifications.channels``."""

    MAX_MEMBERS = "MAX_MEMBERS"
    """Personal MAX message to every active member who linked a MAX account
    (``POST /auth/staff/max-id``); ``target`` is unused."""
    MAX_CHAT = "MAX_CHAT"
    """One message to a MAX group chat; ``target`` is the numeric ``chat_id``."""
    EMAIL = "EMAIL"
    """``target`` is the dispatcher's mailbox address."""
    WEBHOOK = "WEBHOOK"
    """JSON POST to the organization's own system (e.g. its dispatch/CRM); ``target`` is
    an ``https://`` URL, ``secret`` (optional) signs the body with HMAC-SHA256."""
