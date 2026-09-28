import json
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.incidents.enums import IncidentStatus
from src.domains.reports.enums import ReportStatus
from src.map.schemas import MapCity, MapScope

TILE_EXTENT = 4096
TILE_BUFFER = 64
MAX_ZOOM = 22
HOUSES_MIN_ZOOM = 12
HOUSE_FOOTPRINTS_MIN_ZOOM = 15
BUILDINGS_MIN_ZOOM = 14
STATEMENT_TIMEOUT = "8s"
DISTRICT_SIMPLIFY_TOLERANCE = 0.00005
SCOPE_MARGIN_DEGREES = 0.002

INACTIVE_REPORT_STATUSES = [
    status.value for status in (ReportStatus.REJECTED, ReportStatus.WITHDRAWN, ReportStatus.CLOSED)
]
INACTIVE_INCIDENT_STATUSES = [
    status.value
    for status in (
        IncidentStatus.CLOSED,
        IncidentStatus.REJECTED,
        IncidentStatus.CANCELLED,
        IncidentStatus.MERGED,
    )
]

_SCOPE_AREAS = """
scope_areas AS (
    SELECT id FROM geo.administrative_area WHERE id = CAST(:scope_root AS uuid)
    UNION ALL
    SELECT a.id FROM geo.administrative_area a JOIN scope_areas s ON a.parent_id = s.id
)"""

_IN_SCOPE = "(CAST(:scope_root AS uuid) IS NULL OR h.administrative_area_id IN (SELECT id FROM scope_areas))"

_SCOPE_GEOMETRY = f"""
scope_geometry AS (
    SELECT COALESCE(
        (SELECT geometry FROM geo.administrative_area WHERE id = CAST(:scope_root AS uuid)),
        (SELECT ST_Expand(ST_Extent(h.point::geometry)::geometry, {SCOPE_MARGIN_DEGREES})
         FROM geo.house h
         WHERE h.point IS NOT NULL AND h.administrative_area_id IN (SELECT id FROM scope_areas))
    ) AS g
)"""

_BOUNDS = """
bounds AS (
    SELECT ST_TileEnvelope(:z, :x, :y) AS env, ST_Transform(ST_TileEnvelope(:z, :x, :y), 4326) AS env4326
)"""

_HOUSES_TILE = text(
    f"""
WITH RECURSIVE {_SCOPE_AREAS}, {_BOUNDS},
houses AS (
    SELECT h.id, a.formatted, h.footprint, h.point
    FROM geo.house h JOIN geo.address a ON a.id = h.address_id, bounds b
    WHERE (h.footprint && b.env4326 OR h.point && b.env4326::geography) AND {_IN_SCOPE}
),
report_counts AS (
    SELECT r.house_id, count(*) AS active_reports
    FROM reports.report r JOIN houses hs ON hs.id = r.house_id
    WHERE r.status NOT IN :inactive_reports
    GROUP BY r.house_id
),
incident_counts AS (
    SELECT iah.house_id, count(*) AS active_incidents
    FROM incidents.incident_affected_house iah
    JOIN houses hs ON hs.id = iah.house_id
    JOIN incidents.incident i ON i.id = iah.incident_id
    WHERE i.status NOT IN :inactive_incidents
    GROUP BY iah.house_id
),
tile AS (
    SELECT ST_AsMVTGeom(
            ST_Transform(
                CASE WHEN :z >= :footprint_zoom AND hs.footprint IS NOT NULL
                    THEN hs.footprint ELSE hs.point::geometry END,
                3857
            ),
            b.env, :extent, :buffer, true
        ) AS geom,
        hs.id::text AS house_id,
        CASE WHEN :z >= :footprint_zoom THEN hs.formatted END AS address,
        hs.footprint IS NOT NULL AS has_footprint,
        COALESCE(rc.active_reports, 0)::int AS active_reports,
        COALESCE(ic.active_incidents, 0)::int AS active_incidents
    FROM houses hs CROSS JOIN bounds b
    LEFT JOIN report_counts rc ON rc.house_id = hs.id
    LEFT JOIN incident_counts ic ON ic.house_id = hs.id
)
SELECT ST_AsMVT(tile.*, 'houses', :extent, 'geom') FROM tile WHERE geom IS NOT NULL
"""
).bindparams(
    bindparam("inactive_reports", expanding=True),
    bindparam("inactive_incidents", expanding=True),
)

_BUILDINGS_TILE = text(
    f"""
WITH RECURSIVE {_SCOPE_AREAS}, {_SCOPE_GEOMETRY}, {_BOUNDS},
tile AS (
    SELECT ST_AsMVTGeom(ST_Transform(bf.geometry, 3857), b.env, :extent, :buffer, true) AS geom
    FROM geo.building_footprint bf, bounds b
    WHERE bf.geometry && b.env4326
        AND (CAST(:scope_root AS uuid) IS NULL OR ST_Intersects(bf.geometry, (SELECT g FROM scope_geometry)))
)
SELECT ST_AsMVT(tile.*, 'buildings', :extent, 'geom') FROM tile WHERE geom IS NOT NULL
"""
)

_AREAS = text(
    f"""
WITH RECURSIVE {_SCOPE_AREAS},
areas AS (
    SELECT d.id, d.name, d.type, d.geometry
    FROM geo.administrative_area d
    WHERE d.geometry IS NOT NULL
        AND (CAST(:scope_root AS uuid) IS NULL OR d.id IN (SELECT id FROM scope_areas))
),
area_nodes AS (
    SELECT a.id AS area_id, a.id AS node_id FROM areas a
    UNION ALL
    SELECT n.area_id, c.id FROM geo.administrative_area c JOIN area_nodes n ON c.parent_id = n.node_id
),
area_houses AS (
    SELECT n.area_id, h.id AS house_id
    FROM area_nodes n JOIN geo.house h ON h.administrative_area_id = n.node_id
),
lineage AS (
    SELECT a.id AS area_id, p.id AS node_id, p.parent_id, p.name
    FROM areas a JOIN geo.administrative_area p ON p.id = a.id
    UNION ALL
    SELECT l.area_id, p.id, p.parent_id, p.name
    FROM lineage l JOIN geo.administrative_area p ON p.id = l.parent_id
)
SELECT a.id, a.name, a.type,
    (SELECT l.name FROM lineage l WHERE l.area_id = a.id AND l.parent_id IS NULL) AS city,
    ST_AsGeoJSON(ST_SimplifyPreserveTopology(a.geometry, :tolerance), 6) AS geometry,
    (SELECT count(*) FROM area_houses ah WHERE ah.area_id = a.id) AS house_count,
    (SELECT count(*) FROM area_houses ah JOIN reports.report r ON r.house_id = ah.house_id
     WHERE ah.area_id = a.id AND r.status NOT IN :inactive_reports) AS active_reports,
    (SELECT count(DISTINCT iah.incident_id) FROM area_houses ah
     JOIN incidents.incident_affected_house iah ON iah.house_id = ah.house_id
     JOIN incidents.incident i ON i.id = iah.incident_id
     WHERE ah.area_id = a.id AND i.status NOT IN :inactive_incidents) AS active_incidents
FROM areas a
ORDER BY city, a.type = 'CITY' DESC, a.name
"""
).bindparams(
    bindparam("inactive_reports", expanding=True),
    bindparam("inactive_incidents", expanding=True),
)

_CITIES_SUMMARY = text(
    f"""
WITH RECURSIVE {_SCOPE_AREAS}, {_SCOPE_GEOMETRY},
scoped AS (
    SELECT a.city, h.point, h.footprint
    FROM geo.house h JOIN geo.address a ON a.id = h.address_id
    WHERE a.city IS NOT NULL AND {_IN_SCOPE}
)
SELECT s.city,
    count(*) AS houses,
    count(s.point) AS located,
    count(s.footprint) AS with_footprint,
    ST_XMin(ST_Extent(s.point::geometry)) AS min_lon, ST_YMin(ST_Extent(s.point::geometry)) AS min_lat,
    ST_XMax(ST_Extent(s.point::geometry)) AS max_lon, ST_YMax(ST_Extent(s.point::geometry)) AS max_lat,
    CASE WHEN CAST(:scope_root AS uuid) IS NULL
        THEN (SELECT count(*) FROM geo.building_footprint bf WHERE bf.city = s.city)
        ELSE (SELECT count(*) FROM geo.building_footprint bf
              WHERE bf.city = s.city AND ST_Intersects(bf.geometry, (SELECT g FROM scope_geometry)))
    END AS buildings
FROM scoped s
GROUP BY s.city
ORDER BY s.city
"""
)

_SCOPE_TERRITORY = text("SELECT id, name, type FROM geo.administrative_area WHERE id = :scope_root")

_INCIDENT_HOUSES = text(
    f"""
WITH RECURSIVE {_SCOPE_AREAS},
incident_houses AS (
    SELECT h.id AS house_id, a.formatted AS address,
        COALESCE(h.point::geometry, a.point::geometry) AS point,
        i.id AS incident_id, i.title, i.status, i.priority, pc.name AS category,
        i.first_report_at, i.last_report_at
    FROM incidents.incident i
    JOIN incidents.incident_affected_house iah ON iah.incident_id = i.id
    JOIN geo.house h ON h.id = iah.house_id
    JOIN geo.address a ON a.id = h.address_id
    JOIN reports.problem_category pc ON pc.id = i.category_id
    WHERE (:include_closed OR i.status NOT IN :inactive_incidents) AND {_IN_SCOPE}
)
SELECT house_id, address, ST_AsGeoJSON(point, 6) AS point,
    json_agg(json_build_object(
        'incident_id', incident_id, 'title', title, 'status', status, 'priority', priority,
        'category', category, 'first_report_at', first_report_at, 'last_report_at', last_report_at
    ) ORDER BY last_report_at DESC NULLS LAST) AS incidents
FROM incident_houses
WHERE point IS NOT NULL AND (:no_bbox OR point && ST_MakeEnvelope(:west, :south, :east, :north, 4326))
GROUP BY house_id, address, point
"""
).bindparams(bindparam("inactive_incidents", expanding=True))

_INCIDENT_HOUSES_UNLOCATED = text(
    f"""
WITH RECURSIVE {_SCOPE_AREAS}
SELECT count(DISTINCT h.id)
FROM incidents.incident i
JOIN incidents.incident_affected_house iah ON iah.incident_id = i.id
JOIN geo.house h ON h.id = iah.house_id
JOIN geo.address a ON a.id = h.address_id
WHERE (:include_closed OR i.status NOT IN :inactive_incidents)
    AND h.point IS NULL AND a.point IS NULL AND {_IN_SCOPE}
"""
).bindparams(bindparam("inactive_incidents", expanding=True))


class InvalidTileError(ValueError):
    pass


class InvalidBboxError(ValueError):
    pass


def parse_bbox(value: str | None) -> tuple[float, float, float, float] | None:
    if not value:
        return None
    try:
        west, south, east, north = (float(part) for part in value.split(","))
    except ValueError as exc:
        raise InvalidBboxError("bbox must be west,south,east,north") from exc
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise InvalidBboxError("bbox is outside WGS84 bounds or inverted")
    return west, south, east, north


def validate_tile(z: int, x: int, y: int) -> None:
    if not 0 <= z <= MAX_ZOOM:
        raise InvalidTileError(f"z must be between 0 and {MAX_ZOOM}")
    size = 1 << z
    if not (0 <= x < size and 0 <= y < size):
        raise InvalidTileError("x and y are outside the zoom level")


async def _limit_statement_time(session: AsyncSession) -> None:
    await session.execute(text(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT}'"))


async def houses_tile(session: AsyncSession, z: int, x: int, y: int, *, scope_root: UUID | None) -> bytes:
    validate_tile(z, x, y)
    if z < HOUSES_MIN_ZOOM:
        return b""
    await _limit_statement_time(session)
    tile = await session.scalar(
        _HOUSES_TILE,
        {
            "z": z,
            "x": x,
            "y": y,
            "extent": TILE_EXTENT,
            "buffer": TILE_BUFFER,
            "footprint_zoom": HOUSE_FOOTPRINTS_MIN_ZOOM,
            "inactive_reports": INACTIVE_REPORT_STATUSES,
            "inactive_incidents": INACTIVE_INCIDENT_STATUSES,
            "scope_root": scope_root,
        },
    )
    return bytes(tile or b"")


async def buildings_tile(session: AsyncSession, z: int, x: int, y: int, *, scope_root: UUID | None) -> bytes:
    validate_tile(z, x, y)
    if z < BUILDINGS_MIN_ZOOM:
        return b""
    await _limit_statement_time(session)
    tile = await session.scalar(
        _BUILDINGS_TILE,
        {"z": z, "x": x, "y": y, "extent": TILE_EXTENT, "buffer": TILE_BUFFER, "scope_root": scope_root},
    )
    return bytes(tile or b"")


async def districts_feature_collection(session: AsyncSession, *, scope_root: UUID | None) -> dict[str, Any]:
    await _limit_statement_time(session)
    rows = (
        await session.execute(
            _AREAS,
            {
                "tolerance": DISTRICT_SIMPLIFY_TOLERANCE,
                "inactive_reports": INACTIVE_REPORT_STATUSES,
                "inactive_incidents": INACTIVE_INCIDENT_STATUSES,
                "scope_root": scope_root,
            },
        )
    ).all()
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": str(row.id),
                "geometry": json.loads(row.geometry),
                "properties": {
                    "district_id": str(row.id),
                    "name": row.name,
                    "type": row.type,
                    "city": row.city,
                    "house_count": int(row.house_count),
                    "active_reports": int(row.active_reports),
                    "active_incidents": int(row.active_incidents),
                },
            }
            for row in rows
        ],
    }


async def incident_houses_feature_collection(
    session: AsyncSession,
    *,
    bbox: tuple[float, float, float, float] | None,
    include_closed: bool,
    scope_root: UUID | None,
) -> dict[str, Any]:
    await _limit_statement_time(session)
    west, south, east, north = bbox or (0.0, 0.0, 0.0, 0.0)
    params = {
        "include_closed": include_closed,
        "inactive_incidents": INACTIVE_INCIDENT_STATUSES,
        "no_bbox": bbox is None,
        "west": west,
        "south": south,
        "east": east,
        "north": north,
        "scope_root": scope_root,
    }
    rows = (await session.execute(_INCIDENT_HOUSES, params)).all()
    unlocated = await session.scalar(_INCIDENT_HOUSES_UNLOCATED, params)
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": str(row.house_id),
                "geometry": json.loads(row.point),
                "properties": {
                    "house_id": str(row.house_id),
                    "address": row.address,
                    "incident_count": len(row.incidents),
                    "incidents": row.incidents,
                },
            }
            for row in rows
        ],
        "metadata": {"located_houses": len(rows), "unlocated_houses": int(unlocated or 0)},
    }


async def cities_summary(session: AsyncSession, *, scope_root: UUID | None) -> list[MapCity]:
    await _limit_statement_time(session)
    rows = (await session.execute(_CITIES_SUMMARY, {"scope_root": scope_root})).all()
    return [
        MapCity(
            city=row.city,
            houses=int(row.houses),
            located=int(row.located),
            unlocated=int(row.houses) - int(row.located),
            with_footprint=int(row.with_footprint),
            buildings=int(row.buildings),
            bbox=(row.min_lon, row.min_lat, row.max_lon, row.max_lat) if row.min_lon is not None else None,
        )
        for row in rows
    ]


async def scope_territory(session: AsyncSession, scope_root: UUID | None) -> MapScope | None:
    if scope_root is None:
        return None
    row = (await session.execute(_SCOPE_TERRITORY, {"scope_root": scope_root})).first()
    return MapScope(territory_id=row.id, name=row.name, type=row.type) if row else None
