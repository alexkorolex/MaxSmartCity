import json
from pathlib import Path

from maxsmartcity.ml.data.matching import MatchingDatasetBuilder


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )


def test_matching_builder_creates_qrels_and_hard_negatives(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    _write(
        source / "reports.jsonl",
        [
            {
                "report_id": "REP-1",
                "scenario_id": "SCN-1",
                "text": "нет воды на улице Мира 1",
                "category_id": "water",
                "fias_guid": "FIAS-1",
                "timestamp": "2026-09-21T10:00:00+03:00",
            }
        ],
    )
    _write(
        source / "incidents.jsonl",
        [
            {
                "incident_id": "INC-1",
                "scenario_id": "SCN-1",
                "category_id": "water",
                "fias_guids": ["FIAS-1"],
                "started_at": "2026-09-21T09:00:00+03:00",
            },
            {
                "incident_id": "INC-2",
                "scenario_id": "SCN-2",
                "category_id": "water",
                "fias_guids": ["FIAS-2"],
                "started_at": "2026-09-21T09:30:00+03:00",
            },
        ],
    )
    _write(
        source / "houses.jsonl",
        [
            {
                "scenario_id": "SCN-1",
                "street": "улица Мира",
                "house_number": "1",
            },
            {
                "scenario_id": "SCN-2",
                "street": "улица Мира",
                "house_number": "2",
            },
        ],
    )
    _write(
        source / "decisions.jsonl",
        [
            {
                "decision_id": "DEC-1",
                "report_id": "REP-1",
                "target_incident_ids": ["INC-1"],
                "candidate_incident_ids": ["INC-1", "INC-2"],
            }
        ],
    )
    (source / "manifest.json").write_text(
        json.dumps({"dataset_version": "source-v1", "dataset_hash": "a" * 64}),
        encoding="utf-8",
    )

    manifest = MatchingDatasetBuilder(version="matching-v1", split_seed=7).build(source, output)

    pairs = [json.loads(line) for line in (output / "pairs.jsonl").read_text().splitlines()]
    assert [pair["label"] for pair in pairs] == ["MATCH", "NO_MATCH"]
    assert pairs[1]["negative_type"] == "SAME_CATEGORY_DIFFERENT_HOUSE"
    assert manifest["files"]["qrels.jsonl"]["records"] == 1
    query_split = json.loads((output / "queries.jsonl").read_text().splitlines()[0])["split"]
    assert query_split in {"train", "validation", "test"}
