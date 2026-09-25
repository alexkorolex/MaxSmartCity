import asyncio
from pathlib import Path
from uuid import uuid4

from litestar.testing import TestClient

from src.domains.ingestion.importer import import_file
from tests.integration.test_ingestion import make_dataset, save


def test_house_geojson_returns_coordinates_and_pagination(
    api_client: TestClient, database_url: str, tmp_path: Path
) -> None:
    city = f"Карта-{uuid4().hex}"
    dataset = make_dataset(f"map-{uuid4()}", city, with_link=False)
    dataset["houses"][0].update({"latitude": 53.21, "longitude": 34.37})
    dataset["houses"].append(
        {
            "key": "house-2",
            "city": city,
            "street": "улица Вторая",
            "house_number": "2",
        }
    )
    asyncio.run(import_file(save(tmp_path / "map.json", dataset), database_url))

    first = api_client.get("/geo/houses/geojson", params={"city": city, "limit": 2})
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["type"] == "FeatureCollection"
    assert body["metadata"] == {
        "city": city,
        "returned": 2,
        "limit": 2,
        "offset": 0,
        "has_more": False,
        "located": 1,
        "unlocated": 1,
        "geometry_source": "HOUSE_OR_ADDRESS_POINT",
        "footprint_area_available": False,
        "median_footprint_area_m2": None,
    }
    feature = body["features"][0]
    assert feature["type"] == "Feature"
    assert feature["properties"]["active_reports"] == 0
    assert feature["properties"]["active_incidents"] == 0
    assert feature["properties"]["footprint_area_m2"] is None
    assert feature["properties"]["size_group"] is None

    assert {item["geometry"] is None for item in body["features"]} == {False, True}

    page = api_client.get("/geo/houses/geojson", params={"city": city, "limit": 1}).json()
    assert page["metadata"]["has_more"] is True
