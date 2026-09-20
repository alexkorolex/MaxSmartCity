from dataclasses import replace
from pathlib import Path

import pytest

from maxsmartcity.ml.data.splits import DatasetSplit, assert_no_scenario_leakage, split_by_scenario
from maxsmartcity.ml.data.synthetic.config import load_synthetic_config
from maxsmartcity.ml.data.synthetic.generator import SyntheticWorldGenerator
from maxsmartcity.ml.data.synthetic.writer import SyntheticDatasetWriter

CONFIG = load_synthetic_config(Path("ml/configs/synthetic.v2.json"))
GOLDEN_TEST_DATASET_HASH = "9ec86eee5c1bc617c714bce5556dd7f297bcb6e6a74cbc03bd1c984a7412c036"


def test_same_seed_produces_identical_world() -> None:
    generator = SyntheticWorldGenerator(CONFIG, master_seed=42)
    first = generator.generate_standard(scenario_count=30, reports_per_scenario=4)
    second = generator.generate_standard(scenario_count=30, reports_per_scenario=4)

    assert first == second


def test_adding_reports_does_not_change_existing_report_seeds_or_text() -> None:
    generator = SyntheticWorldGenerator(CONFIG, master_seed=42)
    smaller = generator.generate_standard(scenario_count=3, reports_per_scenario=2)
    larger = generator.generate_standard(scenario_count=3, reports_per_scenario=3)
    larger_by_id = {report.report_id: report for report in larger.reports}

    assert all(larger_by_id[report.report_id] == report for report in smaller.reports)


def test_decisions_reference_real_hard_negative_incidents() -> None:
    bundle = SyntheticWorldGenerator(CONFIG, master_seed=42).generate_standard(
        scenario_count=8, reports_per_scenario=2
    )
    incident_ids = {incident.incident_id for incident in bundle.incidents}

    assert all(
        set(decision.candidate_incident_ids) <= incident_ids for decision in bundle.decisions
    )
    assert all(len(decision.candidate_incident_ids) == 2 for decision in bundle.decisions)


def test_counterfactuals_change_text_and_only_target_another_house() -> None:
    bundle = SyntheticWorldGenerator(CONFIG, master_seed=42).generate_standard(
        scenario_count=8, reports_per_scenario=2
    )
    reports = {report.report_id: report for report in bundle.reports}

    assert bundle.counterfactuals
    assert all(item.text != reports[item.source_report_id].text for item in bundle.counterfactuals)
    assert all(item.mutated_field == "house" for item in bundle.counterfactuals)


def test_every_report_references_an_existing_scenario() -> None:
    bundle = SyntheticWorldGenerator(CONFIG, master_seed=42).generate_standard(
        scenario_count=8, reports_per_scenario=2, noise_reports=5
    )
    scenario_ids = {scenario.scenario_id for scenario in bundle.scenarios}

    assert all(report.scenario_id in scenario_ids for report in bundle.reports)


def test_split_has_no_scenario_leakage() -> None:
    bundle = SyntheticWorldGenerator(CONFIG, master_seed=42).generate_standard(
        scenario_count=100, reports_per_scenario=3
    )
    split = split_by_scenario(bundle.reports, seed=42)

    assert_no_scenario_leakage(split)
    assert split.train and split.validation and split.test


def test_leakage_validator_rejects_overlap() -> None:
    report = (
        SyntheticWorldGenerator(CONFIG, master_seed=42)
        .generate_standard(scenario_count=2, reports_per_scenario=1)
        .reports[0]
    )
    leaked = DatasetSplit(train=(report,), validation=(replace(report),), test=())

    with pytest.raises(ValueError, match="scenario leakage"):
        assert_no_scenario_leakage(leaked)


def test_writer_creates_versioned_manifest(tmp_path: Path) -> None:
    bundle = SyntheticWorldGenerator(CONFIG, master_seed=42).generate_standard(
        scenario_count=4, reports_per_scenario=2, noise_reports=1
    )

    manifest = SyntheticDatasetWriter().write(
        bundle,
        tmp_path,
        config=CONFIG,
        master_seed=42,
        dataset_kind="test",
    )

    assert manifest["config_hash"]
    assert manifest["counts"]["reports"] == 9
    assert manifest["dataset_hash"] == GOLDEN_TEST_DATASET_HASH


def test_mass_outage_has_one_incident_and_requested_report_count() -> None:
    bundle = SyntheticWorldGenerator(CONFIG, master_seed=42).generate_mass_outage(
        report_count=1_000
    )

    assert len(bundle.incidents) == 1
    assert len(bundle.houses) == 100
    assert len(bundle.reports) == 1_000
