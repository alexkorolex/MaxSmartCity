from uuid import uuid4

import pytest
from litestar.testing import TestClient

from tests.integration.test_housing_api import _headers, _register_housing_organization
from tests.integration.test_resident_api import (  # noqa: F401
    _insert_affected_house,
    _insert_category,
    _insert_house,
    _insert_incident,
    _insert_report,
    _resident_token,
    _staff_token,
    rsa_keypair,
    run_sql,
    security_env,
)


def _register_authority(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    private_pem: str,
    admin: dict[str, str],
    *,
    name: str,
    kind: str,
    territory_id: str,
) -> tuple[str, dict[str, str]]:
    subject = str(uuid4())

    async def fake_create_staff_user(_settings: object, *, role: str, **_kwargs: object) -> str:
        assert role == "district_admin"
        return subject

    monkeypatch.setattr("src.domains.identity.services.create_staff_user", fake_create_staff_user)
    registered = api_client.post(
        "/identity/organizations/authorities",
        json={
            "name": name,
            "authority_kind": kind,
            "territory_id": territory_id,
            "employee": {"login": f"gov-{uuid4().hex[:8]}", "password": "password-123", "display_name": name},
        },
        headers=admin,
    )
    assert registered.status_code == 201, registered.text
    return registered.json()["organization_id"], _headers(
        _staff_token(private_pem, subject=subject, roles=["district_admin"])
    )


def test_authority_sees_its_territory_in_numbers_and_corresponds_with_platform_and_managers(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_pem, _ = rsa_keypair
    admin = _headers(_staff_token(private_pem, subject=str(uuid4()), roles=["admin"]))
    city = f"Брянск-{uuid4().hex[:6]}"
    house_a = _insert_house(database_url, city=city, street="улица Бежицкая", house_number="1", formatted="a")
    house_b = _insert_house(
        database_url, city=city, street="улица Советская", house_number="2", formatted="b"
    )
    tree = api_client.post("/geo/territories/", json={"name": city, "type": "CITY"}, headers=admin).json()
    city_id = next(node["id"] for node in tree if node["name"] == city and node["parent_id"] is None)

    def district(name: str, street: str) -> str:
        created = api_client.post(
            "/geo/territories/", json={"name": name, "type": "DISTRICT", "parent_id": city_id}, headers=admin
        ).json()
        territory_id = next(
            node["id"] for node in created if node["name"] == name and node["parent_id"] == city_id
        )
        assigned = api_client.post(
            f"/geo/territories/{territory_id}/assign", json={"streets": [street]}, headers=admin
        )
        assert assigned.json() == {"moved": 1}
        return territory_id

    district_a = district("Бежицкий район", "улица Бежицкая")
    district_b = district("Советский район", "улица Советская")

    uk_a, worker_a = _register_housing_organization(api_client, monkeypatch, private_pem, admin, "УК Бежица")
    uk_b, worker_b = _register_housing_organization(
        api_client, monkeypatch, private_pem, admin, "УК Советская"
    )
    for house, organization in ((house_a, uk_a), (house_b, uk_b)):
        managed = api_client.post(
            "/geo/house-management/",
            json={"house_id": house, "organization_id": organization, "basis": "Договор"},
            headers=admin,
        )
        assert managed.status_code == 201, managed.text

    authority_a, gov_a = _register_authority(
        api_client,
        monkeypatch,
        private_pem,
        admin,
        name="Администрация Бежицкого района",
        kind="DISTRICT_ADMINISTRATION",
        territory_id=district_a,
    )
    _city_hall, gov_city = _register_authority(
        api_client,
        monkeypatch,
        private_pem,
        admin,
        name="Брянская городская администрация",
        kind="CITY_ADMINISTRATION",
        territory_id=city_id,
    )
    duplicate = api_client.post(
        "/identity/organizations/authorities",
        json={
            "name": "Ещё одна",
            "authority_kind": "DISTRICT_ADMINISTRATION",
            "territory_id": district_a,
            "employee": {"login": f"gov-{uuid4().hex[:8]}", "password": "password-123", "display_name": "X"},
        },
        headers=admin,
    )
    assert duplicate.status_code == 409
    assert api_client.post("/identity/organizations/authorities", json={}, headers=gov_a).status_code == 403

    category = _insert_category(database_url)
    incident_a = _insert_incident(database_url, category_id=category, status="NEW")
    incident_b = _insert_incident(database_url, category_id=category, status="IN_PROGRESS")
    _insert_affected_house(database_url, incident_id=incident_a, house_id=house_a)
    _insert_affected_house(database_url, incident_id=incident_b, house_id=house_b)
    resident_id, resident_token = _resident_token(api_client)
    api_client.patch("/identity/me/resident", json={"house_id": house_a}, headers=_headers(resident_token))
    report_a = _insert_report(database_url, resident_id=resident_id, house_id=house_a)

    incidents = {item["id"] for item in api_client.get("/incidents/", headers=gov_a).json()}
    assert incident_a in incidents
    assert incident_b not in incidents
    assert api_client.get("/reports/", headers=gov_a).status_code == 403
    assert api_client.get(f"/reports/{report_a}", headers=gov_a).status_code == 404
    assert api_client.get("/identity/residents/", headers=gov_a).status_code == 403
    assert api_client.get(f"/reports/{report_a}/messages", headers=gov_a).status_code == 403
    directory = {item["id"] for item in api_client.get("/identity/organizations/", headers=gov_a).json()}
    assert directory == {authority_a, uk_a}
    assert api_client.get(f"/identity/organizations/{uk_b}", headers=gov_a).status_code == 404
    managed_houses = [
        item["house_id"] for item in api_client.get("/geo/house-management/", headers=gov_a).json()
    ]
    assert managed_houses == [house_a]
    own_tree = api_client.get("/geo/territories/", headers=gov_a).json()
    assert [(node["name"], node["parent_id"]) for node in own_tree] == [("Бежицкий район", None)]

    assert api_client.get(f"/analytics/territories/{city_id}/summary", headers=gov_a).status_code == 403
    own = api_client.get(f"/analytics/territories/{district_a}/summary", headers=gov_a).json()
    assert [item["name"] for item in own["path"]] == ["Бежицкий район"]
    assert (own["total"]["houses"], own["total"]["residents"], own["total"]["reports_total"]) == (1, 1, 1)
    summary = api_client.get(f"/analytics/territories/{city_id}/summary", headers=gov_city).json()
    by_district = {item["territory"]["id"]: item["stats"] for item in summary["children"]}
    assert set(by_district) == {district_a, district_b}
    assert by_district[district_a]["incidents_open"] == 1
    assert by_district[district_b]["incidents_open"] == 1
    assert by_district[district_a]["managing_organizations"] == 1
    assert (
        summary["total"]["houses"],
        summary["total"]["incidents_open"],
        summary["total"]["managing_organizations"],
    ) == (
        2,
        2,
        2,
    )
    assert summary["total"]["houses_without_manager"] == 0

    contacts = api_client.get("/correspondence/contacts", headers=gov_a).json()
    assert [(item["organization_id"], item["kind"]) for item in contacts] == [
        (None, "PLATFORM"),
        (uk_a, "MANAGEMENT_COMPANY"),
    ]
    assert api_client.get("/correspondence/contacts", headers=worker_a).json() == []
    forbidden = api_client.post(
        "/correspondence/conversations",
        json={"organization_id": uk_b, "subject": "Чужая УК", "text": "Здравствуйте"},
        headers=gov_a,
    )
    assert forbidden.status_code == 403
    assert (
        api_client.post(
            "/correspondence/conversations", json={"subject": "Вопрос", "text": "Текст"}, headers=worker_a
        ).status_code
        == 403
    )

    started = api_client.post(
        "/correspondence/conversations",
        json={"organization_id": uk_a, "subject": "Подготовка к зиме", "text": "Пришлите график"},
        headers=gov_a,
    )
    assert started.status_code == 201, started.text
    conversation = started.json()["id"]
    assert started.json()["counterpart_name"] == "УК Бежица"
    assert [
        (item["counterpart_name"], item["unread_count"])
        for item in api_client.get("/correspondence/conversations", headers=worker_a).json()
    ] == [("Администрация Бежицкого района", 1)]
    assert (
        api_client.get(f"/correspondence/conversations/{conversation}", headers=worker_b).status_code == 404
    )
    reply = api_client.post(
        f"/correspondence/conversations/{conversation}/messages", json={"text": "Отправили"}, headers=worker_a
    )
    assert reply.status_code == 201, reply.text
    assert api_client.get("/correspondence/conversations", headers=worker_a).json()[0]["unread_count"] == 0
    authority_view = api_client.get(f"/correspondence/conversations/{conversation}", headers=gov_a).json()
    assert [(item["text"], item["is_mine"]) for item in authority_view["messages"]] == [
        ("Пришлите график", True),
        ("Отправили", False),
    ]
    assert authority_view["counterpart_read_at"] is not None

    to_platform = api_client.post(
        "/correspondence/conversations", json={"subject": "Доступ", "text": "Нужна помощь"}, headers=gov_a
    ).json()
    admin_inbox = api_client.get("/correspondence/conversations", headers=admin).json()
    platform_thread = next(item for item in admin_inbox if item["id"] == to_platform["id"])
    assert (platform_thread["counterpart_name"], platform_thread["unread_count"]) == (
        "Администрация Бежицкого района",
        1,
    )
    assert (
        api_client.post(
            f"/correspondence/conversations/{to_platform['id']}/messages",
            json={"text": "Поможем"},
            headers=admin,
        ).status_code
        == 201
    )
    inbox = {
        item["id"]: item["unread_count"]
        for item in api_client.get("/correspondence/conversations", headers=gov_a).json()
    }
    assert inbox[to_platform["id"]] == 1
    assert (
        api_client.get(f"/correspondence/conversations/{to_platform['id']}", headers=worker_a).status_code
        == 404
    )

    micro = api_client.post(
        "/geo/territories/",
        json={"name": "Микрорайон Мичуринский", "type": "OTHER", "parent_id": district_a},
        headers=gov_a,
    )
    assert micro.status_code == 201, micro.text
    micro_id = next(node["id"] for node in micro.json() if node["name"] == "Микрорайон Мичуринский")
    assert {node["name"] for node in micro.json()} == {"Бежицкий район", "Микрорайон Мичуринский"}
    beyond = {"name": "Чужой район", "type": "DISTRICT", "parent_id": city_id}
    assert api_client.post("/geo/territories/", json=beyond, headers=gov_a).status_code == 403
    assert (
        api_client.post(
            "/geo/territories/", json={"name": "Город", "type": "CITY"}, headers=gov_a
        ).status_code
        == 403
    )
    assert (
        api_client.patch(f"/geo/territories/{district_a}", json={"name": "Х"}, headers=gov_a).status_code
        == 403
    )
    assert api_client.delete(f"/geo/territories/{district_a}", headers=gov_a).status_code == 403
    assert api_client.delete(f"/geo/territories/{district_b}", headers=gov_a).status_code == 403

    streets = api_client.get(f"/geo/territories/{micro_id}/streets", headers=gov_a).json()
    assert [item["street"] for item in streets] == ["улица Бежицкая"]
    assert api_client.get(f"/geo/territories/{district_b}/streets", headers=gov_a).status_code == 403
    outside = api_client.post(
        f"/geo/territories/{micro_id}/assign", json={"house_ids": [house_b]}, headers=gov_a
    )
    assert outside.status_code == 409
    moved = api_client.post(
        f"/geo/territories/{micro_id}/assign",
        json={"streets": ["улица Бежицкая", "улица Советская"]},
        headers=gov_a,
    )
    assert moved.json() == {"moved": 1}
    assert (
        api_client.patch(
            f"/geo/territories/{micro_id}", json={"name": "Мичуринский"}, headers=gov_a
        ).status_code
        == 200
    )
    assert api_client.delete(f"/geo/territories/{micro_id}", headers=gov_a).status_code == 204
    assert (
        api_client.get(f"/analytics/territories/{district_a}/summary", headers=gov_a).json()["total"][
            "houses"
        ]
        == 1
    )

    city_district = api_client.post(
        "/geo/territories/",
        json={"name": "Фокинский район", "type": "DISTRICT", "parent_id": city_id},
        headers=gov_city,
    )
    assert city_district.status_code == 201, city_district.text

    district_staff = api_client.get("/identity/staff-directory/", headers=gov_a).json()
    assert [(item["organization_name"], item["role_code"]) for item in district_staff] == [
        ("УК Бежица", "housing_worker")
    ]
    assert set(district_staff[0]) == {
        "member_id",
        "display_name",
        "role_code",
        "organization_id",
        "organization_name",
    }
    city_staff = api_client.get("/identity/staff-directory/", headers=gov_city).json()
    assert {item["organization_id"] for item in city_staff} == {uk_a, uk_b}
    foreign = api_client.get("/identity/staff-directory/", params={"organization_id": uk_b}, headers=gov_a)
    assert foreign.json() == []
    assert api_client.get("/identity/staff-directory/", headers=worker_a).status_code == 403
