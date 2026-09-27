import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import UUID, uuid4

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from litestar.testing import TestClient

from src.max_bot.dedup import create_login_code
from src.security.keycloak import KeycloakLoginError

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


def test_department_mutation_requires_admin_role(
    api_client: TestClient, rsa_keypair: tuple[str, str]
) -> None:
    private_pem, _ = rsa_keypair
    admin_token = _staff_token(private_pem, subject=str(uuid4()), roles=["admin"])
    org = api_client.post(
        "/identity/organizations",
        json={"code": f"org-{uuid4().hex[:8]}", "name": "Utility", "type": "WATER_UTILITY"},
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()

    anonymous = api_client.post(
        "/identity/departments", json={"organization_id": org["id"], "code": "d1", "name": "Repairs"}
    )
    assert anonymous.status_code == 401

    worker_token = _staff_token(private_pem, subject=str(uuid4()), roles=["housing_worker"])
    forbidden = api_client.post(
        "/identity/departments",
        json={"organization_id": org["id"], "code": "d1", "name": "Repairs"},
        headers={"Authorization": f"Bearer {worker_token}"},
    )
    assert forbidden.status_code == 403

    created = api_client.post(
        "/identity/departments",
        json={"organization_id": org["id"], "code": "d1", "name": "Repairs"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert created.status_code == 201, created.text


def test_staff_login_provisions_stable_local_operator(
    api_client: TestClient, rsa_keypair: tuple[str, str]
) -> None:
    private_pem, _ = rsa_keypair
    subject = str(uuid4())
    token = _staff_token(private_pem, subject=subject, roles=["district_admin"])

    first = api_client.get("/identity/me", headers={"Authorization": f"Bearer {token}"}).json()
    second = api_client.get("/identity/me", headers={"Authorization": f"Bearer {token}"}).json()

    assert first["actor_type"] == "OPERATOR"
    assert first["roles"] == ["district_admin"]
    assert first["actor_id"] == second["actor_id"]


def test_resident_auth_and_token_flow(api_client: TestClient) -> None:
    rejected = api_client.post(
        "/auth/residents/authenticate",
        json={"max_user_id": 424242, "username": "res", "display_name": "Resident"},
    )
    assert rejected.status_code == 401

    authenticated = api_client.post(
        "/auth/residents/authenticate",
        json={"max_user_id": 424242, "username": "res", "display_name": "Resident"},
        headers={"X-Bot-Secret": "test-bot-secret"},
    )
    assert authenticated.status_code == 201, authenticated.text
    resident_id = authenticated.json()["resident_id"]

    token_without_secret = api_client.post("/auth/residents/token", json={"max_user_id": 424242})
    assert token_without_secret.status_code == 401

    unknown_resident = api_client.post(
        "/auth/residents/token", json={"max_user_id": 999999}, headers={"X-Bot-Secret": "test-bot-secret"}
    )
    assert unknown_resident.status_code == 404

    issued = api_client.post(
        "/auth/residents/token", json={"max_user_id": 424242}, headers={"X-Bot-Secret": "test-bot-secret"}
    )
    assert issued.status_code == 201, issued.text
    assert issued.json()["resident_id"] == resident_id
    token = issued.json()["token"]

    me = api_client.get("/identity/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json() == {
        "actor_type": "RESIDENT",
        "actor_id": resident_id,
        "roles": [],
        "organization_id": None,
        "department_id": None,
    }

    admin_only = api_client.post(
        "/identity/departments",
        json={"organization_id": resident_id, "code": "d1", "name": "Repairs"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert admin_only.status_code == 403

    # /geo/houses is intentionally public (unlike /reports and /incidents below): the
    # resident house-picker (and admin-panel city filters) need it before login.
    assert api_client.get("/geo/houses").status_code == 200
    assert api_client.get("/reports").status_code == 401
    assert api_client.get("/incidents").status_code == 401

    resident_headers = {"Authorization": f"Bearer {token}"}
    assert api_client.get("/geo/houses", headers=resident_headers).status_code == 200
    assert api_client.get("/reports/mine", headers=resident_headers).status_code == 200
    assert api_client.get("/incidents/my-house", headers=resident_headers).status_code == 200
    assert api_client.get("/reports", headers=resident_headers).status_code == 403
    assert api_client.get("/incidents", headers=resident_headers).status_code == 403


@pytest.mark.anyio
async def test_resident_web_login_redeems_bot_issued_code(api_client: TestClient) -> None:
    """The bridge the MAX bot uses: a code minted for a resident (e.g. in
    ``src.max_bot.handlers``) can be redeemed by the resident's own browser for a JWT,
    with no bot secret involved."""
    authenticated = api_client.post(
        "/auth/residents/authenticate",
        json={"max_user_id": 909090, "username": "webuser", "display_name": "Web User"},
        headers={"X-Bot-Secret": "test-bot-secret"},
    )
    assert authenticated.status_code == 201, authenticated.text
    resident_id = authenticated.json()["resident_id"]

    code = await create_login_code(UUID(resident_id))

    rejected = api_client.post("/auth/residents/login", json={"code": "not-a-real-code"})
    assert rejected.status_code == 401

    logged_in = api_client.post("/auth/residents/login", json={"code": code})
    assert logged_in.status_code == 201, logged_in.text
    assert logged_in.json()["resident_id"] == resident_id

    reused = api_client.post("/auth/residents/login", json={"code": code})
    assert reused.status_code == 401  # single-use

    me = api_client.get("/identity/me", headers={"Authorization": f"Bearer {logged_in.json()['token']}"})
    assert me.status_code == 200
    assert me.json()["actor_id"] == resident_id


def test_resident_signs_in_silently_with_max_web_app_init_data(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MAX_BOT_TOKEN", "web-app-bot-token")
    monkeypatch.setenv("MAX_WEBHOOK_SECRET", "web-app-webhook-secret")
    monkeypatch.setenv("WEB_APP_LOGIN_URL", "https://example.test/auth/max")
    user = json.dumps({"id": 707070, "first_name": "Мария", "username": "maria"}, ensure_ascii=False)
    fields = {"auth_date": str(int(time.time())), "query_id": "q", "user": user}
    launch_params = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", b"web-app-bot-token", hashlib.sha256).digest()
    signature = hmac.new(secret_key, launch_params.encode(), hashlib.sha256).hexdigest()
    init_data = urlencode({**fields, "hash": signature})

    first = api_client.post("/auth/residents/max-web-app", json={"init_data": init_data})
    assert first.status_code == 201, first.text
    again = api_client.post("/auth/residents/max-web-app", json={"init_data": init_data})
    assert again.status_code == 201, again.text
    assert again.json()["resident_id"] == first.json()["resident_id"]

    me = api_client.get("/identity/me", headers={"Authorization": f"Bearer {again.json()['token']}"})
    assert me.status_code == 200
    assert me.json()["actor_id"] == first.json()["resident_id"]

    forged = api_client.post(
        "/auth/residents/max-web-app", json={"init_data": init_data.replace("707070", "707071")}
    )
    assert forged.status_code == 401


def test_staff_member_edits_own_profile_password_and_max_link(
    api_client: TestClient, rsa_keypair: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    private_pem, _ = rsa_keypair
    subject = str(uuid4())
    # Keycloak also puts its technical default role into every token.
    token = _staff_token(private_pem, subject=subject, roles=["default-roles-maxsmartcity", "housing_worker"])
    headers = {"Authorization": f"Bearer {token}"}
    keycloak_calls: list[tuple[str, dict[str, object]]] = []

    async def fake_update(_settings: object, **kwargs: object) -> None:
        keycloak_calls.append(("update", kwargs))

    async def fake_set_password(_settings: object, **kwargs: object) -> None:
        keycloak_calls.append(("password", kwargs))

    async def fake_login(_settings: object, *, username: str, password: str) -> dict[str, object]:
        if password != "old-password":
            raise KeycloakLoginError("Invalid user credentials")
        return {"access_token": "token"}

    monkeypatch.setattr("src.domains.auth.controllers.update_staff_user", fake_update)
    monkeypatch.setattr("src.domains.auth.controllers.set_staff_password", fake_set_password)
    monkeypatch.setattr("src.domains.auth.controllers.login_staff_with_password", fake_login)

    profile = api_client.get("/auth/staff/profile", headers=headers)
    assert profile.status_code == 200, profile.text
    assert profile.json()["role_code"] == "housing_worker"
    assert profile.json()["email"] is None

    invalid = api_client.patch(
        "/auth/staff/profile", json={"display_name": "Иван Петров", "email": "not-an-email"}, headers=headers
    )
    assert invalid.status_code == 400
    updated = api_client.patch(
        "/auth/staff/profile", json={"display_name": " Иван Петров ", "email": "ivan@uk.ru"}, headers=headers
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["display_name"] == "Иван Петров"
    assert updated.json()["email"] == "ivan@uk.ru"
    assert keycloak_calls[-1] == (
        "update",
        {"subject": subject, "display_name": "Иван Петров", "email": "ivan@uk.ru"},
    )

    wrong_current = api_client.post(
        "/auth/staff/password",
        json={"current_password": "guess", "new_password": "brand-new-pass"},
        headers=headers,
    )
    # 400, never 401 - a 401 would sign the staff member out of the panel.
    assert wrong_current.status_code == 400
    too_short = api_client.post(
        "/auth/staff/password",
        json={"current_password": "old-password", "new_password": "short"},
        headers=headers,
    )
    assert too_short.status_code == 400
    changed = api_client.post(
        "/auth/staff/password",
        json={"current_password": "old-password", "new_password": "brand-new-pass"},
        headers=headers,
    )
    assert changed.status_code == 204, changed.text
    assert keycloak_calls[-1] == ("password", {"subject": subject, "password": "brand-new-pass"})

    assert (
        api_client.post("/auth/staff/max-id", json={"max_user_id": 777001}, headers=headers).status_code
        == 201
    )
    assert api_client.get("/auth/staff/profile", headers=headers).json()["max_user_id"] == 777001
    assert api_client.delete("/auth/staff/max-id", headers=headers).status_code == 204
    assert api_client.get("/auth/staff/profile", headers=headers).json()["max_user_id"] is None
