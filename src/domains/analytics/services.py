from collections.abc import Callable
from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Select, Subquery, and_, distinct, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.enums import Priority
from src.common.models import utc_now
from src.domains.analytics.schemas import (
    CategoryCount,
    TerritoryBreakdown,
    TerritoryRef,
    TerritoryStats,
    TerritorySummary,
)
from src.domains.geo.models import AdministrativeArea, House, HouseManagement
from src.domains.geo.services.territories import TerritoryService, subtree_ids
from src.domains.identity.models import Resident
from src.domains.incidents.enums import IncidentStatus
from src.domains.incidents.models import Incident, IncidentAffectedHouse
from src.domains.reports.enums import ReportStatus
from src.domains.reports.models import ProblemCategory, Report

OPEN_REPORT_STATUSES = (
    ReportStatus.RECEIVED,
    ReportStatus.PROCESSING,
    ReportStatus.READY_FOR_TRIAGE,
    ReportStatus.LINKED,
    ReportStatus.NEEDS_CLARIFICATION,
)
RESOLVED_INCIDENT_STATUSES = (IncidentStatus.RESOLVED, IncidentStatus.CLOSED)
INACTIVE_INCIDENT_STATUSES = (
    *RESOLVED_INCIDENT_STATUSES,
    IncidentStatus.REJECTED,
    IncidentStatus.CANCELLED,
    IncidentStatus.MERGED,
)
TOP_CATEGORIES = 5


def _house_buckets(territory_id: UUID) -> Subquery:
    buckets = (
        select(AdministrativeArea.id.label("area_id"), AdministrativeArea.id.label("bucket"))
        .where(AdministrativeArea.parent_id == territory_id)
        .cte(recursive=True)
    )
    buckets = buckets.union_all(
        select(AdministrativeArea.id, buckets.c.bucket).where(
            AdministrativeArea.parent_id == buckets.c.area_id
        )
    )
    areas = select(buckets.c.area_id, buckets.c.bucket).union_all(
        select(literal(territory_id).label("area_id"), literal(None).label("bucket"))
    )
    area_buckets = areas.subquery()
    return (
        select(House.id.label("house_id"), area_buckets.c.bucket)
        .join(area_buckets, area_buckets.c.area_id == House.administrative_area_id)
        .subquery()
    )


def _count_if(condition: ColumnElement[bool]) -> ColumnElement[int]:
    return func.count().filter(condition)


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def territory_summary(self, territory_id: UUID, *, visible_root: UUID | None) -> TerritorySummary:
        territories = TerritoryService(self.session)
        territory = await territories.get(territory_id)
        houses = _house_buckets(territory_id)
        per_bucket: dict[UUID | None, TerritoryStats] = {}
        total = TerritoryStats()

        def stats(bucket: UUID | None) -> TerritoryStats:
            return per_bucket.setdefault(bucket, TerritoryStats())

        await self._collect(self._house_counts(houses), stats, total)
        await self._collect(self._resident_counts(houses), stats, total)
        await self._collect(self._report_counts(houses), stats, total)
        await self._collect(self._incident_counts(houses, grouped=True), stats, None)
        await self._collect(self._incident_counts(houses, grouped=False), None, total)
        await self._collect(self._organization_counts(houses, grouped=True), stats, None)
        await self._collect(self._organization_counts(houses, grouped=False), None, total)

        children = (
            await self.session.scalars(
                select(AdministrativeArea)
                .where(AdministrativeArea.parent_id == territory_id)
                .order_by(AdministrativeArea.name)
            )
        ).all()
        breakdown = [
            TerritoryBreakdown(territory=_ref(child), stats=per_bucket.get(child.id, TerritoryStats()))
            for child in children
        ]
        if children and None in per_bucket:
            breakdown.append(TerritoryBreakdown(territory=None, stats=per_bucket[None]))
        return TerritorySummary(
            territory=_ref(territory),
            path=await self._path(territory, visible_root),
            total=total,
            children=breakdown,
            top_categories=await self._top_categories(territory_id),
        )

    async def _collect(
        self,
        statement: Select[Any],
        stats: Callable[[UUID | None], TerritoryStats] | None,
        total: TerritoryStats | None,
    ) -> None:
        for row in (await self.session.execute(statement)).mappings().all():
            values = {key: value for key, value in row.items() if key != "bucket"}
            targets = []
            if stats is not None:
                targets.append(stats(row.get("bucket")))
            if total is not None:
                targets.append(total)
            for target in targets:
                for key, value in values.items():
                    setattr(target, key, getattr(target, key) + (value or 0))

    @staticmethod
    def _house_counts(houses: Subquery) -> Select[Any]:
        managed = select(HouseManagement.house_id).where(HouseManagement.is_active.is_(True))
        return select(
            houses.c.bucket,
            func.count().label("houses"),
            _count_if(houses.c.house_id.not_in(managed)).label("houses_without_manager"),
        ).group_by(houses.c.bucket)

    @staticmethod
    def _resident_counts(houses: Subquery) -> Select[Any]:
        return (
            select(houses.c.bucket, func.count(Resident.id).label("residents"))
            .join(Resident, Resident.house_id == houses.c.house_id)
            .group_by(houses.c.bucket)
        )

    @staticmethod
    def _report_counts(houses: Subquery) -> Select[Any]:
        recent = utc_now() - timedelta(days=30)
        return (
            select(
                houses.c.bucket,
                func.count(Report.id).label("reports_total"),
                _count_if(Report.status.in_(OPEN_REPORT_STATUSES)).label("reports_open"),
                _count_if(Report.created_at >= recent).label("reports_last_30_days"),
            )
            .join(Report, Report.house_id == houses.c.house_id)
            .group_by(houses.c.bucket)
        )

    @staticmethod
    def _incident_counts(houses: Subquery, *, grouped: bool) -> Select[Any]:
        is_open = Incident.status.not_in(INACTIVE_INCIDENT_STATUSES)
        columns = [
            func.count(distinct(Incident.id)).filter(is_open).label("incidents_open"),
            func.count(distinct(Incident.id))
            .filter(and_(is_open, Incident.priority == Priority.CRITICAL))
            .label("incidents_critical_open"),
            func.count(distinct(Incident.id))
            .filter(Incident.status.in_(RESOLVED_INCIDENT_STATUSES))
            .label("incidents_resolved"),
        ]
        statement = (
            select(*([houses.c.bucket] if grouped else []), *columns)
            .select_from(houses)
            .join(IncidentAffectedHouse, IncidentAffectedHouse.house_id == houses.c.house_id)
            .join(Incident, Incident.id == IncidentAffectedHouse.incident_id)
        )
        return statement.group_by(houses.c.bucket) if grouped else statement

    @staticmethod
    def _organization_counts(houses: Subquery, *, grouped: bool) -> Select[Any]:
        statement = (
            select(
                *([houses.c.bucket] if grouped else []),
                func.count(distinct(HouseManagement.organization_id)).label("managing_organizations"),
            )
            .select_from(houses)
            .join(
                HouseManagement,
                and_(HouseManagement.house_id == houses.c.house_id, HouseManagement.is_active.is_(True)),
            )
        )
        return statement.group_by(houses.c.bucket) if grouped else statement

    async def _top_categories(self, territory_id: UUID) -> list[CategoryCount]:
        in_territory = select(House.id).where(House.administrative_area_id.in_(subtree_ids(territory_id)))
        rows = (
            await self.session.execute(
                select(ProblemCategory.name, func.count(Report.id).label("reports"))
                .join(Report, Report.category_id == ProblemCategory.id)
                .where(Report.house_id.in_(in_territory))
                .group_by(ProblemCategory.name)
                .order_by(func.count(Report.id).desc(), ProblemCategory.name)
                .limit(TOP_CATEGORIES)
            )
        ).all()
        return [CategoryCount(name=row.name, reports=row.reports) for row in rows]

    async def _path(self, territory: AdministrativeArea, visible_root: UUID | None) -> list[TerritoryRef]:
        path = [_ref(territory)]
        current = territory
        while current.parent_id is not None and current.id != visible_root:
            parent = await self.session.get(AdministrativeArea, current.parent_id)
            if parent is None:
                break
            path.insert(0, _ref(parent))
            current = parent
        return path


def _ref(territory: AdministrativeArea) -> TerritoryRef:
    return TerritoryRef(id=territory.id, name=territory.name, type=territory.type.value)
