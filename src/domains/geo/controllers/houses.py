"""Houses: the address search residents and staff pick a house from, and a house's reference card."""

import re
from collections.abc import Sequence
from typing import Annotated, Any
from uuid import UUID

from litestar import Controller, get
from litestar.di import NamedDependency
from litestar.exceptions import NotFoundException
from litestar.params import FromPath, Parameter
from sqlalchemy import Row, Select, case, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.geo.models import Address, House, HouseManagement
from src.domains.geo.schemas import (
    HouseInfo,
    HouseManagementSummary,
    HouseSummary,
)
from src.domains.geo.services import (
    house_management_summary_statement,
    load_house_reference,
    load_managing_organizations,
    load_platform_manager,
    to_house_management_summary,
)
from src.domains.identity.models import Organization


def _search_words(q: str | None) -> list[str]:
    """Up to 6 words of an address query, LIKE-escaped."""
    words = re.findall(r"[\w-]+", q or "")[:6]
    return [word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") for word in words]


def _house_summary_statement() -> Select[Any]:
    """A house with its address and current manager (if any) flattened in."""
    return (
        select(
            House.id,
            Address.city,
            Address.street,
            Address.house_number,
            Address.formatted,
            HouseManagement.organization_id,
            Organization.name.label("organization_name"),
        )
        .join(Address, Address.id == House.address_id)
        .outerjoin(
            HouseManagement,
            (HouseManagement.house_id == House.id) & HouseManagement.is_active.is_(True),
        )
        .outerjoin(Organization, Organization.id == HouseManagement.organization_id)
    )


def _to_house_summary(row: Row[Any]) -> HouseSummary:
    return HouseSummary(
        house_id=row.id,
        city=row.city,
        street=row.street,
        house_number=row.house_number,
        formatted=row.formatted,
        managed_by_organization_id=row.organization_id,
        managed_by_organization_name=row.organization_name,
    )


class HouseController(Controller):
    """Read-only: what a resident (or the "Сообщить о проблеме" flow) picks a home from.
    Houses are seeded by the ingestion pipeline, not created through this API."""

    path = "/geo/houses"
    tags = ("geo",)
    return_dto = None

    @get("/", name="geo:House:list")
    async def list_items(
        self,
        db_session: NamedDependency[AsyncSession],
        city: Annotated[str | None, Parameter()] = None,
        q: Annotated[str | None, Parameter(max_length=200)] = None,
        limit: Annotated[int, Parameter(ge=1, le=200)] = 200,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[HouseSummary]:
        """``q`` searches word by word, case-insensitively: every word must occur in the
        formatted address, except numbers, which must start the house number - so
        "Мира 9" finds "ул. Мира, д. 9" and "9А", but not a house whose postcode has a 9."""
        with database_action("list", "geo.House"):
            words = _search_words(q)
            numbers = [word.lower() for word in words if word[0].isdigit()]
            # A typed house number first ("Мира 10" -> дом 10, then 10А, 10 корп. 1, ...).
            exact_number_first = (
                case((func.lower(Address.house_number).in_(numbers), 0), else_=1) if numbers else literal(1)
            )
            statement = (
                _house_summary_statement()
                .order_by(exact_number_first, Address.city, Address.street, Address.house_number)
                .limit(limit)
                .offset(offset)
            )
            if city:
                statement = statement.where(Address.city == city)
            for word in words:
                if word[0].isdigit():
                    # Numbers match the house number itself - never a postcode ("241028" holds "10").
                    statement = statement.where(Address.house_number.ilike(f"{word}%"))
                else:
                    statement = statement.where(Address.formatted.ilike(f"%{word}%"))
            rows = (await db_session.execute(statement)).all()
            return [_to_house_summary(row) for row in rows]

    @get("/{item_id:uuid}", name="geo:House:get")
    async def get_item(
        self, item_id: FromPath[UUID], db_session: NamedDependency[AsyncSession]
    ) -> HouseSummary:
        with database_action("get", "geo.House"):
            row = (await db_session.execute(_house_summary_statement().where(House.id == item_id))).first()
            if row is None:
                raise NotFoundException(f"House {item_id} was not found")
            return _to_house_summary(row)

    @get("/{item_id:uuid}/info", name="geo:House:info")
    async def get_info(self, item_id: FromPath[UUID], db_session: NamedDependency[AsyncSession]) -> HouseInfo:
        """Everything a resident wants to know about the house they picked: who manages
        it and how to reach them - from open sources (with provenance) and, when the
        УК/ТСЖ is connected to Smart City, that it receives requests directly."""
        with database_action("get", "geo.House"):
            row = (await db_session.execute(_house_summary_statement().where(House.id == item_id))).first()
            if row is None:
                raise NotFoundException(f"House {item_id} was not found")
            platform_manager = await load_platform_manager(db_session, item_id)
            management_method, official_status = await load_house_reference(db_session, item_id)
            managing_organizations = await load_managing_organizations(
                db_session,
                item_id,
                platform_inn=platform_manager.inn if platform_manager else None,
                platform_ogrn=platform_manager.ogrn if platform_manager else None,
            )
            return HouseInfo(
                house=_to_house_summary(row),
                management_method=management_method,
                official_status=official_status,
                platform_manager=platform_manager,
                managing_organizations=managing_organizations,
            )

    @get("/{item_id:uuid}/management", name="geo:House:management")
    async def get_management(
        self, item_id: FromPath[UUID], db_session: NamedDependency[AsyncSession]
    ) -> HouseManagementSummary:
        """Who currently manages the house (УК/ТСЖ) - lets a resident see where their
        requests go."""
        with database_action("get", "geo.HouseManagement"):
            row = (
                await db_session.execute(
                    house_management_summary_statement().where(
                        HouseManagement.house_id == item_id, HouseManagement.is_active.is_(True)
                    )
                )
            ).first()
            if row is None:
                raise NotFoundException(f"House {item_id} has no active manager")
            return to_house_management_summary(row)
