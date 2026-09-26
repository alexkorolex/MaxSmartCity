import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from litestar.testing import TestClient

from src.domains.ingestion.importer import import_file
from tests.integration.test_ingestion import rows, save
from tests.integration.test_resident_api import (  # noqa: F401
    _insert_house,
    _staff_token,
    rsa_keypair,
    run_sql,
    security_env,
)


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _house(database_url: str, city: str, street: str, number: str) -> str:
    return _insert_house(
        database_url, city=city, street=street, house_number=number, formatted=f"{city}, {street}, {number}"
    )


def _area_of(database_url: str, house_id: str) -> str | None:
    (row,) = asyncio.run(
        rows(database_url, "SELECT administrative_area_id FROM geo.house WHERE id = :id", id=house_id)
    )
    return None if row[0] is None else str(row[0])


def _node(tree: list[dict[str, object]], name: str, parent_id: object = None) -> dict[str, object]:
    return next(node for node in tree if node["name"] == name and node["parent_id"] == parent_id)


def test_admin_builds_a_city_tree_and_assigns_houses_by_street(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
) -> None:
    private_pem, _ = rsa_keypair
    admin = _headers(_staff_token(private_pem, subject=str(uuid4()), roles=["admin"]))
    city = f"Брянск-{uuid4().hex[:6]}"
    lenina_1 = _house(database_url, city, "улица Ленина", "1")
    lenina_2 = _house(database_url, city, "улица Ленина", "2")
    mira = _house(database_url, city, "улица Мира", "5")
    elsewhere = _house(database_url, f"Другой-{uuid4().hex[:6]}", "улица Ленина", "1")

    assert (
        api_client.post(
            "/geo/territories/", json={"name": "Район", "type": "DISTRICT"}, headers=admin
        ).status_code
        == 409
    )
    tree = api_client.post(
        "/geo/territories/", json={"name": f" {city} ", "type": "CITY"}, headers=admin
    ).json()
    root = _node(tree, city)
    assert (root["house_count"], root["direct_house_count"]) == (3, 3)
    assert _area_of(database_url, elsewhere) is None

    def child(name: str, parent: object, type: str = "DISTRICT") -> str:
        created = api_client.post(
            "/geo/territories/", json={"name": name, "type": type, "parent_id": parent}, headers=admin
        )
        assert created.status_code == 201, created.text
        return str(_node(created.json(), name, parent)["id"])

    bezhitsky = child("Бежицкий район", root["id"])
    sovetsky = child("Советский район", root["id"])
    assert (
        api_client.post(
            "/geo/territories/",
            json={"name": "бежицкий  район", "type": "DISTRICT", "parent_id": root["id"]},
            headers=admin,
        ).status_code
        == 409
    )
    assert (
        api_client.patch(f"/geo/territories/{root['id']}", json={"name": "Орёл"}, headers=admin).status_code
        == 409
    )

    streets = api_client.get(f"/geo/territories/{bezhitsky}/streets", headers=admin).json()
    assert [(item["street"], item["house_count"]) for item in streets] == [
        ("улица Ленина", 2),
        ("улица Мира", 1),
    ]

    moved = api_client.post(
        f"/geo/territories/{bezhitsky}/assign", json={"streets": ["улица Ленина"]}, headers=admin
    )
    assert moved.json() == {"moved": 2}
    split = api_client.post(
        f"/geo/territories/{sovetsky}/assign", json={"house_ids": [lenina_2]}, headers=admin
    )
    assert split.json() == {"moved": 1}
    foreign = api_client.post(
        f"/geo/territories/{sovetsky}/assign", json={"house_ids": [elsewhere]}, headers=admin
    )
    assert foreign.status_code == 409
    assert (_area_of(database_url, lenina_1), _area_of(database_url, lenina_2)) == (bezhitsky, sovetsky)
    assert _area_of(database_url, mira) == root["id"]

    street_houses = api_client.get(
        f"/geo/territories/{bezhitsky}/houses", params={"street": "улица Ленина"}, headers=admin
    ).json()
    assert [(item["house_number"], item["territory_name"]) for item in street_houses] == [
        ("1", "Бежицкий район"),
        ("2", "Советский район"),
    ]

    microdistrict = child("Микрорайон Октябрьский", bezhitsky, "OTHER")
    assert (
        api_client.post(
            f"/geo/territories/{microdistrict}/assign", json={"house_ids": [lenina_1]}, headers=admin
        ).status_code
        == 201
    )
    tree = api_client.get("/geo/territories/", headers=admin).json()
    assert _node(tree, "Бежицкий район", root["id"])["house_count"] == 1
    assert _node(tree, city)["house_count"] == 3

    assert (
        api_client.patch(
            f"/geo/territories/{microdistrict}", json={"parent_id": microdistrict}, headers=admin
        ).status_code
        == 409
    )
    assert api_client.delete(f"/geo/territories/{bezhitsky}", headers=admin).status_code == 409
    assert api_client.delete(f"/geo/territories/{microdistrict}", headers=admin).status_code == 204
    assert _area_of(database_url, lenina_1) == bezhitsky
    assert api_client.delete(f"/geo/territories/{bezhitsky}", headers=admin).status_code == 204
    assert _area_of(database_url, lenina_1) == root["id"]

    worker = _headers(_staff_token(private_pem, subject=str(uuid4()), roles=["housing_worker"]))
    assert api_client.get("/geo/territories/", headers=worker).status_code == 403
    assert (
        api_client.post(
            f"/geo/territories/{sovetsky}/assign", json={"house_ids": [mira]}, headers=worker
        ).status_code
        == 403
    )


@pytest.mark.anyio
async def test_import_places_houses_by_the_district_in_the_dataset(database_url: str, tmp_path: Path) -> None:
    city = f"Бахчисарай-{uuid4().hex[:6]}"
    code = f"test-territories-{uuid4()}"

    def dataset(timestamp: str, **extra: str) -> dict[str, object]:
        return {
            "version": 1,
            "source": {"code": code, "data_kind": "DEMO", "retrieved_at": timestamp},
            "houses": [
                {"key": "h-1", "city": city, "street": "улица Мира", "house_number": "3", **extra},
                {"key": "h-2", "city": city, "street": "улица Мира", "house_number": "9"},
            ],
            "organizations": [],
            "links": [],
        }

    first = await import_file(
        save(tmp_path / "first.json", dataset("2026-09-26T10:00:00+03:00", district="Центральный район")),
        database_url,
    )
    assert first["error_count"] == 0
    placed = await rows(
        database_url,
        "SELECT a.street || ' ' || a.house_number, area.name, area.type, parent.name "
        "FROM geo.house h JOIN geo.address a ON a.id = h.address_id "
        "LEFT JOIN geo.administrative_area area ON area.id = h.administrative_area_id "
        "LEFT JOIN geo.administrative_area parent ON parent.id = area.parent_id "
        "WHERE a.city = :city ORDER BY 1",
        city=city,
    )
    assert [tuple(row) for row in placed] == [
        ("улица Мира 3", "Центральный район", "DISTRICT", city),
        ("улица Мира 9", city, "CITY", None),
    ]

    await import_file(save(tmp_path / "second.json", dataset("2026-09-26T11:00:00+03:00")), database_url)
    again = await rows(
        database_url,
        "SELECT area.name FROM geo.house h JOIN geo.address a ON a.id = h.address_id "
        "JOIN geo.administrative_area area ON area.id = h.administrative_area_id "
        "WHERE a.city = :city ORDER BY a.house_number",
        city=city,
    )
    assert [row[0] for row in again] == ["Центральный район", city]
