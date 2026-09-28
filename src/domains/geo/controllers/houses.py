"""Поиск домов, карточка дома и данные для городской карты."""

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
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
    GeoJSONPoint,
    HouseInfo,
    HouseManagementSummary,
    HouseMapFeature,
    HouseMapFeatureCollection,
    HouseMapMetadata,
    HouseMapProperties,
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
from src.domains.incidents.enums import IncidentStatus
from src.domains.incidents.models import Incident, IncidentAffectedHouse
from src.domains.reports.enums import ReportStatus
from src.domains.reports.models import Report

_INACTIVE_REPORT_STATUSES = (
    ReportStatus.REJECTED,
    ReportStatus.WITHDRAWN,
    ReportStatus.CLOSED,
)
_INACTIVE_INCIDENT_STATUSES = (
    IncidentStatus.CLOSED,
    IncidentStatus.REJECTED,
    IncidentStatus.CANCELLED,
    IncidentStatus.MERGED,
)


@dataclass(frozen=True, slots=True)
class _HouseMapRowData:
    id: UUID
    city: str | None
    street: str | None
    house_number: str | None
    formatted: str
    point_geojson: str | None
    active_reports: int
    active_incidents: int


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


def _house_map_statement() -> Select[Any]:
    report_counts = (
        select(Report.house_id.label("house_id"), func.count(Report.id).label("active_reports"))
        .where(Report.house_id.is_not(None), Report.status.not_in(_INACTIVE_REPORT_STATUSES))
        .group_by(Report.house_id)
        .subquery()
    )
    incident_counts = (
        select(
            IncidentAffectedHouse.house_id.label("house_id"),
            func.count(IncidentAffectedHouse.incident_id).label("active_incidents"),
        )
        .join(Incident, Incident.id == IncidentAffectedHouse.incident_id)
        .where(Incident.status.not_in(_INACTIVE_INCIDENT_STATUSES))
        .group_by(IncidentAffectedHouse.house_id)
        .subquery()
    )
    point = func.coalesce(House.point, Address.point)
    return (
        select(
            House.id,
            Address.city,
            Address.street,
            Address.house_number,
            Address.formatted,
            func.ST_AsGeoJSON(point).label("point_geojson"),
            func.coalesce(report_counts.c.active_reports, 0).label("active_reports"),
            func.coalesce(incident_counts.c.active_incidents, 0).label("active_incidents"),
        )
        .join(Address, Address.id == House.address_id)
        .outerjoin(report_counts, report_counts.c.house_id == House.id)
        .outerjoin(incident_counts, incident_counts.c.house_id == House.id)
    )


def _house_map_row_data(row: Row[Any]) -> _HouseMapRowData:
    return _HouseMapRowData(
        id=row.id,
        city=row.city,
        street=row.street,
        house_number=row.house_number,
        formatted=row.formatted,
        point_geojson=row.point_geojson,
        active_reports=row.active_reports,
        active_incidents=row.active_incidents,
    )


def _to_house_map_feature(row: _HouseMapRowData) -> HouseMapFeature:
    point = None
    if row.point_geojson is not None:
        geometry = json.loads(row.point_geojson)
        coordinates = geometry.get("coordinates")
        if geometry.get("type") != "Point" or not isinstance(coordinates, list) or len(coordinates) != 2:
            raise ValueError("House coordinate is not a GeoJSON Point")
        point = GeoJSONPoint(coordinates=(float(coordinates[0]), float(coordinates[1])))
    return HouseMapFeature(
        id=str(row.id),
        geometry=point,
        properties=HouseMapProperties(
            house_id=row.id,
            formatted=row.formatted,
            city=row.city,
            street=row.street,
            house_number=row.house_number,
            active_reports=int(row.active_reports),
            active_incidents=int(row.active_incidents),
        ),
    )


class HouseController(Controller):
    """Read-only: what a resident (or the "Сообщить о проблеме" flow) picks a home from.
    Houses are seeded by the ingestion pipeline, not created through this API."""

    path = "/geo/houses"
    tags = ("geo",)
    return_dto = None

    @get("/geojson", name="geo:House:geojson")
    async def geojson(
        self,
        db_session: NamedDependency[AsyncSession],
        city: Annotated[str, Parameter(min_length=1, max_length=255)],
        limit: Annotated[int, Parameter(ge=1, le=5000)] = 1000,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> HouseMapFeatureCollection:
        """Точки домов и текущая нагрузка для слоёв карты на фронтенде."""
        with database_action("list", "geo.HouseMap"):
            rows = (
                await db_session.execute(
                    _house_map_statement()
                    .where(Address.city == city)
                    .order_by(House.id)
                    .limit(limit + 1)
                    .offset(offset)
                )
            ).all()
            has_more = len(rows) > limit
            features = [_to_house_map_feature(_house_map_row_data(row)) for row in rows[:limit]]
            located = sum(feature.geometry is not None for feature in features)
            return HouseMapFeatureCollection(
                features=features,
                metadata=HouseMapMetadata(
                    city=city,
                    returned=len(features),
                    limit=limit,
                    offset=offset,
                    has_more=has_more,
                    located=located,
                    unlocated=len(features) - located,
                ),
            )

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
