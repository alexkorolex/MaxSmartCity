from datetime import UTC, datetime
from pathlib import Path

from maxsmartcity.ml.adapters.baselines import RuleBaselineDecisionModel, RuleIncidentRanker
from maxsmartcity.ml.data.config import load_rule_baseline
from maxsmartcity.ml.domain.requests import DecisionRequest, IncidentCandidate, ReportInput

NOW = datetime(2026, 9, 20, 10, tzinfo=UTC)


def make_model() -> RuleBaselineDecisionModel:
    config = load_rule_baseline(Path("ml/configs/rule-baseline.v1.json"))
    return RuleBaselineDecisionModel(RuleIncidentRanker(config))


def test_structured_facts_rank_same_location_without_parsing_text() -> None:
    request = DecisionRequest(
        request_id="REQ-1",
        report=ReportInput(
            "REP-1",
            "произвольный текст, который baseline не парсит",
            NOW,
            house_id="HOUSE-12",
            category_hint="water",
        ),
        incident_candidates=(
            IncidentCandidate("INC-12", NOW, "water", affected_house_ids=("HOUSE-12",)),
            IncidentCandidate("INC-21", NOW, "water", affected_house_ids=("HOUSE-21",)),
        ),
    )

    response = make_model().decide(request)

    assert response.incident_ranking.candidates[0].id == "INC-12"
    assert response.incident_ranking.abstain is True
    assert response.incident_ranking.model is not None
    assert response.incident_ranking.model.score_kind == "normalized_heuristic_not_probability"
    assert "SAME_HOUSE_ID" in response.incident_ranking.candidates[0].reason_codes
    assert response.requires_manual_review is True


def test_unimplemented_tasks_are_explicitly_abstained() -> None:
    request = DecisionRequest(
        request_id="REQ-2",
        report=ReportInput("REP-2", "нет данных", NOW),
    )

    response = make_model().decide(request)

    assert response.category is None
    assert response.features.values == {}
    assert response.organization_ranking.abstain_reason is not None
    assert response.action_ranking.abstain_reason is not None
