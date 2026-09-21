from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from maxsmartcity.ml.evaluation.classification import (
    evaluate_category_predictions,
    select_abstain_threshold,
)
from maxsmartcity.ml.inference.category import CategoryArtifact
from maxsmartcity.ml.training.config import CategoryTrainingConfig
from maxsmartcity.ml.training.dataset import assert_scenario_disjoint, load_split
from maxsmartcity.ml.training.trainer import CategoryTrainer


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _row(example_id: str, scenario_id: str, text: str, label: str) -> dict[str, object]:
    return {
        "example_id": example_id,
        "scenario_spec_id": scenario_id,
        "text": text,
        "category_ids": [label],
    }


def test_scenario_leakage_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "split.jsonl"
    _write_jsonl(path, [_row("a", "same", "нет воды", "water")])
    examples = load_split(path)
    with pytest.raises(ValueError, match="Scenario leakage"):
        assert_scenario_disjoint({"train": examples, "test": examples})


def test_v2_loader_uses_primary_category_and_skips_routing_records(tmp_path: Path) -> None:
    path = tmp_path / "split.jsonl"
    _write_jsonl(
        path,
        [
            {
                "record_id": "accepted",
                "scenario_id": "scenario-1",
                "text": "нет воды",
                "primary_category": "water",
                "routing_outcome": "ACCEPT",
            },
            {
                "record_id": "clarify",
                "scenario_id": "scenario-2",
                "text": "помогите",
                "primary_category": None,
                "routing_outcome": "NEEDS_CLARIFICATION",
            },
        ],
    )
    examples = load_split(path, "primary_category")
    assert len(examples) == 1
    assert examples[0].labels == ("water",)


def test_selective_threshold_meets_target_when_possible() -> None:
    result = select_abstain_threshold(
        np.array([0.95, 0.85, 0.6, 0.4]),
        np.array([1.0, 1.0, 0.0, 0.0]),
        precision_target=1.0,
        minimum_coverage=0.25,
    )
    assert result["target_met"] is True
    assert result["coverage"] == pytest.approx(0.5)
    assert result["threshold"] == pytest.approx(0.85)


def test_metrics_include_required_tz_outputs() -> None:
    metrics = evaluate_category_predictions(
        np.array([[1, 0], [0, 1]]),
        np.array([[0.9, 0.1], [0.2, 0.8]]),
        ["water", "waste"],
        label_threshold=0.5,
        abstain_threshold=0.85,
    )
    assert metrics["macro_f1"] == pytest.approx(1.0)
    assert metrics["ece"] >= 0.0
    assert metrics["brier_score"] >= 0.0
    assert metrics["per_class"]["water"]["confusion_matrix"] == [[1, 0], [0, 1]]


def test_empty_label_prediction_is_counted_as_abstain() -> None:
    metrics = evaluate_category_predictions(
        np.array([[1, 0]]),
        np.array([[0.4, 0.3]]),
        ["water", "waste"],
        label_threshold=0.5,
        abstain_threshold=0.2,
    )
    assert metrics["coverage"] == 0.0
    assert metrics["abstain_ratio"] == 1.0


def test_training_writes_loadable_artifact(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "data"
    dataset_dir.mkdir()
    rows_by_split = {
        "train": [
            _row("tr-w1", "tr-w1", "нет холодной воды", "water"),
            _row("tr-w2", "tr-w2", "из крана не течет вода", "water"),
            _row("tr-e1", "tr-e1", "в доме отключили свет", "electricity"),
            _row("tr-e2", "tr-e2", "нет электричества", "electricity"),
        ],
        "validation": [
            _row("va-w", "va-w", "пропала вода", "water"),
            _row("va-e", "va-e", "пропал свет", "electricity"),
        ],
        "test": [
            _row("te-w", "te-w", "вода не идет", "water"),
            _row("te-e", "te-e", "электричества нет", "electricity"),
        ],
    }
    for split, rows in rows_by_split.items():
        _write_jsonl(dataset_dir / f"{split}.jsonl", rows)
    (dataset_dir / "manifest.json").write_text(
        json.dumps({"dataset_version": "test-v1"}), encoding="utf-8"
    )
    taxonomy_path = tmp_path / "taxonomy.json"
    taxonomy_path.write_text(
        json.dumps(
            {
                "version": "taxonomy-test-v1",
                "categories": [{"id": "water"}, {"id": "electricity"}],
            }
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    config = CategoryTrainingConfig(
        experiment_name="test",
        model_version="test-v1",
        dataset_dir=dataset_dir,
        artifact_dir=tmp_path / "artifact",
        taxonomy_path=taxonomy_path,
        seed=7,
        word_ngram_range=(1, 2),
        char_ngram_range=(3, 4),
        word_max_features=100,
        char_max_features=100,
        min_df=1,
        max_iter=100,
        label_threshold=0.5,
        automation_precision_target=0.5,
        minimum_coverage=0.5,
    )
    result = CategoryTrainer(config, config_path).train()
    artifact = CategoryArtifact.load(result.artifact_dir)
    prediction = artifact.predict("нет воды")
    assert prediction.model_version == "test-v1"
    assert prediction.labels
    assert (result.artifact_dir / "manifest.json").exists()
    assert (result.artifact_dir / "metrics.json").exists()
