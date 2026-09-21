import httpx
import pytest

from src.security.keycloak import KeycloakLoginError, login_staff_with_password
from src.security.keycloak_admin import KeycloakAdminError, create_staff_user
from src.security.settings import SecuritySettings

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> SecuritySettings:
    monkeypatch.setenv("KEYCLOAK_ISSUER", "http://localhost:8080/realms/maxsmartcity")
    monkeypatch.setenv(
        "KEYCLOAK_JWKS_URI", "http://keycloak:8080/realms/maxsmartcity/protocol/openid-connect/certs"
    )
    monkeypatch.setenv("KEYCLOAK_INTERNAL_URL", "http://keycloak:8080")
    monkeypatch.setenv("KEYCLOAK_REALM", "maxsmartcity")
    monkeypatch.setenv("KEYCLOAK_AUDIENCE", "maxsmartcity-backend")
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "maxsmartcity-backend")
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("KEYCLOAK_ADMIN", "admin")
    monkeypatch.setenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
    monkeypatch.setenv("RESIDENT_JWT_SECRET", "test-resident-secret-at-least-32-bytes-long")
    monkeypatch.setenv("BOT_SHARED_SECRET", "test-bot-secret")
    return SecuritySettings.from_environment()


async def test_login_staff_with_password_success(
    settings: SecuritySettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_post(self: httpx.AsyncClient, url: str, **_kwargs: object) -> httpx.Response:
        assert url == settings.keycloak_token_url
        return httpx.Response(200, json={"access_token": "abc", "refresh_token": "def", "expires_in": 300})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    tokens = await login_staff_with_password(settings, username="admin_test", password="admin_test")

    assert tokens["access_token"] == "abc"


async def test_login_staff_with_password_rejects_bad_credentials(
    settings: SecuritySettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_post(self: httpx.AsyncClient, url: str, **_kwargs: object) -> httpx.Response:
        return httpx.Response(401, json={"error_description": "Invalid user credentials"})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(KeycloakLoginError):
        await login_staff_with_password(settings, username="admin_test", password="wrong")


async def test_create_staff_user_assigns_role_and_returns_subject(
    settings: SecuritySettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    async def fake_post(self: httpx.AsyncClient, url: str, **_kwargs: object) -> httpx.Response:
        calls.append(url)
        if url == settings.keycloak_master_token_url:
            return httpx.Response(200, json={"access_token": "admin-token"})
        if url == settings.keycloak_admin_users_url:
            return httpx.Response(
                201, headers={"Location": f"{settings.keycloak_admin_users_url}/new-subject-id"}
            )
        if url == f"{settings.keycloak_admin_users_url}/new-subject-id/role-mappings/realm":
            return httpx.Response(204)
        raise AssertionError(f"unexpected POST {url}")

    async def fake_get(self: httpx.AsyncClient, url: str, **_kwargs: object) -> httpx.Response:
        assert (
            url
            == f"{settings.keycloak_internal_url}/admin/realms/{settings.keycloak_realm}/roles/housing_worker"
        )
        return httpx.Response(200, json={"id": "role-id", "name": "housing_worker"})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    subject = await create_staff_user(
        settings,
        login="new_worker",
        password="Str0ngPass!23",
        email="worker@example.com",
        display_name="Petr Ivanov",
        role="housing_worker",
    )

    assert subject == "new-subject-id"
    assert settings.keycloak_admin_users_url in calls


async def test_create_staff_user_raises_on_conflict(
    settings: SecuritySettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_post(self: httpx.AsyncClient, url: str, **_kwargs: object) -> httpx.Response:
        if url == settings.keycloak_master_token_url:
            return httpx.Response(200, json={"access_token": "admin-token"})
        return httpx.Response(409)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(KeycloakAdminError) as excinfo:
        await create_staff_user(
            settings,
            login="already_exists",
            password="Str0ngPass!23",
            email=None,
            display_name="Someone",
            role="admin",
        )
    assert excinfo.value.conflict is True
