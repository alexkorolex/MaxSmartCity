import json
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.incidents.enums import IncidentStatus
from src.domains.reports.enums import ReportStatus
from src.map.schemas import MapCity

TILE_EXTENT = 4096
TILE_BUFFER = 64
MAX_ZOOM = 22
HOUSES_MIN_ZOOM = 12
HOUSE_FOOTPRINTS_MIN_ZOOM = 15
BUILDINGS_MIN_ZOOM = 14
STATEMENT_TIMEOUT = "8s"
DISTRICT_SIMPLIFY_TOLERANCE = 0.00005

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

_BOUNDS = (
    "bounds AS (SELECT ST_TileEnvelope(:z, :x, :y) AS env, "
    "ST_Transform(ST_TileEnvelope(:z, :x, :y), 4326) AS env4326)"
)

_ACTIVE_COUNTS = (
    "report_counts AS ("
    " SELECT r.house_id, count(*) AS active_reports FROM reports.report r"
    " JOIN houses hs ON hs.id = r.house_id"
    " WHERE r.status NOT IN :inactive_reports GROUP BY r.house_id"
    "), incident_counts AS ("
    " SELECT iah.house_id, count(*) AS active_incidents FROM incidents.incident_affected_house iah"
    " JOIN houses hs ON hs.id = iah.house_id"
    " JOIN incidents.incident i ON i.id = iah.incident_id"
    " WHERE i.status NOT IN :inactive_incidents GROUP BY iah.house_id"
    ")"
)

_HOUSES_TILE = text(
    f"WITH {_BOUNDS}, "
    "houses AS ("
    " SELECT h.id, a.formatted, h.footprint, h.point"
    " FROM geo.house h JOIN geo.address a ON a.id = h.address_id, bounds b"
    " WHERE h.footprint && b.env4326 OR h.point && b.env4326::geography"
    f"), {_ACTIVE_COUNTS}, tile AS ("
    " SELECT ST_AsMVTGeom("
    "  ST_Transform(CASE WHEN :z >= :footprint_zoom AND hs.footprint IS NOT NULL"
    "   THEN hs.footprint ELSE hs.point::geometry END, 3857),"
    "  b.env, :extent, :buffer, true) AS geom,"
    " hs.id::text AS house_id,"
    " CASE WHEN :z >= :footprint_zoom THEN hs.formatted END AS address,"
    " hs.footprint IS NOT NULL AS has_footprint,"
    " COALESCE(rc.active_reports, 0)::int AS active_reports,"
    " COALESCE(ic.active_incidents, 0)::int AS active_incidents"
    " FROM houses hs CROSS JOIN bounds b"
    " LEFT JOIN report_counts rc ON rc.house_id = hs.id"
    " LEFT JOIN incident_counts ic ON ic.house_id = hs.id"
    ")"
    " SELECT ST_AsMVT(tile.*, 'houses', :extent, 'geom') FROM tile WHERE geom IS NOT NULL"
).bindparams(
    bindparam("inactive_reports", expanding=True),
    bindparam("inactive_incidents", expanding=True),
)

_BUILDINGS_TILE = text(
    f"WITH {_BOUNDS}, tile AS ("
    " SELECT ST_AsMVTGeom(ST_Transform(bf.geometry, 3857), b.env, :extent, :buffer, true) AS geom"
    " FROM geo.building_footprint bf, bounds b WHERE bf.geometry && b.env4326"
    ")"
    " SELECT ST_AsMVT(tile.*, 'buildings', :extent, 'geom') FROM tile WHERE geom IS NOT NULL"
)

_DISTRICTS = text(
    "WITH RECURSIVE subtree AS ("
    " SELECT d.id AS district_id, d.id AS area_id FROM geo.administrative_area d"
    " WHERE d.type = 'DISTRICT' AND d.geometry IS NOT NULL"
    " UNION ALL SELECT s.district_id, a.id FROM geo.administrative_area a"
    " JOIN subtree s ON a.parent_id = s.area_id"
    "), district_houses AS ("
    " SELECT s.district_id, h.id AS house_id FROM subtree s"
    " JOIN geo.house h ON h.administrative_area_id = s.area_id"
    ")"
    " SELECT d.id, d.name, city.name AS city,"
    " ST_AsGeoJSON(ST_SimplifyPreserveTopology(d.geometry, :tolerance), 6) AS geometry,"
    " (SELECT count(*) FROM district_houses dh WHERE dh.district_id = d.id) AS house_count,"
    " (SELECT count(*) FROM district_houses dh JOIN reports.report r ON r.house_id = dh.house_id"
    "  WHERE dh.district_id = d.id AND r.status NOT IN :inactive_reports) AS active_reports,"
    " (SELECT count(DISTINCT iah.incident_id) FROM district_houses dh"
    "  JOIN incidents.incident_affected_house iah ON iah.house_id = dh.house_id"
    "  JOIN incidents.incident i ON i.id = iah.incident_id"
    "  WHERE dh.district_id = d.id AND i.status NOT IN :inactive_incidents) AS active_incidents"
    " FROM geo.administrative_area d JOIN geo.administrative_area city ON city.id = d.parent_id"
    " WHERE d.type = 'DISTRICT' AND d.geometry IS NOT NULL"
    " ORDER BY city.name, d.name"
).bindparams(
    bindparam("inactive_reports", expanding=True),
    bindparam("inactive_incidents", expanding=True),
)

_CITIES_SUMMARY = text(
    "SELECT a.city,"
    " count(*) AS houses,"
    " count(h.point) AS located,"
    " count(h.footprint) AS with_footprint,"
    " ST_XMin(ST_Extent(h.point::geometry)) AS min_lon, ST_YMin(ST_Extent(h.point::geometry)) AS min_lat,"
    " ST_XMax(ST_Extent(h.point::geometry)) AS max_lon, ST_YMax(ST_Extent(h.point::geometry)) AS max_lat,"
    " (SELECT count(*) FROM geo.building_footprint bf WHERE bf.city = a.city) AS buildings"
    " FROM geo.house h JOIN geo.address a ON a.id = h.address_id"
    " WHERE a.city IS NOT NULL GROUP BY a.city ORDER BY a.city"
)


class InvalidTileError(ValueError):
    pass


class InvalidBboxError(ValueError):
    pass


_INCIDENT_HOUSES = """
WITH incident_houses AS (
    SELECT h.id AS house_id, a.formatted AS address,
        COALESCE(h.point::geometry, a.point::geometry) AS point,
        i.id AS incident_id, i.title, i.status, i.priority, pc.name AS category,
        i.first_report_at, i.last_report_at
    FROM incidents.incident i
    JOIN incidents.incident_affected_house iah ON iah.incident_id = i.id
    JOIN geo.house h ON h.id = iah.house_id
    JOIN geo.address a ON a.id = h.address_id
    JOIN reports.problem_category pc ON pc.id = i.category_id
    WHERE (:include_closed OR i.status NOT IN :inactive_incidents)
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

_INCIDENT_HOUSES_UNLOCATED = """
SELECT count(DISTINCT h.id)
FROM incidents.incident i
JOIN incidents.incident_affected_house iah ON iah.incident_id = i.id
JOIN geo.house h ON h.id = iah.house_id
JOIN geo.address a ON a.id = h.address_id
WHERE (:include_closed OR i.status NOT IN :inactive_incidents)
    AND h.point IS NULL AND a.point IS NULL
"""


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


async def incident_houses_feature_collection(
    session: AsyncSession, *, bbox: tuple[float, float, float, float] | None, include_closed: bool
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
    }
    expanding = bindparam("inactive_incidents", expanding=True)
    rows = (await session.execute(text(_INCIDENT_HOUSES).bindparams(expanding), params)).all()
    unlocated = await session.scalar(text(_INCIDENT_HOUSES_UNLOCATED).bindparams(expanding), params)
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


def validate_tile(z: int, x: int, y: int) -> None:
    if not 0 <= z <= MAX_ZOOM:
        raise InvalidTileError(f"z must be between 0 and {MAX_ZOOM}")
    size = 1 << z
    if not (0 <= x < size and 0 <= y < size):
        raise InvalidTileError("x and y are outside the zoom level")


async def _limit_statement_time(session: AsyncSession) -> None:
    await session.execute(text(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT}'"))


async def houses_tile(session: AsyncSession, z: int, x: int, y: int) -> bytes:
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
        },
    )
    return bytes(tile or b"")


async def buildings_tile(session: AsyncSession, z: int, x: int, y: int) -> bytes:
    validate_tile(z, x, y)
    if z < BUILDINGS_MIN_ZOOM:
        return b""
    await _limit_statement_time(session)
    tile = await session.scalar(
        _BUILDINGS_TILE, {"z": z, "x": x, "y": y, "extent": TILE_EXTENT, "buffer": TILE_BUFFER}
    )
    return bytes(tile or b"")


async def districts_feature_collection(session: AsyncSession) -> dict[str, Any]:
    await _limit_statement_time(session)
    rows = (
        await session.execute(
            _DISTRICTS,
            {
                "tolerance": DISTRICT_SIMPLIFY_TOLERANCE,
                "inactive_reports": INACTIVE_REPORT_STATUSES,
                "inactive_incidents": INACTIVE_INCIDENT_STATUSES,
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
                    "city": row.city,
                    "house_count": int(row.house_count),
                    "active_reports": int(row.active_reports),
                    "active_incidents": int(row.active_incidents),
                },
            }
            for row in rows
        ],
    }


async def cities_summary(session: AsyncSession) -> list[MapCity]:
    await _limit_statement_time(session)
    rows = (await session.execute(_CITIES_SUMMARY)).all()
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
