"""Vocabulary owned by the incidents domain."""

from enum import StrEnum


class IncidentStatus(StrEnum):
    NEW = "NEW"
    TRIAGE = "TRIAGE"
    CONFIRMED = "CONFIRMED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    MERGED = "MERGED"
    RESOLUTION_DISPUTED = "RESOLUTION_DISPUTED"
    REOPENED = "REOPENED"


class LinkSource(StrEnum):
    MANUAL = "MANUAL"
    ML = "ML"
    RULE = "RULE"
    INGESTION = "INGESTION"


class AffectedHouseSource(StrEnum):
    MANUAL = "MANUAL"
    REPORT = "REPORT"
    INGESTION = "INGESTION"
    GEO = "GEO"


class IncidentRelationType(StrEnum):
    MERGED_INTO = "MERGED_INTO"
    SPLIT_FROM = "SPLIT_FROM"


class ResolutionDisputeStatus(StrEnum):
    OPEN = "OPEN"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    RESOLVED = "RESOLVED"
