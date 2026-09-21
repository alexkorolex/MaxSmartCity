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


class AttachmentType(StrEnum):
    IMAGE = "IMAGE"
    FILE = "FILE"
