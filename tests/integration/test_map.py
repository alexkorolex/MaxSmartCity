import asyncio
import csv
import json
import math
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from litestar.testing import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.domains.ingestion import geodata
from src.domains.ingestion.importer import import_dataset
from src.map.app import create_map_app
from tests.integration.test_authorities import _register_authority
from tests.integration.test_resident_api import (  # noqa: F401
    _insert_category,
    _insert_incident,
    _resident_token,
    _staff_token,
    rsa_keypair,
    run_sql,
    security_env,
)

LON, LAT = 34.3712, 53.2436
FOOTPRINT = {
    "type": "Polygon",
    "coordinates": [
        [[34.3710, 53.2435], [34.3714, 53.2435], [34.3714, 53.2437], [34.3710, 53.2437], [34.3710, 53.2435]]
    ],
}
DISTRICT = {
    "type": "Polygon",
    "coordinates": [[[34.36, 53.23], [34.39, 53.23], [34.39, 53.26], [34.36, 53.26], [34.36, 53.23]]],
}


def _tile(z: int, lon: float = LON, lat: float = LAT) -> tuple[int, int, int]:
    n = 1 << z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return z, x, y


@pytest.fixture
def map_client(database_url: str) -> Iterator[TestClient]:
    with TestClient(create_map_app(database_url)) as client:
        yield client


def _headers(private_pem: str, *roles: str) -> dict[str, str]:
    token = _staff_token(private_pem, subject=str(uuid4()), roles=list(roles))
    return {"Authorization": f"Bearer {token}"}


async def _scalar(database_url: str, sql: str, **params: object) -> object:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            return (await connection.execute(text(sql), params)).scalar_one()
    finally:
        await engine.dispose()


def scalar(database_url: str, sql: str, **params: object) -> object:
    return asyncio.run(_scalar(database_url, sql, **params))


def _import_city(database_url: str, city: str, tmp_path: Path) -> str:
    key = f"test-map:{uuid4()}"
    dataset = {
        "version": 1,
        "source": {
            "code": f"test-map-{uuid4()}",
            "data_kind": "DEMO",
            "retrieved_at": "2026-09-27T00:00:00+03:00",
        },
        "houses": [{"key": key, "city": city, "street": "улица Картографическая", "house_number": "1"}],
        "organizations": [],
        "links": [],
    }
    asyncio.run(import_dataset(dataset, uuid4().hex, database_url))

    geolocation = tmp_path / "geolocation.csv"
    with geolocation.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["key", "latitude", "longitude", "geometry_geojson", "match_status", "source"]
        )
        writer.writeheader()
        writer.writerow(
            {
                "key": key,
                "latitude": LAT,
                "longitude": LON,
                "geometry_geojson": json.dumps(FOOTPRINT),
                "match_status": "matched_polygon",
                "source": "OpenStreetMap via Geofabrik",
            }
        )
        writer.writerow({"key": f"test-map:{uuid4()}", "match_status": "unmatched"})
    districts = tmp_path / "districts.geojson"
    districts.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "properties": {"name": "Тестовый район"}, "geometry": DISTRICT}
                ],
            }
        ),
        encoding="utf-8",
    )
    buildings = tmp_path / "buildings.geojsonl"
    buildings.write_text(
        json.dumps({"type": "Feature", "properties": {}, "geometry": FOOTPRINT}) + "\n", encoding="utf-8"
    )

    summary = asyncio.run(
        geodata.run(
            geolocation=geolocation,
            districts=districts,
            districts_city=city,
            buildings=[(city, buildings)],
            database_url=database_url,
        )
    )
    assert summary["houses_geolocated"] == 1
    assert summary["districts"] == 1
    assert summary["houses_placed_into_districts"] == 1
    assert summary[f"buildings:{city}"] == 1
    return str(
        scalar(
            database_url,
            "SELECT h.id::text FROM geo.house h JOIN ingestion.house_source hs ON hs.house_id = h.id "
            "WHERE hs.source_key = :key",
            key=key,
        )
    )


def test_geodata_import_places_house_footprint_and_district(database_url: str, tmp_path: Path) -> None:
    city = f"Картоград-{uuid4().hex[:8]}"
    house_id = _import_city(database_url, city, tmp_path)

    assert scalar(database_url, "SELECT footprint IS NOT NULL FROM geo.house WHERE id = :id", id=house_id)
    assert (
        scalar(
            database_url,
            "SELECT a.name FROM geo.house h "
            "JOIN geo.administrative_area a ON a.id = h.administrative_area_id WHERE h.id = :id",
            id=house_id,
        )
        == "Тестовый район"
    )
    assert scalar(
        database_url,
        "SELECT geometry IS NOT NULL FROM geo.administrative_area WHERE parent_id IS NULL AND name = :city",
        city=city,
    )


def test_map_is_only_for_admins_and_authorities(
    map_client: TestClient,
    api_client: TestClient,
    rsa_keypair: tuple[str, str],  # noqa: F811
) -> None:
    private_pem, _ = rsa_keypair
    _, resident_token = _resident_token(api_client)
    resident = {"Authorization": f"Bearer {resident_token}"}

    assert map_client.get("/map/summary").status_code == 401
    assert map_client.get("/map/summary", headers=resident).status_code == 403
    assert map_client.get("/map/summary", headers=_headers(private_pem, "housing_worker")).status_code == 403
    assert map_client.get("/map/summary", headers=_headers(private_pem, "admin")).status_code == 200
    assert (
        map_client.get("/map/incidents", headers=_headers(private_pem, "district_admin")).status_code == 403
    )


def test_map_serves_lazy_vector_tiles_and_district_stats(
    map_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
    tmp_path: Path,
) -> None:
    private_pem, _ = rsa_keypair
    city = f"Картоград-{uuid4().hex[:8]}"
    house_id = _import_city(database_url, city, tmp_path)
    run_sql(
        database_url,
        "INSERT INTO reports.report(id, source_type, house_id, created_at, updated_at) "
        "VALUES (:id, 'MAX', :house_id, now(), now())",
        id=str(uuid4()),
        house_id=house_id,
    )
    headers = _headers(private_pem, "admin")

    z, x, y = _tile(16)
    houses = map_client.get(f"/map/tiles/houses/{z}/{x}/{y}", headers=headers)
    assert houses.status_code == 200
    assert houses.headers["content-type"].startswith("application/vnd.mapbox-vector-tile")
    assert b"houses" in houses.content
    assert house_id.encode() in houses.content

    buildings = map_client.get(f"/map/tiles/buildings/{z}/{x}/{y}", headers=headers)
    assert buildings.status_code == 200
    assert b"buildings" in buildings.content

    z, x, y = _tile(8)
    assert map_client.get(f"/map/tiles/houses/{z}/{x}/{y}", headers=headers).status_code == 204
    assert map_client.get("/map/tiles/houses/3/9/0", headers=headers).status_code == 400

    districts = map_client.get("/map/districts", headers=headers).json()
    (district,) = [feature for feature in districts["features"] if feature["properties"]["city"] == city]
    assert district["geometry"]["type"] in ("Polygon", "MultiPolygon")
    assert district["properties"]["house_count"] == 1
    assert district["properties"]["active_reports"] == 1

    summary = map_client.get("/map/summary", headers=headers).json()
    (stats,) = [item for item in summary["cities"] if item["city"] == city]
    assert stats["located"] == 1
    assert stats["with_footprint"] == 1
    assert stats["buildings"] == 1
    assert summary["zooms"]["houses_min_zoom"] == 12


def test_map_shows_houses_with_incidents_at_any_zoom(
    map_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
    tmp_path: Path,
) -> None:
    private_pem, _ = rsa_keypair
    headers = _headers(private_pem, "admin")
    house_id = _import_city(database_url, f"Картоград-{uuid4().hex[:8]}", tmp_path)
    category_id = _insert_category(database_url)
    active = _insert_incident(database_url, category_id=category_id, status="IN_PROGRESS")
    closed = _insert_incident(database_url, category_id=category_id, status="CLOSED")
    for incident_id in (active, closed):
        run_sql(
            database_url,
            "INSERT INTO incidents.incident_affected_house(incident_id, house_id, source) "
            "VALUES (:incident, :house, 'REPORT')",
            incident=incident_id,
            house=house_id,
        )

    def house_feature(**query: str) -> dict[str, Any] | None:
        body = map_client.get("/map/incidents", params=query, headers=headers).json()
        return next((item for item in body["features"] if item["id"] == house_id), None)

    feature = house_feature(bbox=f"{LON - 0.01},{LAT - 0.01},{LON + 0.01},{LAT + 0.01}")
    assert feature is not None
    assert feature["geometry"]["type"] == "Point"
    assert [item["incident_id"] for item in feature["properties"]["incidents"]] == [active]
    assert feature["properties"]["incidents"][0]["category"] == "Test category"

    history = house_feature(include_closed="true")
    assert history is not None
    assert {item["incident_id"] for item in history["properties"]["incidents"]} == {active, closed}

    assert house_feature(bbox="30.0,50.0,30.1,50.1") is None
    assert map_client.get("/map/incidents", params={"bbox": "1,2,3"}, headers=headers).status_code == 400


def _territory_id(database_url: str, city: str, district: str | None = None) -> str:
    if district is None:
        sql = "SELECT id::text FROM geo.administrative_area WHERE parent_id IS NULL AND name = :city"
        return str(scalar(database_url, sql, city=city))
    sql = (
        "SELECT d.id::text FROM geo.administrative_area d "
        "JOIN geo.administrative_area c ON c.id = d.parent_id "
        "WHERE c.name = :city AND d.name = :district"
    )
    return str(scalar(database_url, sql, city=city, district=district))


def test_authority_sees_only_its_own_territory_on_the_map(
    map_client: TestClient,
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    private_pem, _ = rsa_keypair
    admin = _headers(private_pem, "admin")
    city_a, city_b = f"Картоград-{uuid4().hex[:8]}", f"Картоград-{uuid4().hex[:8]}"
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    house_a = _import_city(database_url, city_a, tmp_path / "a")
    house_b = _import_city(database_url, city_b, tmp_path / "b")
    category_id = _insert_category(database_url)
    for house_id in (house_a, house_b):
        incident_id = _insert_incident(database_url, category_id=category_id, status="IN_PROGRESS")
        run_sql(
            database_url,
            "INSERT INTO incidents.incident_affected_house(incident_id, house_id, source) "
            "VALUES (:incident, :house, 'REPORT')",
            incident=incident_id,
            house=house_id,
        )

    def authority(name: str, kind: str, territory_id: str) -> dict[str, str]:
        _, headers = _register_authority(
            api_client, monkeypatch, private_pem, admin, name=name, kind=kind, territory_id=territory_id
        )
        return headers

    city_hall = authority("Администрация А", "CITY_ADMINISTRATION", _territory_id(database_url, city_a))
    district_a = authority(
        "Район А", "DISTRICT_ADMINISTRATION", _territory_id(database_url, city_a, "Тестовый район")
    )
    district_b = authority(
        "Район Б", "DISTRICT_ADMINISTRATION", _territory_id(database_url, city_b, "Тестовый район")
    )
    z, x, y = _tile(16)

    for headers, own, other, scope_type in (
        (city_hall, house_a, house_b, "CITY"),
        (district_a, house_a, house_b, "DISTRICT"),
        (district_b, house_b, house_a, "DISTRICT"),
    ):
        tile = map_client.get(f"/map/tiles/houses/{z}/{x}/{y}", headers=headers)
        assert tile.status_code == 200
        assert own.encode() in tile.content
        assert other.encode() not in tile.content

        incidents = map_client.get("/map/incidents", headers=headers).json()
        assert [feature["id"] for feature in incidents["features"]] == [own]

        own_city = city_a if own == house_a else city_b
        districts = map_client.get("/map/districts", headers=headers).json()
        assert {feature["properties"]["city"] for feature in districts["features"]} == {own_city}

        summary = map_client.get("/map/summary", headers=headers).json()
        assert [item["city"] for item in summary["cities"]] == [own_city]
        assert summary["scope"]["type"] == scope_type
        assert map_client.get(f"/map/tiles/buildings/{z}/{x}/{y}", headers=headers).status_code == 200

    admin_summary = map_client.get("/map/summary", headers=admin).json()
    assert admin_summary["scope"] is None
    assert {city_a, city_b} <= {item["city"] for item in admin_summary["cities"]}


def test_city_boundary_import_sets_city_geometry_and_places_unassigned_houses(
    database_url: str, tmp_path: Path
) -> None:
    city = f"Бахчиград-{uuid4().hex[:8]}"
    key = f"test-map:{uuid4()}"
    dataset = {
        "version": 1,
        "source": {
            "code": f"test-map-{uuid4()}",
            "data_kind": "DEMO",
            "retrieved_at": "2026-09-28T00:00:00+03:00",
        },
        "houses": [{"key": key, "city": city, "street": "улица Ханская", "house_number": "1"}],
        "organizations": [],
        "links": [],
    }
    asyncio.run(import_dataset(dataset, uuid4().hex, database_url))
    boundary = tmp_path / "boundary.geojson"
    boundary.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [{"type": "Feature", "properties": {"name": city}, "geometry": DISTRICT}],
            }
        ),
        encoding="utf-8",
    )

    summary = asyncio.run(
        geodata.run(
            geolocation=None,
            districts=None,
            districts_city=city,
            buildings=[],
            city_boundaries=[(city, boundary)],
            database_url=database_url,
        )
    )

    assert summary[f"city_boundary:{city}"] == 1
    assert summary[f"houses_placed_into_city:{city}"] == 1
    assert scalar(
        database_url,
        "SELECT ST_IsValid(geometry) FROM geo.administrative_area WHERE parent_id IS NULL AND name = :city",
        city=city,
    )
    assert (
        scalar(
            database_url,
            "SELECT a.name FROM geo.house h JOIN ingestion.house_source hs ON hs.house_id = h.id "
            "JOIN geo.administrative_area a ON a.id = h.administrative_area_id WHERE hs.source_key = :key",
            key=key,
        )
        == city
    )
