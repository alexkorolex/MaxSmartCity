from uuid import uuid4

import pytest
from litestar.testing import TestClient

from tests.integration.test_resident_api import _staff_token, rsa_keypair, security_env  # noqa: F401


@pytest.fixture
def admin(rsa_keypair: tuple[str, str]) -> dict[str, str]:  # noqa: F811
    """Organization mutations are admin-only; the other catalogs simply ignore the header."""
    token = _staff_token(rsa_keypair[0], subject=str(uuid4()), roles=["admin"])
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    ("path", "payload", "field"),
    [
        ("/identity/organizations", {"name": "Water utility", "type": "WATER_UTILITY"}, "name"),
        ("/reports/categories", {"name": "Water outage"}, "name"),
        ("/geo/addresses", {"formatted": "Test address", "point": "POINT(37.62 55.75)"}, "formatted"),
    ],
)
def test_catalog_crud(
    api_client: TestClient, admin: dict[str, str], path: str, payload: dict[str, str], field: str
) -> None:
    data = dict(payload)
    if path != "/geo/addresses":
        data["code"] = uuid4().hex
    created = api_client.post(path, json=data, headers=admin)
    assert created.status_code == 201, created.text
    item_path = f"{path}/{created.json()['id']}"
    try:
        assert api_client.get(item_path, headers=admin).json()[field] == data[field]
        assert api_client.get(path, params={"limit": 1}, headers=admin).status_code == 200
        if "point" in data:
            assert created.json()["point"] == data["point"]
        updated = api_client.patch(item_path, json={field: "Updated"}, headers=admin)
        assert updated.status_code == 200, updated.text
        assert api_client.get(item_path, headers=admin).json()[field] == "Updated"
    finally:
        assert api_client.delete(item_path, headers=admin).status_code == 204
    assert api_client.get(item_path, headers=admin).status_code == 404


def test_duplicate_organization_code_conflicts(api_client: TestClient, admin: dict[str, str]) -> None:
    data = {"code": uuid4().hex, "name": "Utility", "type": "POWER_GRID"}
    created = api_client.post("/identity/organizations", json=data, headers=admin)
    assert created.status_code == 201
    try:
        assert api_client.post("/identity/organizations", json=data, headers=admin).status_code == 409
    finally:
        api_client.delete(f"/identity/organizations/{created.json()['id']}", headers=admin)


def test_organization_catalog_is_staff_only_and_mutations_are_admin_only(
    api_client: TestClient,
    rsa_keypair: tuple[str, str],  # noqa: F811
) -> None:
    worker_token = _staff_token(rsa_keypair[0], subject=str(uuid4()), roles=["housing_worker"])
    worker = {"Authorization": f"Bearer {worker_token}"}
    data = {"code": uuid4().hex, "name": "Utility", "type": "POWER_GRID"}
    assert api_client.get("/identity/organizations").status_code == 401
    assert api_client.post("/identity/organizations", json=data).status_code == 401
    assert api_client.post("/identity/organizations", json=data, headers=worker).status_code == 403


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_catalog_pagination_is_bounded(
    api_client: TestClient, admin: dict[str, str], params: dict[str, int]
) -> None:
    assert api_client.get("/identity/organizations", params=params, headers=admin).status_code == 400
