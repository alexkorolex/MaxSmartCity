import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from maxsmartcity.ml.service.runtime import parse_decision_request
from src.common.enums import Priority
from src.domains.incidents.enums import IncidentStatus
from src.domains.incidents.models import Incident
from src.domains.ml.client import MLDecisionClient
from src.domains.ml.mapping import build_decision_request
from src.domains.reports.enums import ReportSourceType, ReportStatus
from src.domains.reports.models import Report
from src.main import create_app


def test_backend_exposes_ml_gateway_routes() -> None:
    app = create_app(
        "postgresql+asyncpg://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
    )
    schema = app.openapi_schema.to_schema()

    assert "get" in schema["paths"]["/ml/health"]
    assert "post" in schema["paths"]["/ml/decide"]


def test_backend_entities_map_to_allowlisted_ml_snapshot() -> None:
    category_id = uuid4()
    house_id = uuid4()
    now = datetime(2026, 9, 21, 12, tzinfo=UTC)
    report = Report(
        id=uuid4(),
        created_at=now,
        source_type=ReportSourceType.MAX,
        text="Нет воды",
        status=ReportStatus.RECEIVED,
        category_id=category_id,
        urgency=Priority.NORMAL,
        house_id=house_id,
        received_at=now,
    )
    incident = Incident(
        id=uuid4(),
        created_at=now,
        title="Отключение воды",
        category_id=category_id,
        status=IncidentStatus.CONFIRMED,
        priority=Priority.NORMAL,
        first_report_at=now,
    )

    payload = build_decision_request(
        request_id="REQ-1",
        report=report,
        incidents=[incident],
        category_codes={category_id: "water"},
        incident_house_ids={incident.id: [house_id]},
    )

    assert payload["report"]["category_hint"] == "water"
    candidate = payload["candidate_incidents"][0]
    assert candidate["id"] == str(incident.id)
    assert candidate["affected_house_ids"] == [str(house_id)]
    assert candidate["active"] is True
    parsed = parse_decision_request(payload)
    assert parsed.report.house_id == str(house_id)
    assert parsed.incident_candidates[0].id == str(incident.id)


def test_ml_client_forwards_contract_without_mutating_it() -> None:
    payload = {"contract_version": "2.0.0-draft", "request_id": "REQ-2"}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/decide"
        assert request.content == b'{"contract_version":"2.0.0-draft","request_id":"REQ-2"}'
        return httpx.Response(200, json={"request_id": "REQ-2", "requires_manual_review": True})

    client = MLDecisionClient(
        "http://ml.test",
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(client.decide(payload))

    assert result.status_code == 200
    assert result.body["request_id"] == "REQ-2"
    assert payload == {"contract_version": "2.0.0-draft", "request_id": "REQ-2"}


def test_ml_client_returns_retryable_error_when_service_is_down() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    client = MLDecisionClient(
        "http://ml.test",
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(client.decide({"request_id": "REQ-3"}))

    assert result.status_code == 503
    assert result.body["code"] == "MODEL_UNAVAILABLE"
    assert result.body["retryable"] is True
