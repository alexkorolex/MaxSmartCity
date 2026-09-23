"""Vocabulary owned by the notifications domain."""

from enum import StrEnum


class NotificationType(StrEnum):
    REPORT_STATUS_CHANGED = "REPORT_STATUS_CHANGED"
    INCIDENT_STATUS_CHANGED = "INCIDENT_STATUS_CHANGED"
    RESOLUTION_REQUESTED = "RESOLUTION_REQUESTED"
    NEWS = "NEWS"
    GENERIC = "GENERIC"
