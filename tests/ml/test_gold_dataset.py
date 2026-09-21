import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from maxsmartcity.ml.data.config import load_taxonomy
from maxsmartcity.ml.data.gold.models import GoldReportAnnotation
from maxsmartcity.ml.data.gold.validator import GoldDatasetValidator

VALIDATOR = GoldDatasetValidator(load_taxonomy(Path("ml/configs/taxonomy.v1.json")))


def test_seed_draft_is_semantically_valid_but_not_gold() -> None:
    path = Path("ml/data/gold/drafts/reports.seed.jsonl")
    records = VALIDATOR.load_and_validate(path)
    manifest = json.loads(Path("ml/data/gold/drafts/manifest.json").read_text(encoding="utf-8"))

    assert len(records) == 20
    assert all(record.review_status == "DRAFT" for record in records)
    assert all(record.reviewer is None for record in records)
    assert manifest["record_count"] == len(records)
    assert manifest["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_reviewed_record_requires_reviewer() -> None:
    record = GoldReportAnnotation(
        annotation_version="gold-report-v1",
        example_id="EXAMPLE",
        text="Нет воды",
        category_ids=("water",),
        subcategory_ids=(),
        entities=(),
        danger_signals=(),
        needs_clarification=False,
        ambiguity=False,
        source="HUMAN_AUTHORED",
        review_status="REVIEWED",
        annotator="annotator",
        reviewer=None,
    )

    with pytest.raises(ValueError, match="require reviewer"):
        VALIDATOR.validate((record,))


def test_reviewed_mvp_dataset_is_complete_unique_and_leakage_safe() -> None:
    root = Path("ml/data/gold/v1")
    reports = VALIDATOR.load_and_validate(root / "reports.jsonl")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))

    assert len(reports) == 362
    assert len({record.scenario_spec_id for record in reports}) == 181
    assert set(Counter(record.scenario_spec_id for record in reports).values()) == {2}
    assert len({" ".join(record.text.casefold().split()) for record in reports}) == 362
    assert Counter(record.source for record in reports) == {
        "SYNTHETIC_TEMPLATE": 181,
        "LLM_ASSISTED": 181,
    }
    assert all(record.review_status == "REVIEWED" for record in reports)
    assert manifest["status"] == "REVIEWED_MVP_PENDING_HUMAN_SIGNOFF"
    assert (
        manifest["files"]["reports.jsonl"]["sha256"]
        == hashlib.sha256((root / "reports.jsonl").read_bytes()).hexdigest()
    )

    split_scenarios = [
        {record.scenario_spec_id for record in VALIDATOR.load_and_validate(root / f"{split}.jsonl")}
        for split in ("train", "validation", "test")
    ]
    assert not split_scenarios[0] & split_scenarios[1]
    assert not split_scenarios[0] & split_scenarios[2]
    assert not split_scenarios[1] & split_scenarios[2]
    split_categories = [
        {
            category
            for record in VALIDATOR.load_and_validate(root / f"{split}.jsonl")
            for category in record.category_ids
        }
        for split in ("train", "validation", "test")
    ]
    assert all("non_incident" in categories for categories in split_categories)
    assert all("electricity" in categories for categories in split_categories)


def test_reviewed_mvp_contains_semantic_corrections() -> None:
    reports = VALIDATOR.load_and_validate(Path("ml/data/gold/v1/reports.jsonl"))
    by_scenario = {
        record.scenario_spec_id: [] for record in reports if record.scenario_spec_id is not None
    }
    for record in reports:
        if record.scenario_spec_id is not None:
            by_scenario[record.scenario_spec_id].append(record.text)

    assert any(
        "пользователь считает" in text.casefold()
        for text in by_scenario["CURATED-wrong-organization-mentioned"]
    )
    assert any(
        "повторно" in text.casefold() for text in by_scenario["CURATED-repeated-user-duplicate"]
    )
    assert any(
        "переполнен" in text.casefold()
        for text in by_scenario["EXT-SF311-RECENT-CASES-085489f19785"]
    )
    assert any(
        "вне установленного времени" in text.casefold()
        for text in by_scenario["EXT-SF311-RECENT-CASES-73bba6b69114"]
    )
