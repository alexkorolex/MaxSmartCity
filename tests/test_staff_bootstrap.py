import pytest

from src.security import staff_bootstrap
from src.security.settings import SecuritySettings
from src.security.staff_bootstrap import StaffBootstrapClosedError, ensure_bootstrap_allowed
from tests.test_keycloak_client import settings  # noqa: F401

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _admins(exist: bool) -> object:
    async def fake(_settings: object, role: str) -> bool:
        assert role == "admin"
        return exist

    return fake


async def test_bootstrap_creates_only_the_first_admin(
    settings: SecuritySettings,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(staff_bootstrap, "realm_role_has_users", _admins(False))
    await ensure_bootstrap_allowed(settings, "admin")

    monkeypatch.setattr(staff_bootstrap, "realm_role_has_users", _admins(True))
    with pytest.raises(StaffBootstrapClosedError, match="already exists"):
        await ensure_bootstrap_allowed(settings, "admin")


async def test_bootstrap_cannot_create_other_roles(settings: SecuritySettings) -> None:  # noqa: F811
    with pytest.raises(StaffBootstrapClosedError, match="first administrator"):
        await ensure_bootstrap_allowed(settings, "housing_worker")
