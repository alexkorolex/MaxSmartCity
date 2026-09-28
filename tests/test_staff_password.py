from collections.abc import Awaitable, Callable
from typing import Any, cast

import httpx
import pytest

from src.security import staff_password
from src.security.keycloak import (
    KeycloakLoginError,
    KeycloakPasswordChangeRequired,
    login_staff_with_password,
)
from src.security.keycloak_admin import create_staff_user
from src.security.settings import SecuritySettings
from src.security.staff_password import (
    InitialPasswordError,
    PasswordChangeNotRequiredError,
    change_initial_password,
)
from tests.test_keycloak_client import settings  # noqa: F401

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_login_reports_a_temporary_password_as_a_required_change(
    settings: SecuritySettings,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_post(self: httpx.AsyncClient, url: str, **_kwargs: object) -> httpx.Response:
        return httpx.Response(
            400, json={"error": "invalid_grant", "error_description": "Account is not fully set up"}
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(KeycloakPasswordChangeRequired):
        await login_staff_with_password(settings, username="new", password="temporary-1")


async def test_new_staff_accounts_get_a_temporary_password(
    settings: SecuritySettings,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: dict[str, Any] = {}

    async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
        if url == settings.keycloak_admin_users_url:
            created.update(cast(dict[str, Any], kwargs["json"]))
            return httpx.Response(201, headers={"Location": f"{url}/subject-1"})
        if url.endswith("/role-mappings/realm"):
            return httpx.Response(204)
        return httpx.Response(200, json={"access_token": "admin-token"})

    async def fake_get(self: httpx.AsyncClient, url: str, **_kwargs: object) -> httpx.Response:
        return httpx.Response(200, json={"id": "role-id", "name": "housing_worker"})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    await create_staff_user(
        settings, login="new", password="temporary-1", email=None, display_name="Иван", role="housing_worker"
    )

    assert created["credentials"] == [{"type": "password", "value": "temporary-1", "temporary": True}]
    assert created["requiredActions"] == ["UPDATE_PASSWORD"]


def _fake_login(passwords: dict[str, str | Exception]) -> Callable[..., Awaitable[dict[str, Any]]]:
    async def fake_login(_settings: object, *, username: str, password: str) -> dict[str, Any]:
        outcome = passwords.get(password, KeycloakLoginError("Invalid user credentials"))
        if isinstance(outcome, Exception):
            raise outcome
        return {"access_token": outcome}

    return fake_login


async def test_initial_password_is_changed_only_after_the_temporary_one_is_proven(
    settings: SecuritySettings,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed: list[tuple[str, str]] = []

    async def fake_complete(_settings: object, *, username: str, password: str) -> None:
        completed.append((username, password))

    monkeypatch.setattr(
        staff_password,
        "login_staff_with_password",
        _fake_login({"temporary-1": KeycloakPasswordChangeRequired("x"), "permanent-9": "token"}),
    )
    monkeypatch.setattr(staff_password, "complete_initial_password", fake_complete)

    tokens = await change_initial_password(
        settings, username="new", password="temporary-1", new_password="permanent-9"
    )
    assert tokens == {"access_token": "token"}
    assert completed == [("new", "permanent-9")]

    with pytest.raises(KeycloakLoginError):
        await change_initial_password(
            settings, username="new", password="wrong-guess", new_password="other-99"
        )
    assert completed == [("new", "permanent-9")]


async def test_initial_password_rejects_accounts_without_a_temporary_password(
    settings: SecuritySettings,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(staff_password, "login_staff_with_password", _fake_login({"permanent-1": "token"}))

    with pytest.raises(PasswordChangeNotRequiredError):
        await change_initial_password(
            settings, username="old", password="permanent-1", new_password="another-2"
        )


@pytest.mark.parametrize(
    ("password", "new_password"), [("temporary-1", "short"), ("temporary-1", "temporary-1")]
)
async def test_initial_password_validates_the_new_password(
    settings: SecuritySettings,  # noqa: F811
    password: str,
    new_password: str,
) -> None:
    with pytest.raises(InitialPasswordError):
        await change_initial_password(settings, username="new", password=password, new_password=new_password)
