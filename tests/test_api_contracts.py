from typing import Any
from uuid import uuid4

import pytest
from litestar import Litestar, post
from litestar.dto import DTOData
from litestar.testing import TestClient

from src.domains.incidents.models import Incident
from src.domains.incidents.schemas import IncidentCreateDTO
from src.main import create_app


@pytest.fixture
def api_schema() -> dict[str, Any]:
    app = create_app(
        "postgresql+asyncpg://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
    )
    return app.openapi_schema.to_schema()


def test_crud_schemas_are_generated_from_domain_models(api_schema: dict[str, Any]) -> None:
    schemas = api_schema["components"]["schemas"]
    for path in ("/identity/organizations", "/geo/addresses", "/reports/categories"):
        create = api_schema["paths"][path]["post"]
        update = api_schema["paths"][f"{path}/{{item_id}}"]["patch"]
        create_ref = create["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        update_ref = update["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        response_ref = create["responses"]["201"]["content"]["application/json"]["schema"]["$ref"]
        properties = schemas[create_ref.rsplit("/", 1)[1]]["properties"]
        assert not {"id", "created_at", "updated_at", "_sentinel"}.intersection(properties)
        assert "id" in schemas[response_ref.rsplit("/", 1)[1]]["properties"]
        assert not schemas[update_ref.rsplit("/", 1)[1]].get("required")


def test_aggregate_routes_do_not_allow_unrestricted_mutations(api_schema: dict[str, Any]) -> None:
    for path in ("/incidents", "/reports", "/collaboration/work-items"):
        assert "get" in api_schema["paths"][path]
        assert "post" not in api_schema["paths"][path]
        assert "patch" not in api_schema["paths"][f"{path}/{{item_id}}"]
    assert "patch" not in api_schema["paths"]["/collaboration/assignments/{item_id}"]


def test_incident_core_exposes_commands_instead_of_generic_mutations(
    api_schema: dict[str, Any],
) -> None:
    assert "post" in api_schema["paths"]["/reports/intake"]
    assert "get" in api_schema["paths"]["/reports/mine"]
    assert "post" in api_schema["paths"]["/reports/{item_id}/grouping-decision"]
    assert "post" in api_schema["paths"]["/incidents/group-reports/{report_id}"]
    assert "post" in api_schema["paths"]["/incidents/{item_id}/status"]
    assert "get" in api_schema["paths"]["/incidents/{item_id}/card"]
    assert "post" in api_schema["paths"]["/incidents/{item_id}/resolution-feedback"]
    assert "post" in api_schema["paths"]["/collaboration/assignments"]
    assert "post" in api_schema["paths"]["/collaboration/assignments/{item_id}/status"]


@pytest.mark.parametrize("field", ["id", "version", "status", "created_at", "unknown_field"])
def test_incident_dto_rejects_server_managed_fields(field: str) -> None:
    @post("/", dto=IncidentCreateDTO, sync_to_thread=False)
    def accept_incident(data: DTOData[Incident]) -> dict[str, object]:
        return {"title": data.create_instance().title}

    with TestClient(Litestar(route_handlers=[accept_incident])) as client:
        response = client.post(
            "/", json={"title": "Water leak", "category_id": str(uuid4()), field: "invalid"}
        )
        assert response.status_code == 400


def test_spatial_columns_have_string_dto_contracts(api_schema: dict[str, Any]) -> None:
    request = api_schema["paths"]["/geo/addresses"]["post"]["requestBody"]
    reference = request["content"]["application/json"]["schema"]["$ref"]
    properties = api_schema["components"]["schemas"][reference.rsplit("/", 1)[1]]["properties"]
    assert {"type": "string"} in properties["point"]["oneOf"]
