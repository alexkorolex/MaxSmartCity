from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class TerritoryStats:
    houses: int = 0
    houses_without_manager: int = 0
    managing_organizations: int = 0
    residents: int = 0
    reports_total: int = 0
    reports_open: int = 0
    reports_last_30_days: int = 0
    incidents_open: int = 0
    incidents_critical_open: int = 0
    incidents_resolved: int = 0


@dataclass(slots=True)
class TerritoryRef:
    id: UUID
    name: str
    type: str


@dataclass(slots=True)
class TerritoryBreakdown:
    territory: TerritoryRef | None
    stats: TerritoryStats


@dataclass(slots=True)
class CategoryCount:
    name: str
    reports: int


@dataclass(slots=True)
class TerritorySummary:
    territory: TerritoryRef
    path: list[TerritoryRef]
    total: TerritoryStats
    children: list[TerritoryBreakdown]
    top_categories: list[CategoryCount]
