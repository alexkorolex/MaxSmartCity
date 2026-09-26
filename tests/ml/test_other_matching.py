import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from src.ml.evaluation.other_matching import evaluate_other_matching


class FixedProvider:
    model_name = "fixed"

    def embed_queries(self, texts: Sequence[str]) -> np.ndarray:
        assert len(texts) == 2
        return np.asarray(((1.0, 0.0), (0.0, 1.0)), dtype=np.float32)

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        assert len(texts) == 2
        return np.asarray(((1.0, 0.0), (0.9, 0.1)), dtype=np.float32)


def test_metrics_cover_matches_and_create_new(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "candidate_sets.jsonl",
        [
            {
                "query_id": "Q1",
                "text": "match",
                "candidate_incident_ids": ["I1", "I2"],
                "target_incident_id": "I1",
                "split": "test",
            },
            {
                "query_id": "Q2",
                "text": "new",
                "candidate_incident_ids": ["I1", "I2"],
                "target_incident_id": None,
                "split": "test",
            },
        ],
    )
    _write_jsonl(
        tmp_path / "incidents.jsonl",
        [
            {"incident_id": "I1", "representative_texts": ["one"]},
            {"incident_id": "I2", "representative_texts": ["two"]},
        ],
    )
    (tmp_path / "manifest.json").write_text(
        json.dumps({"dataset_version": "test", "limitations": []}), encoding="utf-8"
    )
    result = evaluate_other_matching(tmp_path, FixedProvider())
    assert result["splits"]["test"]["recall_at_1"] == 1.0
    assert result["splits"]["test"]["create_new_query_count"] == 1


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
