"""Coverage for the resident-facing endpoints added for the frontend: report
creation/"mine", incident resolution confirm/dispute + "my house", notifications,
news, and the resident self-profile."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from litestar.testing import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

ISSUER = "http://localhost:8080/realms/maxsmartcity"
AUDIENCE = "maxsmartcity-backend"


@pytest.fixture(scope="module")
def rsa_keypair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


@pytest.fixture(autouse=True)
def security_env(
    monkeypatch: pytest.MonkeyPatch, rsa_keypair: tuple[str, str], api_client: TestClient
) -> None:
    _, public_pem = rsa_keypair
    monkeypatch.setenv("KEYCLOAK_ISSUER", ISSUER)
    monkeypatch.setenv("KEYCLOAK_JWKS_URI", f"{ISSUER}/protocol/openid-connect/certs")
    monkeypatch.setenv("KEYCLOAK_INTERNAL_URL", "http://keycloak:8080")
    monkeypatch.setenv("KEYCLOAK_REALM", "maxsmartcity")
    monkeypatch.setenv("KEYCLOAK_AUDIENCE", AUDIENCE)
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", AUDIENCE)
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("KEYCLOAK_ADMIN", "admin")
    monkeypatch.setenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
    monkeypatch.setenv("RESIDENT_JWT_SECRET", "test-resident-secret-at-least-32-bytes-long")
    monkeypatch.setenv("BOT_SHARED_SECRET", "test-bot-secret")
    monkeypatch.setattr(
        jwt.PyJWKClient,
        "get_signing_key_from_jwt",
        lambda self, token: type("Key", (), {"key": public_pem})(),
    )


def _staff_token(private_pem: str, *, subject: str, roles: list[str]) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": now + timedelta(minutes=5),
        "iat": now,
        "preferred_username": f"user-{subject[:8]}",
        "realm_access": {"roles": roles},
    }
    return jwt.encode(payload, private_pem, algorithm="RS256")


def _resident_token(api_client: TestClient, *, display_name: str = "Resident") -> tuple[str, str]:
    """Registers a fresh resident (bot-issued) and returns ``(resident_id, token)``."""
    max_user_id = uuid4().int % 2_000_000_000
    authenticated = api_client.post(
        "/auth/residents/authenticate",
        json={"max_user_id": max_user_id, "username": f"user{max_user_id}", "display_name": display_name},
        headers={"X-Bot-Secret": "test-bot-secret"},
    )
    assert authenticated.status_code == 201, authenticated.text
    issued = api_client.post(
        "/auth/residents/token",
        json={"max_user_id": max_user_id},
        headers={"X-Bot-Secret": "test-bot-secret"},
    )
    assert issued.status_code == 201, issued.text
    body = issued.json()
    return body["resident_id"], body["token"]


async def _execute(database_url: str, sql: str, **params: object) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(sql), params)
    finally:
        await engine.dispose()


def run_sql(database_url: str, sql: str, **params: object) -> None:
    asyncio.run(_execute(database_url, sql, **params))


def _insert_report(
    database_url: str, *, resident_id: str | None, house_id: str | None = None, source_type: str = "MAX"
) -> str:
    report_id = str(uuid4())
    run_sql(
        database_url,
        "INSERT INTO reports.report(id, resident_id, source_type, house_id, created_at, updated_at) "
        "VALUES (:id, :resident_id, :source_type, :house_id, now(), now())",
        id=report_id,
        resident_id=resident_id,
        source_type=source_type,
        house_id=house_id,
    )
    return report_id


def _insert_category(database_url: str) -> str:
    category_id = str(uuid4())
    run_sql(
        database_url,
        "INSERT INTO reports.problem_category(id, code, name, created_at, updated_at) "
        "VALUES (:id, :code, 'Test category', now(), now())",
        id=category_id,
        code=uuid4().hex,
    )
    return category_id


def _insert_incident(database_url: str, *, category_id: str, status: str) -> str:
    incident_id = str(uuid4())
    run_sql(
        database_url,
        "INSERT INTO incidents.incident(id, title, category_id, status, created_at, updated_at) "
        "VALUES (:id, 'Test incident', :category_id, :status, now(), now())",
        id=incident_id,
        category_id=category_id,
        status=status,
    )
    return incident_id


def _insert_report_link(
    database_url: str, *, incident_id: str, report_id: str, is_active: bool = True
) -> None:
    run_sql(
        database_url,
        "INSERT INTO incidents.incident_report_link(id, incident_id, report_id, is_active, link_source) "
        "VALUES (:id, :incident_id, :report_id, :is_active, 'MANUAL')",
        id=str(uuid4()),
        incident_id=incident_id,
        report_id=report_id,
        is_active=is_active,
    )


def _insert_house(
    database_url: str,
    *,
    city: str | None = None,
    street: str | None = None,
    house_number: str | None = None,
    formatted: str = "Test address",
) -> str:
    address_id = str(uuid4())
    house_id = str(uuid4())
    run_sql(
        database_url,
        "INSERT INTO geo.address(id, formatted, city, street, house_number, created_at, updated_at) "
        "VALUES (:id, :formatted, :city, :street, :house_number, now(), now())",
        id=address_id,
        formatted=formatted,
        city=city,
        street=street,
        house_number=house_number,
    )
    run_sql(
        database_url,
        "INSERT INTO geo.house(id, address_id, created_at, updated_at) "
        "VALUES (:id, :address_id, now(), now())",
        id=house_id,
        address_id=address_id,
    )
    return house_id


def _insert_affected_house(
    database_url: str, *, incident_id: str, house_id: str, source: str = "MANUAL"
) -> None:
    run_sql(
        database_url,
        "INSERT INTO incidents.incident_affected_house(incident_id, house_id, source) "
        "VALUES (:incident_id, :house_id, :source)",
        incident_id=incident_id,
        house_id=house_id,
        source=source,
    )


def _insert_notification(database_url: str, *, resident_id: str, is_read: bool = False) -> str:
    notification_id = str(uuid4())
    run_sql(
        database_url,
        "INSERT INTO notifications.notification"
        "(id, resident_id, type, title, body, is_read, created_at, updated_at) "
        "VALUES (:id, :resident_id, 'GENERIC', 'Title', 'Body', :is_read, now(), now())",
        id=notification_id,
        resident_id=resident_id,
        is_read=is_read,
    )
    return notification_id


# --- Reports: create + "mine" -------------------------------------------------------


def test_resident_creates_and_lists_own_reports_only(api_client: TestClient) -> None:
    resident_a, token_a = _resident_token(api_client, display_name="Alice")
    resident_b, token_b = _resident_token(api_client, display_name="Bob")

    anonymous = api_client.post("/reports/", json={"source_type": "OPERATOR"})
    assert anonymous.status_code == 401

    created = api_client.post(
        "/reports/",
        json={"text": "Труба течёт", "source_type": "SYSTEM", "resident_id": resident_b},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    # server-side override: always MAX-sourced and stamped with the caller's own identity,
    # regardless of what the client attempted to send.
    assert body["source_type"] == "MAX"
    assert body["resident_id"] == resident_a

    api_client.post(
        "/reports/",
        json={"text": "Другое обращение", "source_type": "MAX"},
        headers={"Authorization": f"Bearer {token_b}"},
    )

    mine_a = api_client.get("/reports/mine", headers={"Authorization": f"Bearer {token_a}"})
    assert mine_a.status_code == 200
    ids_a = {item["id"] for item in mine_a.json()}
    assert body["id"] in ids_a
    assert all(item["resident_id"] == resident_a for item in mine_a.json())

    mine_b = api_client.get("/reports/mine", headers={"Authorization": f"Bearer {token_b}"})
    assert body["id"] not in {item["id"] for item in mine_b.json()}

    assert api_client.get("/reports/mine").status_code == 401


def test_reports_mine_route_does_not_collide_with_item_route(api_client: TestClient) -> None:
    _, token = _resident_token(api_client)
    created = api_client.post(
        "/reports/",
        json={"source_type": "MAX"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 201, created.text
    report_id = created.json()["id"]

    by_id = api_client.get(f"/reports/{report_id}", headers={"Authorization": f"Bearer {token}"})
    assert by_id.status_code == 200
    assert by_id.json()["id"] == report_id

    mine = api_client.get("/reports/mine", headers={"Authorization": f"Bearer {token}"})
    assert mine.status_code == 200


# --- Incidents: confirm/dispute resolution + "my house" -----------------------------


def test_confirm_resolution_transitions_incident_and_requires_link(
    api_client: TestClient, database_url: str
) -> None:
    resident_id, token = _resident_token(api_client)
    _other_resident_id, other_token = _resident_token(api_client)

    category_id = _insert_category(database_url)
    report_id = _insert_report(database_url, resident_id=resident_id)
    incident_id = _insert_incident(database_url, category_id=category_id, status="AWAITING_CONFIRMATION")
    _insert_report_link(database_url, incident_id=incident_id, report_id=report_id)

    unrelated = api_client.post(
        f"/incidents/{incident_id}/confirm-resolution",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert unrelated.status_code == 403

    confirmed = api_client.post(
        f"/incidents/{incident_id}/confirm-resolution",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirmed.status_code == 201, confirmed.text
    assert confirmed.json()["status"] == "CLOSED"
    assert confirmed.json()["closed_at"] is not None

    again = api_client.post(
        f"/incidents/{incident_id}/confirm-resolution",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert again.status_code == 409


def test_dispute_resolution_creates_dispute_scoped_to_resident(
    api_client: TestClient, database_url: str
) -> None:
    resident_id, token = _resident_token(api_client)
    _other_resident_id, other_token = _resident_token(api_client)

    category_id = _insert_category(database_url)
    report_id = _insert_report(database_url, resident_id=resident_id)
    incident_id = _insert_incident(database_url, category_id=category_id, status="AWAITING_CONFIRMATION")
    _insert_report_link(database_url, incident_id=incident_id, report_id=report_id)

    disputed = api_client.post(
        f"/incidents/{incident_id}/dispute-resolution",
        json={"comment": "Не устранено"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert disputed.status_code == 201, disputed.text
    assert disputed.json()["comment"] == "Не устранено"
    assert disputed.json()["status"] == "OPEN"

    incident_after = api_client.get(f"/incidents/{incident_id}")
    assert incident_after.json()["status"] == "RESOLUTION_DISPUTED"

    again = api_client.post(
        f"/incidents/{incident_id}/dispute-resolution",
        json={"comment": "Ещё раз"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert again.status_code == 409

    mine = api_client.get(f"/incidents/{incident_id}/disputes", headers={"Authorization": f"Bearer {token}"})
    assert mine.status_code == 200
    assert len(mine.json()) == 1

    others = api_client.get(
        f"/incidents/{incident_id}/disputes", headers={"Authorization": f"Bearer {other_token}"}
    )
    assert others.json() == []


def test_my_house_lists_incidents_affecting_residents_most_recent_house(
    api_client: TestClient, database_url: str
) -> None:
    resident_id, token = _resident_token(api_client)
    empty = api_client.get("/incidents/my-house", headers={"Authorization": f"Bearer {token}"})
    assert empty.status_code == 200
    assert empty.json() == []

    house_id = _insert_house(database_url)
    _insert_report(database_url, resident_id=resident_id, house_id=house_id)

    category_id = _insert_category(database_url)
    incident_id = _insert_incident(database_url, category_id=category_id, status="TRIAGE")
    _insert_affected_house(database_url, incident_id=incident_id, house_id=house_id)

    result = api_client.get("/incidents/my-house", headers={"Authorization": f"Bearer {token}"})
    assert result.status_code == 200
    assert incident_id in {item["id"] for item in result.json()}


# --- Notifications --------------------------------------------------------------------


def test_notifications_are_scoped_and_can_be_marked_read(api_client: TestClient, database_url: str) -> None:
    resident_id, token = _resident_token(api_client)
    other_resident_id, other_token = _resident_token(api_client)

    mine_1 = _insert_notification(database_url, resident_id=resident_id)
    mine_2 = _insert_notification(database_url, resident_id=resident_id)
    _insert_notification(database_url, resident_id=other_resident_id)

    listed = api_client.get("/notifications/", headers={"Authorization": f"Bearer {token}"})
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()}
    assert {mine_1, mine_2} <= ids
    assert all(item["resident_id"] == resident_id for item in listed.json())

    not_found = api_client.post(
        f"/notifications/{mine_1}/read", headers={"Authorization": f"Bearer {other_token}"}
    )
    assert not_found.status_code == 404

    read = api_client.post(f"/notifications/{mine_1}/read", headers={"Authorization": f"Bearer {token}"})
    assert read.status_code == 201, read.text
    assert read.json()["is_read"] is True
    assert read.json()["read_at"] is not None

    read_all = api_client.post("/notifications/read-all", headers={"Authorization": f"Bearer {token}"})
    assert read_all.status_code == 201, read_all.text
    assert read_all.json() == {"updated": 1}

    final = api_client.get("/notifications/", headers={"Authorization": f"Bearer {token}"})
    assert all(item["is_read"] for item in final.json() if item["id"] in {mine_1, mine_2})


# --- News -------------------------------------------------------------------------


def test_news_list_shows_only_published_and_writes_are_staff_only(
    api_client: TestClient, rsa_keypair: tuple[str, str]
) -> None:
    private_pem, _ = rsa_keypair
    staff_token = _staff_token(private_pem, subject=str(uuid4()), roles=["admin"])
    _, resident_token = _resident_token(api_client)

    anonymous_create = api_client.post("/news/", json={"title": "T", "body": "B"})
    assert anonymous_create.status_code == 401

    resident_create = api_client.post(
        "/news/", json={"title": "T", "body": "B"}, headers={"Authorization": f"Bearer {resident_token}"}
    )
    assert resident_create.status_code == 403

    created = api_client.post(
        "/news/",
        json={"title": "Draft", "body": "Body"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert created.status_code == 201, created.text
    post_id = created.json()["id"]
    assert created.json()["is_published"] is False

    published_list = api_client.get("/news/", headers={"Authorization": f"Bearer {resident_token}"})
    assert post_id not in {item["id"] for item in published_list.json()}

    get_unpublished = api_client.get(
        f"/news/{post_id}", headers={"Authorization": f"Bearer {resident_token}"}
    )
    assert get_unpublished.status_code == 200

    published_at = datetime.now(UTC).isoformat()
    updated = api_client.patch(
        f"/news/{post_id}",
        json={"is_published": True, "published_at": published_at},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert updated.status_code == 200, updated.text

    published_list_after = api_client.get("/news/", headers={"Authorization": f"Bearer {resident_token}"})
    assert post_id in {item["id"] for item in published_list_after.json()}

    resident_delete = api_client.delete(
        f"/news/{post_id}", headers={"Authorization": f"Bearer {resident_token}"}
    )
    assert resident_delete.status_code == 403

    staff_delete = api_client.delete(f"/news/{post_id}", headers={"Authorization": f"Bearer {staff_token}"})
    assert staff_delete.status_code == 204


# --- Resident self-profile ---------------------------------------------------------


def test_resident_self_profile_get_and_patch(api_client: TestClient, rsa_keypair: tuple[str, str]) -> None:
    private_pem, _ = rsa_keypair
    resident_id, token = _resident_token(api_client, display_name="Original Name")
    staff_token = _staff_token(private_pem, subject=str(uuid4()), roles=["admin"])

    forbidden = api_client.get("/identity/me/resident", headers={"Authorization": f"Bearer {staff_token}"})
    assert forbidden.status_code == 403

    profile = api_client.get("/identity/me/resident", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["id"] == resident_id
    assert profile.json()["display_name"] == "Original Name"
    assert profile.json()["notifications_enabled"] is True

    updated = api_client.patch(
        "/identity/me/resident",
        json={"notifications_enabled": False, "display_name": "New Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["notifications_enabled"] is False
    assert updated.json()["display_name"] == "New Name"

    refetched = api_client.get("/identity/me/resident", headers={"Authorization": f"Bearer {token}"})
    assert refetched.json()["display_name"] == "New Name"
    assert refetched.json()["notifications_enabled"] is False


# --- Geo: houses, and setting a resident's own home ------------------------------------


def test_geo_houses_lists_and_filters_by_city(api_client: TestClient, database_url: str) -> None:
    bryansk_house = _insert_house(database_url, city="Брянск", street="улица Евдокимова", house_number="8")
    crimea_house = _insert_house(database_url, city="Бахчисарай", street="улица Мира", house_number="9")

    everything = api_client.get("/geo/houses")
    assert everything.status_code == 200
    house_ids = {item["house_id"] for item in everything.json()}
    assert {bryansk_house, crimea_house}.issubset(house_ids)

    filtered = api_client.get("/geo/houses", params={"city": "Брянск"})
    assert filtered.status_code == 200
    filtered_ids = {item["house_id"] for item in filtered.json()}
    assert bryansk_house in filtered_ids
    assert crimea_house not in filtered_ids

    fetched = api_client.get(f"/geo/houses/{bryansk_house}")
    assert fetched.status_code == 200
    assert fetched.json() == {
        "house_id": bryansk_house,
        "city": "Брянск",
        "street": "улица Евдокимова",
        "house_number": "8",
        "formatted": "Test address",
    }

    missing = api_client.get(f"/geo/houses/{uuid4()}")
    assert missing.status_code == 404


def test_resident_can_set_and_change_their_house(api_client: TestClient, database_url: str) -> None:
    resident_id, token = _resident_token(api_client)
    house_a = _insert_house(database_url, city="Брянск")
    house_b = _insert_house(database_url, city="Бахчисарай")

    initial = api_client.get("/identity/me/resident", headers={"Authorization": f"Bearer {token}"})
    assert initial.json()["house_id"] is None

    unknown_house = api_client.patch(
        "/identity/me/resident",
        json={"house_id": str(uuid4())},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert unknown_house.status_code == 404

    set_house = api_client.patch(
        "/identity/me/resident",
        json={"house_id": house_a},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert set_house.status_code == 200, set_house.text
    assert set_house.json()["house_id"] == house_a
    assert set_house.json()["id"] == resident_id

    changed = api_client.patch(
        "/identity/me/resident",
        json={"house_id": house_b},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert changed.status_code == 200
    assert changed.json()["house_id"] == house_b
