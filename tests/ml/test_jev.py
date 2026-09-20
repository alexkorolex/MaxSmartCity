from datetime import UTC, datetime

import pytest

from maxsmartcity.ml.adapters.models.jev import (
    UntrainedJevIncidentRanker,
    build_incident_nli_examples,
)
from maxsmartcity.ml.domain.requests import DecisionRequest, IncidentCandidate, ReportInput
from maxsmartcity.ml.ports.models import ComponentUnavailableError


def make_request() -> DecisionRequest:
    timestamp = datetime(2026, 9, 20, tzinfo=UTC)
    return DecisionRequest(
        request_id="REQ-1",
        report=ReportInput("REP-1", "нет воды", timestamp, "FIAS-1"),
        incident_candidates=(
            IncidentCandidate("INC-1", timestamp, "water", ("FIAS-1",)),
            IncidentCandidate("INC-2", timestamp, "water", ("FIAS-2",)),
        ),
    )


def test_decision_snapshot_converts_to_nli_pairs() -> None:
    examples = build_incident_nli_examples(
        make_request(),
        target_incident_ids=frozenset({"INC-1"}),
        neutral_incident_ids=frozenset({"INC-2"}),
    )

    assert [example.label for example in examples] == ["ENTAILMENT", "NEUTRAL"]
    assert {example.candidate_id for example in examples} == {"INC-1", "INC-2"}


def test_unknown_nli_target_is_rejected() -> None:
    with pytest.raises(ValueError, match="absent from allowed candidates"):
        build_incident_nli_examples(
            make_request(),
            target_incident_ids=frozenset({"INC-INVENTED"}),
        )


def test_untrained_jev_ranker_is_an_explicit_stub() -> None:
    with pytest.raises(ComponentUnavailableError, match="no trained"):
        UntrainedJevIncidentRanker().rank(make_request())
