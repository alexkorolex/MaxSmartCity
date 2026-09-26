from uuid import UUID

from sqlalchemy import ColumnElement, or_, select

from src.domains.geo.models import House, HouseManagement
from src.domains.geo.services.territories import ancestor_ids
from src.domains.identity.models import Organization, Resident
from src.domains.news.models import NewsPost


def resident_audience(resident_id: UUID) -> ColumnElement[bool]:
    house_managers = (
        select(HouseManagement.organization_id)
        .join(Resident, Resident.house_id == HouseManagement.house_id)
        .where(Resident.id == resident_id, HouseManagement.is_active.is_(True))
    )
    resident_territory = (
        select(House.administrative_area_id)
        .join(Resident, Resident.house_id == House.id)
        .where(Resident.id == resident_id)
        .scalar_subquery()
    )
    territory_authorities = select(Organization.id).where(
        Organization.territory_id.in_(ancestor_ids(resident_territory))
    )
    return or_(
        NewsPost.organization_id.is_(None),
        NewsPost.organization_id.in_(house_managers),
        NewsPost.organization_id.in_(territory_authorities),
    )


def staff_audience(organization_id: UUID | None) -> ColumnElement[bool]:
    if organization_id is None:
        return NewsPost.organization_id.is_(None)
    return or_(NewsPost.organization_id.is_(None), NewsPost.organization_id == organization_id)
