from pathlib import Path

import pytest

from maxsmartcity.ml.data.gold.v2 import GoldV2MigrationConfig, GoldV2Migrator


def _migrator() -> GoldV2Migrator:
    config = GoldV2MigrationConfig.load(Path("ml/configs/gold-v2-migration.json"))
    return GoldV2Migrator(config)


def _record(category_ids: list[str], danger_signals: list[str]) -> dict[str, object]:
    return {
        "example_id": "GOLD-1",
        "scenario_spec_id": "SCN-1",
        "text": "У дома оборван провод.",
        "subcategory_ids": ["exposed_wire"],
        "category_ids": category_ids,
        "danger_signals": danger_signals,
        "ambiguity": False,
        "source": "SYNTHETIC_TEMPLATE",
    }


def test_migrates_secondary_emergency_and_danger_alias() -> None:
    migrated = _migrator().migrate(_record(["electricity", "emergency"], ["EXPOSED_WIRE"]))
    assert migrated["primary_category"] == "electricity"
    assert migrated["routing_outcome"] == "ACCEPT"
    assert migrated["danger_signals"] == ["EXPOSED_WIRE"]
    assert migrated["review_status"] == "CANDIDATE"


def test_clarification_has_no_primary_category() -> None:
    migrated = _migrator().migrate(_record(["water", "needs_clarification"], []))
    assert migrated["primary_category"] is None
    assert migrated["routing_outcome"] == "NEEDS_CLARIFICATION"


def test_rejects_ambiguous_multiple_primary_categories() -> None:
    with pytest.raises(ValueError, match="cannot select one primary category"):
        _migrator().migrate(_record(["water", "electricity"], []))


def test_scenario_override_routes_multi_issue_report_to_clarification() -> None:
    record = _record(["water", "electricity"], [])
    record["scenario_spec_id"] = "CURATED-same-house-water-and-power"
    migrated = _migrator().migrate(record)
    assert migrated["routing_outcome"] == "NEEDS_CLARIFICATION"
    assert migrated["primary_category"] is None
