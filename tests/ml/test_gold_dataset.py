import hashlib
import json
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
