"""Vocabulary owned by the reports domain."""

from enum import StrEnum


class ReportSourceType(StrEnum):
    MAX = "MAX"
    INGESTION = "INGESTION"
    OPERATOR = "OPERATOR"
    SYSTEM = "SYSTEM"


class ReportStatus(StrEnum):
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    READY_FOR_TRIAGE = "READY_FOR_TRIAGE"
    LINKED = "LINKED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    CLOSED = "CLOSED"
    """The linked incident was closed - the resident confirmed the fix, or didn't answer
    within the confirmation window. Returns to ``LINKED`` if the incident is reopened."""


class AttachmentType(StrEnum):
    IMAGE = "IMAGE"
    FILE = "FILE"
