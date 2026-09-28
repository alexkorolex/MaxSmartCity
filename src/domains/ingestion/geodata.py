import argparse
import asyncio
import csv
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from src.database.config import DatabaseSettings

GEOLOCATED_STATUSES = frozenset({"matched_polygon", "matched_point"})
BUILDINGS_SOURCE = "microsoft"
BATCH_SIZE = 2000
SOURCE_LIMIT = 64

_VALID_POLYGONS = "ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON({}), 4326)), 3))"


def _batches(rows: list[dict[str, Any]]) -> Iterator[list[dict[str, Any]]]:
    for start in range(0, len(rows), BATCH_SIZE):
        yield rows[start : start + BATCH_SIZE]


def read_geolocations(path: Path) -> list[dict[str, Any]]:
    csv.field_size_limit(sys.maxsize)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [
            {
                "key": row["key"],
                "lon": float(row["longitude"]),
                "lat": float(row["latitude"]),
                "footprint": row.get("geometry_geojson") or None,
                "source": (row.get("source") or "")[:SOURCE_LIMIT] or None,
            }
            for row in csv.DictReader(handle)
            if row.get("match_status") in GEOLOCATED_STATUSES and row.get("latitude") and row.get("longitude")
        ]


def read_building_geometries(path: Path) -> list[str]:
    geometries = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip().lstrip("\x1e")
            if not line:
                continue
            geometry = json.loads(line).get("geometry")
            if geometry and geometry.get("type") in ("Polygon", "MultiPolygon"):
                geometries.append(json.dumps(geometry, separators=(",", ":")))
    return geometries


async def import_geolocations(connection: AsyncConnection, rows: list[dict[str, Any]]) -> int:
    await connection.execute(
        text(
            "CREATE TEMP TABLE geolocation_import "
            "(key text PRIMARY KEY, lon float8, lat float8, footprint text, source text) ON COMMIT DROP"
        )
    )
    for batch in _batches(rows):
        await connection.execute(
            text(
                "INSERT INTO geolocation_import (key, lon, lat, footprint, source) "
                "VALUES (:key, :lon, :lat, :footprint, :source) ON CONFLICT (key) DO NOTHING"
            ),
            batch,
        )
    result = await connection.execute(
        text(
            "WITH located AS ("
            " SELECT hs.house_id,"
            " ST_SetSRID(ST_MakePoint(g.lon, g.lat), 4326)::geography AS point,"
            f" CASE WHEN g.footprint IS NULL THEN NULL ELSE {_VALID_POLYGONS.format('g.footprint')} END"
            " AS footprint,"
            " g.source"
            " FROM geolocation_import g"
            " JOIN ingestion.house_source hs ON hs.source_key = g.key"
            ")"
            " UPDATE geo.house h SET"
            " point = located.point,"
            " footprint = CASE WHEN ST_IsEmpty(located.footprint) THEN NULL ELSE located.footprint END,"
            " geolocation_source = located.source,"
            " updated_at = now()"
            " FROM located WHERE located.house_id = h.id"
        )
    )
    return result.rowcount


async def _city_id(connection: AsyncConnection, city: str) -> UUID:
    existing = (
        await connection.execute(
            text(
                "SELECT id FROM geo.administrative_area "
                "WHERE parent_id IS NULL AND lower(trim(name)) = lower(trim(:name))"
            ),
            {"name": city},
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    city_id = uuid4()
    await connection.execute(
        text(
            "INSERT INTO geo.administrative_area (id, parent_id, name, type, created_at, updated_at) "
            "VALUES (:id, NULL, :name, 'CITY', now(), now())"
        ),
        {"id": city_id, "name": city},
    )
    return city_id


async def import_districts(
    connection: AsyncConnection, features: list[dict[str, Any]], city: str
) -> dict[str, int]:
    city_id = await _city_id(connection, city)
    for feature in features:
        name = " ".join(str(feature["properties"]["name"]).split())
        geometry = json.dumps(feature["geometry"], separators=(",", ":"))
        updated = await connection.execute(
            text(
                "UPDATE geo.administrative_area SET "
                f"geometry = {_VALID_POLYGONS.format(':geometry')}, updated_at = now() "
                "WHERE parent_id = :city_id AND lower(trim(name)) = lower(:name)"
            ),
            {"city_id": city_id, "name": name, "geometry": geometry},
        )
        if updated.rowcount == 0:
            await connection.execute(
                text(
                    "INSERT INTO geo.administrative_area "
                    "(id, parent_id, name, type, geometry, created_at, updated_at) "
                    "VALUES (:id, :city_id, :name, 'DISTRICT', "
                    f"{_VALID_POLYGONS.format(':geometry')}, now(), now())"
                ),
                {"id": uuid4(), "city_id": city_id, "name": name, "geometry": geometry},
            )
    await connection.execute(
        text(
            "UPDATE geo.administrative_area SET geometry = ("
            " SELECT ST_Multi(ST_CollectionExtract(ST_Union(geometry), 3)) FROM geo.administrative_area"
            " WHERE parent_id = :city_id AND geometry IS NOT NULL"
            "), updated_at = now() WHERE id = :city_id"
        ),
        {"city_id": city_id},
    )
    placed = await connection.execute(
        text(
            "UPDATE geo.house h SET administrative_area_id = d.id, updated_at = now() "
            "FROM geo.administrative_area d "
            "WHERE d.parent_id = :city_id AND d.type = 'DISTRICT' AND d.geometry IS NOT NULL "
            "AND h.point IS NOT NULL AND (h.administrative_area_id = :city_id OR ("
            " h.administrative_area_id IS NULL AND EXISTS ("
            "  SELECT 1 FROM geo.address a WHERE a.id = h.address_id"
            "  AND lower(trim(a.city)) = lower(trim(:city_name))"
            "))) "
            "AND ST_Intersects(d.geometry, h.point::geometry)"
        ),
        {"city_id": city_id, "city_name": city},
    )
    return {"districts": len(features), "houses_placed_into_districts": placed.rowcount}


async def import_buildings(connection: AsyncConnection, geometries: list[str], city: str) -> int:
    await connection.execute(
        text("DELETE FROM geo.building_footprint WHERE city = :city AND source = :source"),
        {"city": city, "source": BUILDINGS_SOURCE},
    )
    rows = [
        {"id": uuid4(), "city": city, "source": BUILDINGS_SOURCE, "geometry": geometry}
        for geometry in geometries
    ]
    for batch in _batches(rows):
        await connection.execute(
            text(
                "INSERT INTO geo.building_footprint (id, city, source, geometry, created_at) "
                "SELECT :id, :city, :source, g, now() FROM "
                f"(SELECT {_VALID_POLYGONS.format(':geometry')} AS g) AS valid "
                "WHERE NOT ST_IsEmpty(g)"
            ),
            batch,
        )
    return (
        await connection.execute(
            text("SELECT count(*) FROM geo.building_footprint WHERE city = :city AND source = :source"),
            {"city": city, "source": BUILDINGS_SOURCE},
        )
    ).scalar_one()


async def import_city_boundary(
    connection: AsyncConnection, features: list[dict[str, Any]], city: str
) -> dict[str, int]:
    city_id = await _city_id(connection, city)
    geometries = [json.dumps(feature["geometry"], separators=(",", ":")) for feature in features]
    await connection.execute(
        text(
            "UPDATE geo.administrative_area SET geometry = ("
            f" SELECT ST_Multi(ST_CollectionExtract(ST_Union({_VALID_POLYGONS.format('g')}), 3))"
            " FROM unnest(CAST(:geometries AS text[])) AS g"
            "), updated_at = now() WHERE id = :city_id"
        ),
        {"city_id": city_id, "geometries": geometries},
    )
    placed = await connection.execute(
        text(
            "UPDATE geo.house h SET administrative_area_id = :city_id, updated_at = now() "
            "FROM geo.address a "
            "WHERE a.id = h.address_id AND h.administrative_area_id IS NULL "
            "AND lower(trim(a.city)) = lower(trim(:city_name))"
        ),
        {"city_id": city_id, "city_name": city},
    )
    return {f"city_boundary:{city}": len(features), f"houses_placed_into_city:{city}": placed.rowcount}


async def run(
    *,
    geolocation: Path | None,
    districts: Path | None,
    districts_city: str,
    buildings: list[tuple[str, Path]],
    city_boundaries: list[tuple[str, Path]] | None = None,
    database_url: str | None = None,
) -> dict[str, Any]:
    engine = create_async_engine(database_url or DatabaseSettings.from_environment().url)
    summary: dict[str, Any] = {}
    try:
        if geolocation is not None:
            rows = await asyncio.to_thread(read_geolocations, geolocation)
            async with engine.begin() as connection:
                summary["houses_geolocated"] = await import_geolocations(connection, rows)
                summary["geolocation_rows"] = len(rows)
        if districts is not None:
            features = json.loads(await asyncio.to_thread(districts.read_text, encoding="utf-8"))["features"]
            async with engine.begin() as connection:
                summary |= await import_districts(connection, features, districts_city)
        for city, path in city_boundaries or []:
            features = json.loads(await asyncio.to_thread(path.read_text, encoding="utf-8"))["features"]
            async with engine.begin() as connection:
                summary |= await import_city_boundary(connection, features, city)
        for city, path in buildings:
            geometries = await asyncio.to_thread(read_building_geometries, path)
            async with engine.begin() as connection:
                summary[f"buildings:{city}"] = await import_buildings(connection, geometries, city)
        async with engine.begin() as connection:
            for table in ("geo.house", "geo.administrative_area", "geo.building_footprint"):
                await connection.execute(text(f"ANALYZE {table}"))
    finally:
        await engine.dispose()
    return summary


def _city_path(value: str) -> tuple[str, Path]:
    city, separator, path = value.partition("=")
    if not separator or not city or not path:
        raise argparse.ArgumentTypeError("expected CITY=PATH")
    return city, Path(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import house coordinates, footprints, districts and buildings"
    )
    parser.add_argument("--geolocation", type=Path, help="house_geolocation_multisource.csv")
    parser.add_argument("--districts", type=Path, help="GeoJSON FeatureCollection of city districts")
    parser.add_argument("--districts-city", default="Брянск")
    parser.add_argument("--buildings", type=_city_path, action="append", default=[], metavar="CITY=PATH")
    parser.add_argument(
        "--city-boundary",
        type=_city_path,
        action="append",
        default=[],
        metavar="CITY=PATH",
        help="GeoJSON FeatureCollection with the city boundary; replaces the union of its districts",
    )
    args = parser.parse_args()
    load_dotenv()
    summary = asyncio.run(
        run(
            geolocation=args.geolocation,
            districts=args.districts,
            districts_city=args.districts_city,
            buildings=args.buildings,
            city_boundaries=args.city_boundary,
        )
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
