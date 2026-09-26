"""Who a news post is for. The platform admin's posts (``organization_id is None``) reach
every resident; an УК/ТСЖ's reach the residents of the houses it manages right now; the
district administration's (Управа) - which manages no houses - the residents of its city."""

from uuid import UUID

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute

from src.domains.geo.models import Address, House, HouseManagement
from src.domains.identity.enums import OrganizationType
from src.domains.identity.models import Organization, Resident
from src.domains.news.models import NewsPost


def _normalized(column: InstrumentedAttribute[str | None]) -> ColumnElement[str | None]:
    return func.lower(func.trim(column))


def resident_audience(resident_id: UUID) -> ColumnElement[bool]:
    """The posts meant for this resident, by the house they live in. A resident who hasn't
    picked their house yet gets only the platform-wide posts."""
    house_managers = (
        select(HouseManagement.organization_id)
        .join(Resident, Resident.house_id == HouseManagement.house_id)
        .where(Resident.id == resident_id, HouseManagement.is_active.is_(True))
    )
    resident_city = (
        select(_normalized(Address.city))
        .join(House, House.address_id == Address.id)
        .join(Resident, Resident.house_id == House.id)
        .where(Resident.id == resident_id)
        .scalar_subquery()
    )
    city_administrations = select(Organization.id).where(
        Organization.type == OrganizationType.ADMINISTRATION,
        _normalized(Organization.city) == resident_city,
    )
    return or_(
        NewsPost.organization_id.is_(None),
        NewsPost.organization_id.in_(house_managers),
        NewsPost.organization_id.in_(city_administrations),
    )


def staff_audience(organization_id: UUID | None) -> ColumnElement[bool]:
    """A staff member sees the platform-wide posts and their own organization's - not what
    other organizations tell their residents."""
    if organization_id is None:
        return NewsPost.organization_id.is_(None)
    return or_(NewsPost.organization_id.is_(None), NewsPost.organization_id == organization_id)
