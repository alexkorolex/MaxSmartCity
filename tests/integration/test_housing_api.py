"""API surface for housing organizations: admin registration together with the first
employee, organization members, house management, notification channels, and how a
housing worker's visibility is confined to their own organization's houses."""

from uuid import uuid4

import pytest
from litestar.testing import TestClient

from tests.integration.test_housing_organizations import random_inn, random_ogrn
from tests.integration.test_resident_api import (  # noqa: F401
    _insert_affected_house,
    _insert_category,
    _insert_house,
    _insert_incident,
    _insert_report,
    _resident_token,
    _staff_token,
    rsa_keypair,
    security_env,
)


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_registers_organization_with_employee_who_gets_houses_and_channels(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_pem, _ = rsa_keypair
    keycloak_subjects: dict[str, str] = {}

    async def fake_create_staff_user(_settings: object, *, login: str, **_kwargs: object) -> str:
        keycloak_subjects[login] = str(uuid4())
        return keycloak_subjects[login]

    monkeypatch.setattr("src.domains.identity.services.create_staff_user", fake_create_staff_user)
    admin = _headers(_staff_token(private_pem, subject=str(uuid4()), roles=["admin"]))
    outsider = _headers(_staff_token(private_pem, subject=str(uuid4()), roles=["housing_worker"]))
    login = f"uk-{uuid4().hex[:8]}"
    payload = {
        "code": uuid4().hex,
        "name": "УК Уютный дом",
        "type": "MANAGEMENT_COMPANY",
        "inn": random_inn(),
        "ogrn": random_ogrn(),
        "license_number": "077-000321",
        "in_reserve_registry": True,
        "city": "Брянск",
        "employee": {"login": login, "password": "password-123", "display_name": "Иван Диспетчер"},
    }

    forbidden = api_client.post("/identity/organizations/register", json=payload, headers=outsider)
    assert forbidden.status_code == 403
    invalid = api_client.post(
        "/identity/organizations/register", json={**payload, "license_number": None}, headers=admin
    )
    assert invalid.status_code == 400, invalid.text
    assert keycloak_subjects == {}

    registered = api_client.post("/identity/organizations/register", json=payload, headers=admin)
    assert registered.status_code == 201, registered.text
    organization_id = registered.json()["organization_id"]
    assert registered.json()["employee"]["login"] == login
    organization = api_client.get(f"/identity/organizations/{organization_id}", headers=admin).json()
    assert organization["registration_status"] == "APPROVED"
    assert organization["enabled"] is True

    director = _headers(_staff_token(private_pem, subject=keycloak_subjects[login], roles=["housing_worker"]))
    assert api_client.get("/identity/me/", headers=director).json()["organization_id"] == organization_id

    worker_login = f"worker-{uuid4().hex[:8]}"
    worker = {"login": worker_login, "password": "password-123", "display_name": "Мастер"}
    accounts_path = f"/identity/organizations/{organization_id}/members/accounts"
    assert api_client.post(accounts_path, json=worker, headers=director).status_code == 403
    created = api_client.post(accounts_path, json=worker, headers=admin)
    assert created.status_code == 201, created.text

    members = api_client.get(f"/identity/organizations/{organization_id}/members/", headers=director)
    assert members.status_code == 200, members.text
    assert sorted(member["login"] for member in members.json()) == sorted([login, worker_login])
    assert (
        api_client.get(f"/identity/organizations/{organization_id}/members/", headers=outsider).status_code
        == 403
    )
    organization = {"id": organization_id}

    house_id = _insert_house(database_url, formatted="г. Брянск, ул. Ленина, 1")
    assignment = {
        "house_id": house_id,
        "organization_id": organization["id"],
        "basis": "Решение администрации об определении УК из Перечня",
        "assigned_via_reserve_registry": True,
    }
    # Any staff without that organization can't attach houses to it...
    assert api_client.post("/geo/house-management/", json=assignment, headers=outsider).status_code == 403
    # ...but its own employee takes a free house for it themselves.
    assigned = api_client.post("/geo/house-management/", json=assignment, headers=director)
    assert assigned.status_code == 201, assigned.text
    assert assigned.json()["house_formatted"] == "г. Брянск, ул. Ленина, 1"

    mine = api_client.get("/geo/house-management/", headers=director)
    assert [item["house_id"] for item in mine.json()] == [house_id]
    public = api_client.get(f"/geo/houses/{house_id}/management")
    assert public.status_code == 200
    assert public.json()["organization_name"] == "УК Уютный дом"

    channel = api_client.post(
        "/notifications/organization-channels/",
        json={"organization_id": organization["id"], "type": "MAX_CHAT", "target": "-100500"},
        headers=director,
    )
    assert channel.status_code == 201, channel.text
    assert "secret" not in channel.json()
    webhook = api_client.post(
        "/notifications/organization-channels/",
        json={"organization_id": organization["id"], "type": "WEBHOOK", "target": "https://crm.example/h"},
        headers=director,
    )
    assert webhook.status_code == 403
    bad_target = api_client.post(
        "/notifications/organization-channels/",
        json={"organization_id": organization["id"], "type": "EMAIL", "target": "nope"},
        headers=director,
    )
    assert bad_target.status_code == 400
    listed = api_client.get("/notifications/organization-channels/", headers=director)
    assert [item["type"] for item in listed.json()] == ["MAX_CHAT"]
    foreign = api_client.post(
        f"/notifications/organization-channels/{channel.json()['id']}/deactivate", headers=outsider
    )
    assert foreign.status_code == 403


def _register_housing_organization(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    private_pem: str,
    admin: dict[str, str],
    name: str,
) -> tuple[str, dict[str, str]]:
    """Admin registers a УК with one employee; returns ``(organization_id, employee headers)``."""
    subject = str(uuid4())

    async def fake_create_staff_user(_settings: object, **_kwargs: object) -> str:
        return subject

    monkeypatch.setattr("src.domains.identity.services.create_staff_user", fake_create_staff_user)
    registered = api_client.post(
        "/identity/organizations/register",
        json={
            "code": uuid4().hex,
            "name": name,
            "type": "MANAGEMENT_COMPANY",
            "inn": random_inn(),
            "ogrn": random_ogrn(),
            "license_number": "077-000999",
            "employee": {"login": f"uk-{uuid4().hex[:8]}", "password": "password-123", "display_name": name},
        },
        headers=admin,
    )
    assert registered.status_code == 201, registered.text
    token = _staff_token(private_pem, subject=subject, roles=["housing_worker"])
    return registered.json()["organization_id"], _headers(token)


def test_housing_worker_works_only_through_their_own_houses(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_pem, _ = rsa_keypair
    admin = _headers(_staff_token(private_pem, subject=str(uuid4()), roles=["admin"]))
    org_a, worker_a = _register_housing_organization(api_client, monkeypatch, private_pem, admin, "УК А")
    org_b, worker_b = _register_housing_organization(api_client, monkeypatch, private_pem, admin, "УК Б")
    house_a = _insert_house(database_url, formatted=f"ул. Первая, {uuid4().hex[:6]}")
    house_b = _insert_house(database_url, formatted=f"ул. Вторая, {uuid4().hex[:6]}")

    def take(house_id: str, organization_id: str, headers: dict[str, str]) -> int:
        body = {"house_id": house_id, "organization_id": organization_id, "basis": "Договор управления №1"}
        return api_client.post("/geo/house-management/", json=body, headers=headers).status_code

    assert take(house_a, org_a, worker_a) == 201
    assert take(house_b, org_b, worker_b) == 201
    assert take(house_a, org_b, worker_b) == 409  # already managed by another УК
    assert take(house_b, org_a, worker_b) == 403  # not worker B's organization

    # Other УК/ТСЖ are invisible.
    visible = api_client.get("/identity/organizations/", headers=worker_a).json()
    assert [org["id"] for org in visible] == [org_a]
    assert api_client.get(f"/identity/organizations/{org_b}", headers=worker_a).status_code == 404
    assert api_client.get(f"/identity/organizations/{org_b}", headers=admin).status_code == 200

    # Residents: those living in (or reporting about) the organization's houses only.
    living_a, token_a = _resident_token(api_client)
    living_b, token_b = _resident_token(api_client)
    for token, house in ((token_a, house_a), (token_b, house_b)):
        moved = api_client.patch("/identity/me/resident", json={"house_id": house}, headers=_headers(token))
        assert moved.status_code == 200, moved.text
    reporter, _ = _resident_token(api_client)
    report_a = _insert_report(database_url, resident_id=reporter, house_id=house_a)
    report_b = _insert_report(database_url, resident_id=living_b, house_id=house_b)

    residents = {item["id"] for item in api_client.get("/identity/residents/", headers=worker_a).json()}
    assert {living_a, reporter} <= residents
    assert living_b not in residents
    assert api_client.get(f"/identity/residents/{living_b}", headers=worker_a).status_code == 404

    reports = {item["id"] for item in api_client.get("/reports/", headers=worker_a).json()}
    assert report_a in reports
    assert report_b not in reports
    assert api_client.get(f"/reports/{report_b}", headers=worker_a).status_code == 404

    category_id = _insert_category(database_url)
    incident_a = _insert_incident(database_url, category_id=category_id, status="NEW")
    incident_b = _insert_incident(database_url, category_id=category_id, status="NEW")
    _insert_affected_house(database_url, incident_id=incident_a, house_id=house_a)
    _insert_affected_house(database_url, incident_id=incident_b, house_id=house_b)
    incidents = {item["id"] for item in api_client.get("/incidents/", headers=worker_a).json()}
    assert incident_a in incidents
    assert incident_b not in incidents
    assert api_client.get(f"/incidents/{incident_b}/card", headers=worker_a).status_code == 404

    # Releasing a house: only one's own.
    managed_b = api_client.get("/geo/house-management/", headers=worker_b).json()
    assert [item["house_id"] for item in managed_b] == [house_b]
    terminate_b = f"/geo/house-management/{managed_b[0]['id']}/terminate"
    assert api_client.post(terminate_b, json={}, headers=worker_a).status_code == 404
    assert api_client.post(terminate_b, json={}, headers=worker_b).status_code == 200

    # The house picker shows who manages what, and searches by address.
    found = api_client.get("/geo/houses/", params={"q": "ул. Первая"}, headers=worker_a).json()
    picked = next(item for item in found if item["house_id"] == house_a)
    assert picked["managed_by_organization_name"] == "УК А"
