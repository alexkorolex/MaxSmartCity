from uuid import uuid4

import pytest
from litestar.testing import TestClient


@pytest.mark.parametrize(
    ("path", "payload", "field"),
    [
        ("/identity/organizations", {"name": "Water utility", "type": "WATER_UTILITY"}, "name"),
        ("/reports/categories", {"name": "Water outage"}, "name"),
        ("/geo/addresses", {"formatted": "Test address", "point": "POINT(37.62 55.75)"}, "formatted"),
    ],
)
def test_catalog_crud(api_client: TestClient, path: str, payload: dict[str, str], field: str) -> None:
    data = dict(payload)
    if path != "/geo/addresses":
        data["code"] = uuid4().hex
    created = api_client.post(path, json=data)
    assert created.status_code == 201, created.text
    item_path = f"{path}/{created.json()['id']}"
    try:
        assert api_client.get(item_path).json()[field] == data[field]
        assert api_client.get(path, params={"limit": 1}).status_code == 200
        if "point" in data:
            assert created.json()["point"] == data["point"]
        updated = api_client.patch(item_path, json={field: "Updated"})
        assert updated.status_code == 200, updated.text
        assert api_client.get(item_path).json()[field] == "Updated"
    finally:
        assert api_client.delete(item_path).status_code == 204
    assert api_client.get(item_path).status_code == 404


def test_duplicate_organization_code_conflicts(api_client: TestClient) -> None:
    data = {"code": uuid4().hex, "name": "Utility", "type": "POWER_GRID"}
    created = api_client.post("/identity/organizations", json=data)
    assert created.status_code == 201
    try:
        assert api_client.post("/identity/organizations", json=data).status_code == 409
    finally:
        api_client.delete(f"/identity/organizations/{created.json()['id']}")


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_catalog_pagination_is_bounded(api_client: TestClient, params: dict[str, int]) -> None:
    assert api_client.get("/identity/organizations", params=params).status_code == 400
