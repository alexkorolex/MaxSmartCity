"""Build leakage-safe retrieval qrels and pairwise reranking examples."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from maxsmartcity.ml.data.splits import split_by_scenario


@dataclass(frozen=True, slots=True)
class ScenarioMarker:
    scenario_id: str


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MatchingDatasetBuilder:
    def __init__(self, *, version: str, split_seed: int) -> None:
        self._version = version
        self._split_seed = split_seed

    def build(self, source_dir: Path, output_dir: Path) -> dict[str, Any]:
        reports = _read_jsonl(source_dir / "reports.jsonl")
        incidents = _read_jsonl(source_dir / "incidents.jsonl")
        decisions = _read_jsonl(source_dir / "decisions.jsonl")
        houses = _read_jsonl(source_dir / "houses.jsonl")
        source_manifest = json.loads((source_dir / "manifest.json").read_text(encoding="utf-8"))

        incident_by_id = {str(item["incident_id"]): item for item in incidents}
        report_by_id = {str(item["report_id"]): item for item in reports}
        addresses_by_scenario: dict[str, list[str]] = {}
        for house in houses:
            addresses_by_scenario.setdefault(str(house["scenario_id"]), []).append(
                f"{house['street']}, дом {house['house_number']}"
            )

        scenario_ids = sorted({str(item["scenario_id"]) for item in reports})
        split = split_by_scenario(
            (ScenarioMarker(scenario_id) for scenario_id in scenario_ids), seed=self._split_seed
        )
        split_by_id = {
            marker.scenario_id: name
            for name, markers in (
                ("train", split.train),
                ("validation", split.validation),
                ("test", split.test),
            )
            for marker in markers
        }

        corpus = [
            {
                "incident_id": str(incident["incident_id"]),
                "scenario_id": str(incident["scenario_id"]),
                "category_id": str(incident["category_id"]),
                "affected_fias_guids": incident["fias_guids"],
                "started_at": str(incident["started_at"]),
                "text": self._incident_text(incident, addresses_by_scenario),
            }
            for incident in incidents
        ]
        queries: list[dict[str, Any]] = []
        qrels: list[dict[str, Any]] = []
        pairs: list[dict[str, Any]] = []

        for decision in decisions:
            report_id = str(decision["report_id"])
            report = report_by_id[report_id]
            scenario_id = str(report["scenario_id"])
            split_name = split_by_id[scenario_id]
            target_ids = {str(item) for item in decision["target_incident_ids"]}
            candidate_ids = [str(item) for item in decision["candidate_incident_ids"]]
            unknown = (target_ids | set(candidate_ids)) - set(incident_by_id)
            if unknown:
                raise ValueError(f"Unknown incident IDs in {decision['decision_id']}: {sorted(unknown)}")
            queries.append(
                {
                    "query_id": report_id,
                    "scenario_id": scenario_id,
                    "split": split_name,
                    "text": str(report["text"]),
                    "category_id": str(report["category_id"]),
                    "fias_guid": report.get("fias_guid"),
                    "timestamp": str(report["timestamp"]),
                    "has_target": bool(target_ids),
                }
            )
            qrels.extend(
                {
                    "query_id": report_id,
                    "incident_id": target_id,
                    "relevance": 1,
                    "split": split_name,
                }
                for target_id in sorted(target_ids)
            )
            for candidate_id in candidate_ids:
                incident = incident_by_id[candidate_id]
                is_match = candidate_id in target_ids
                pairs.append(
                    {
                        "pair_id": f"{report_id}:{candidate_id}",
                        "scenario_id": scenario_id,
                        "split": split_name,
                        "report_id": report_id,
                        "report_text": str(report["text"]),
                        "candidate_incident_id": candidate_id,
                        "candidate_text": self._incident_text(incident, addresses_by_scenario),
                        "label": "MATCH" if is_match else "NO_MATCH",
                        "negative_type": None if is_match else self._negative_type(report, incident),
                    }
                )

        output_dir.mkdir(parents=True, exist_ok=True)
        outputs = {
            "corpus.jsonl": corpus,
            "queries.jsonl": queries,
            "qrels.jsonl": qrels,
            "pairs.jsonl": pairs,
        }
        files: dict[str, dict[str, Any]] = {}
        for filename, rows in outputs.items():
            path = output_dir / filename
            path.write_text(
                "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
                encoding="utf-8",
                newline="\n",
            )
            files[filename] = {"records": len(rows), "sha256": _hash_file(path)}

        manifest = {
            "dataset_version": self._version,
            "source_dataset_version": source_manifest["dataset_version"],
            "source_dataset_hash": source_manifest["dataset_hash"],
            "split_seed": self._split_seed,
            "files": files,
            "split_counts": {
                name: sum(query["split"] == name for query in queries)
                for name in ("train", "validation", "test")
            },
            "limitations": [
                "Synthetic benchmark; not a replacement for frozen human-reviewed pairs.",
                "Candidates are generated from a small closed synthetic incident universe.",
                "Query scenarios are split safely, but the candidate corpus is shared across splits.",
                "Backend/ingestion canonical snapshots must replace demo IDs before integration.",
            ],
        }
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return manifest

    @staticmethod
    def _incident_text(incident: dict[str, Any], addresses_by_scenario: dict[str, list[str]]) -> str:
        addresses = addresses_by_scenario.get(str(incident["scenario_id"]), [])
        rendered_addresses = "; ".join(addresses) if addresses else "адрес не указан"
        return (
            f"Категория: {incident['category_id']}. "
            f"Адреса: {rendered_addresses}. Начало: {incident['started_at']}."
        )

    @staticmethod
    def _negative_type(report: dict[str, Any], incident: dict[str, Any]) -> str:
        same_category = report["category_id"] == incident["category_id"]
        same_house = report.get("fias_guid") in set(incident.get("fias_guids", []))
        if same_category and not same_house:
            return "SAME_CATEGORY_DIFFERENT_HOUSE"
        if same_house and not same_category:
            return "SAME_HOUSE_DIFFERENT_CATEGORY"
        return "OTHER_INCIDENT"
