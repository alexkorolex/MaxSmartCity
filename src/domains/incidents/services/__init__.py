"""Incident application services - see ``core.IncidentCoreService``."""

from src.domains.incidents.services.base import (
    ACTIVE_INCIDENT_STATUSES,
    AWAITING_RESIDENT_STATUSES,
    DISPUTE_ESCALATION_THRESHOLD,
    DISPUTE_ESCALATION_WINDOW,
    FINAL_REPORT_STATUSES,
    OPEN_ASSIGNMENT_STATUSES,
    RESOLUTION_CONFIRMATION_WINDOW,
    STAFF_COMPLETABLE_STATUSES,
    IncidentCoreConflictError,
    IncidentCoreError,
    IncidentCoreNotFoundError,
)
from src.domains.incidents.services.core import IncidentCoreService, IncidentService, ResolutionDisputeService

__all__ = (
    "ACTIVE_INCIDENT_STATUSES",
    "AWAITING_RESIDENT_STATUSES",
    "DISPUTE_ESCALATION_THRESHOLD",
    "DISPUTE_ESCALATION_WINDOW",
    "FINAL_REPORT_STATUSES",
    "OPEN_ASSIGNMENT_STATUSES",
    "RESOLUTION_CONFIRMATION_WINDOW",
    "STAFF_COMPLETABLE_STATUSES",
    "IncidentCoreConflictError",
    "IncidentCoreError",
    "IncidentCoreNotFoundError",
    "IncidentCoreService",
    "IncidentService",
    "ResolutionDisputeService",
)
