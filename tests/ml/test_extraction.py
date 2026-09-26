from datetime import UTC, datetime
from pathlib import Path

from src.ml.adapters.extraction import RuleFeatureExtractor
from src.ml.domain.requests import DecisionRequest, ReportInput


def _extract(text: str) -> dict[str, object]:
    extractor = RuleFeatureExtractor.from_path(Path("ml/configs/extraction-rules.v1.json"))
    request = DecisionRequest(
        request_id="REQ-EXTRACT",
        report=ReportInput("REP-EXTRACT", text, datetime(2026, 9, 21, tzinfo=UTC)),
    )
    return extractor.extract(request).values


def test_extracts_backend_aligned_observable_features() -> None:
    values = _extract(
        "На Советской улице, дом 12, подъезд 3, этаж 7 уже два часа искрит щиток "
        "и проблема до сих пор продолжается во всём доме."
    )
    assert values["raw_address"] == "Советской улице, дом 12"
    assert values["entrance"] == 3
    assert values["floor"] == 7
    assert values["duration"] == {"text": "два часа", "seconds": 7200}
    assert values["scale_hint"] == "HOUSE"
    assert values["danger_signals"] == ("SPARKING",)
    assert values["problem_continues"] is True


def test_resolved_problem_wins_over_recurrence_words() -> None:
    values = _extract("Свет снова отключали, но уже устранили и электричество восстановили.")
    assert values["problem_continues"] is False


def test_extractor_does_not_invent_canonical_address_id() -> None:
    values = _extract("У нас в подъезде пахнет газом.")
    assert values["danger_signals"] == ("GAS_SMELL",)
    assert "address_id" not in values
    assert "house_id" not in values
