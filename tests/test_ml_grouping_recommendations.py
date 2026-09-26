from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.incidents.models import Incident, IncidentGroupingDecision
from src.domains.ml.client import MLDecisionClient
from src.domains.ml.report_grouping import (
    ReportGroupingRecommendationService,
    _exact_candidate_ids,
    _ranked_scores,
)
from src.domains.reports.models import Report


def test_semantic_recommendations_are_bounded_filtered_and_sorted() -> None:
    allowed = [uuid4() for _ in range(5)]
    foreign = uuid4()
    body = {
        "candidates": [
            {"incident_id": str(allowed[0]), "score": 0.89},
            {"incident_id": str(allowed[1]), "score": 0.97},
            {"incident_id": str(foreign), "score": 0.99},
            {"incident_id": str(allowed[2]), "score": 0.87},
            {"incident_id": str(allowed[3]), "score": 0.91},
            {"incident_id": str(allowed[4]), "score": 0.90},
            {"incident_id": str(allowed[1]), "score": 0.96},
        ]
    }

    result = _ranked_scores(body, allowed_ids=set(allowed))

    assert result == [
        (allowed[1], 0.97),
        (allowed[3], 0.91),
        (allowed[4], 0.90),
    ]


def test_semantic_recommendations_fail_closed_on_invalid_payload() -> None:
    allowed = uuid4()
    body = {
        "candidates": [
            {"incident_id": "not-a-uuid", "score": 0.99},
            {"incident_id": str(allowed), "score": "not-a-score"},
            None,
        ]
    }

    assert _ranked_scores(body, allowed_ids={allowed}) == []
    assert _ranked_scores({"candidates": {}}, allowed_ids={UUID(int=0)}) == []


def test_exact_candidate_matching_is_case_and_whitespace_insensitive() -> None:
    incident_id = uuid4()
    incident = Incident(id=incident_id, title="Другая проблема")
    incident.description = "В подъезде  появился неприятный запах"

    result = _exact_candidate_ids(
        "  В ПОДЪЕЗДЕ появился неприятный запах ",
        [incident_id],
        {incident_id: incident},
        {incident_id: []},
    )

    assert result == [incident_id]


def test_exact_candidate_matching_checks_linked_report_texts_and_is_bounded() -> None:
    incident_ids = [uuid4() for _ in range(4)]
    incidents = {}
    for incident_id in incident_ids:
        incident = Incident(id=incident_id, title="Другая проблема")
        incident.description = "другое описание"
        incidents[incident_id] = incident
    texts = {incident_id: ["Одинаковая заявка"] for incident_id in incident_ids}

    result = _exact_candidate_ids("одинаковая заявка", incident_ids, incidents, texts)

    assert result == incident_ids[:3]


@pytest.mark.anyio
async def test_backend_exact_match_does_not_depend_on_ml_service() -> None:
    incident_id = uuid4()
    category_id = uuid4()
    repeated = "В подъезде появился резкий неприятный запах"
    incident = Incident(
        id=incident_id,
        title="Другая проблема",
        description=repeated,
        category_id=category_id,
        last_report_at=datetime.now(UTC),
    )
    report = Report(id=uuid4(), category_id=category_id, text=repeated)
    decision = IncidentGroupingDecision(
        id=uuid4(),
        report_id=report.id,
        candidate_incident_ids=[str(incident_id)],
    )

    session_mock = AsyncMock()
    scalar_result = MagicMock()
    scalar_result.all.return_value = [incident]
    session_mock.scalars.return_value = scalar_result
    session_mock.scalar.return_value = "other"
    texts_result = MagicMock()
    texts_result.all.return_value = [(incident_id, repeated)]
    counts_result = MagicMock()
    counts_result.tuples.return_value.all.return_value = [(incident_id, 3)]
    details_result = MagicMock()
    details_result.all.return_value = [
        SimpleNamespace(
            id=incident_id,
            first_report_at=incident.last_report_at,
            last_report_at=incident.last_report_at,
            created_at=incident.last_report_at,
            category_name="Другая проблема",
        )
    ]
    session_mock.execute.side_effect = [texts_result, counts_result, details_result]
    client_mock = AsyncMock()

    result = await ReportGroupingRecommendationService(
        cast(AsyncSession, session_mock),
        cast(MLDecisionClient, client_mock),
    ).recommend(report, decision)

    assert [item.incident_id for item in result.candidates] == [incident_id]
    assert result.candidates[0].score == 1.0
    assert result.scorer_version == "normalized-exact-text-v1"
    assert result.candidates[0].headline == "В подъезде появился резкий неприятный запах"
    assert (result.candidates[0].category_name, result.candidates[0].reports_count) == ("Другая проблема", 3)
    client_mock.recommend_grouping.assert_not_awaited()
