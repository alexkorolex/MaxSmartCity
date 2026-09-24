"""What an organization works on - the single source of truth for every admin-panel
listing a ``district_admin``/``housing_worker`` is confined to.

A УК/ТСЖ works through its houses: every incident affecting a house it actively manages,
every resident report about such a house, and every resident living in one. On top of
that it sees incidents it was explicitly assigned to (``collaboration.Assignment``, e.g.
a water utility sent to a house it doesn't manage) together with their reports and
reporters. Each function returns a subquery of ids for ``column.in_(...)`` filters.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import Select, select, union

from src.domains.collaboration.models import Assignment
from src.domains.geo.models import HouseManagement
from src.domains.identity.models import Resident
from src.domains.incidents.models import IncidentAffectedHouse, IncidentReportLink
from src.domains.reports.models import Report


def managed_house_ids(organization_id: UUID) -> Select[Any]:
    return select(HouseManagement.house_id).where(
        HouseManagement.organization_id == organization_id,
        HouseManagement.is_active.is_(True),
    )


def organization_incident_ids(organization_id: UUID) -> Select[Any]:
    return select(
        union(
            select(Assignment.incident_id).where(Assignment.organization_id == organization_id),
            select(IncidentAffectedHouse.incident_id).where(
                IncidentAffectedHouse.house_id.in_(managed_house_ids(organization_id))
            ),
        ).subquery()
    )


def organization_report_ids(organization_id: UUID) -> Select[Any]:
    return select(
        union(
            select(Report.id).where(Report.house_id.in_(managed_house_ids(organization_id))),
            select(IncidentReportLink.report_id).where(
                IncidentReportLink.is_active.is_(True),
                IncidentReportLink.incident_id.in_(organization_incident_ids(organization_id)),
            ),
        ).subquery()
    )


def organization_resident_ids(organization_id: UUID) -> Select[Any]:
    return select(
        union(
            select(Resident.id).where(Resident.house_id.in_(managed_house_ids(organization_id))),
            select(Report.resident_id).where(
                Report.resident_id.is_not(None),
                Report.id.in_(organization_report_ids(organization_id)),
            ),
        ).subquery()
    )
