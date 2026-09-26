"""Reproducible matching and HTTP stress benchmarks for the MVP decision layer."""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from src.ml.adapters.baselines import RuleIncidentRanker
from src.ml.data.config import load_rule_baseline
from src.ml.data.synthetic.config import load_synthetic_config
from src.ml.data.synthetic.generator import SyntheticWorldGenerator
from src.ml.domain.requests import DecisionRequest, IncidentCandidate, ReportInput
from src.ml.domain.results import CONTRACT_VERSION


def evaluate_rule_matching(dataset_dir: Path, rule_config_path: Path) -> dict[str, Any]:
    """Evaluate the rule ranker on the existing versioned matching dataset."""

    queries = _read_jsonl(dataset_dir / "queries.jsonl")
    pairs = _read_jsonl(dataset_dir / "pairs.jsonl")
    qrels = _read_jsonl(dataset_dir / "qrels.jsonl")
    corpus = {str(row["incident_id"]): row for row in _read_jsonl(dataset_dir / "corpus.jsonl")}
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))

    candidate_ids: dict[str, list[str]] = defaultdict(list)
    for pair in pairs:
        candidate_ids[str(pair["report_id"])].append(str(pair["candidate_incident_id"]))
    targets: dict[str, set[str]] = defaultdict(set)
    for qrel in qrels:
        if int(qrel["relevance"]) > 0:
            targets[str(qrel["query_id"])].add(str(qrel["incident_id"]))

    ranker = RuleIncidentRanker(load_rule_baseline(rule_config_path))
    rows: list[dict[str, Any]] = []
    for query in queries:
        query_id = str(query["query_id"])
        incidents = tuple(_incident_candidate(corpus[item]) for item in candidate_ids[query_id])
        request = DecisionRequest(
            request_id=f"BENCH-{query_id}",
            report=ReportInput(
                report_id=query_id,
                text=str(query["text"]),
                created_at=_timestamp(str(query["timestamp"])),
                fias_guid=_optional_string(query.get("fias_guid")),
                category_hint=str(query["category_id"]),
            ),
            incident_candidates=incidents,
        )
        result = ranker.rank(request)
        ordered_ids = [item.id for item in result.candidates]
        target_ids = targets[query_id]
        target_ranks = [ordered_ids.index(item) + 1 for item in target_ids if item in ordered_ids]
        rows.append(
            {
                "split": str(query["split"]),
                "candidate_count": len(ordered_ids),
                "has_target": bool(target_ids),
                "first_target_rank": min(target_ranks) if target_ranks else None,
                "abstain": result.abstain,
            }
        )

    return {
        "benchmark": "rule-incident-matching",
        "dataset_version": manifest["dataset_version"],
        "source_dataset_hash": manifest["source_dataset_hash"],
        "rule_version": ranker.config.version,
        "automation_enabled": ranker.config.automation_enabled,
        "splits": {
            split: _matching_metrics(
                rows if split == "all" else [row for row in rows if row["split"] == split]
            )
            for split in ("train", "validation", "test", "all")
        },
        "limitations": [
            "Synthetic benchmark; it does not replace human-reviewed incident pairs.",
            "Candidate retrieval is not evaluated because candidates are supplied by the fixture.",
            "No-target queries contain no candidates, so false-merge quality is not measurable here.",
            "Automation is disabled; scores are ranking heuristics rather than probabilities.",
        ],
    }


def run_http_stress_benchmark(
    *,
    base_url: str,
    synthetic_config_path: Path,
    report_count: int,
    batch_size: int,
    seed: int,
    timeout_seconds: float,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Generate a mass outage in memory and benchmark the running HTTP batch endpoint."""

    if report_count < 1:
        raise ValueError("report_count must be positive")
    if batch_size < 1 or batch_size > 1024:
        raise ValueError("batch_size must be between 1 and 1024")
    config = load_synthetic_config(synthetic_config_path)
    reports = (
        SyntheticWorldGenerator(config, master_seed=seed)
        .generate_mass_outage(report_count=report_count)
        .reports
    )
    expected_label = reports[0].category_id
    active_client = client or httpx.Client(base_url=base_url, timeout=timeout_seconds)
    owns_client = client is None
    latencies: list[float] = []
    errors = 0
    abstained = 0
    correct = 0
    accepted_correct = 0
    model_versions: set[str] = set()
    started = time.perf_counter()
    try:
        for batch_index, offset in enumerate(range(0, len(reports), batch_size)):
            batch = reports[offset : offset + batch_size]
            payload = {
                "contract_version": CONTRACT_VERSION,
                "batch_id": f"STRESS-{batch_index:05d}",
                "items": [
                    {"request_id": report.report_id, "text": report.text, "top_k": 1} for report in batch
                ],
            }
            batch_started = time.perf_counter()
            response = active_client.post("/v1/classify:batch", json=payload)
            latencies.append((time.perf_counter() - batch_started) * 1000)
            response.raise_for_status()
            items = response.json().get("items", [])
            if len(items) != len(batch):
                errors += abs(len(batch) - len(items))
            for item in items:
                body = item.get("response")
                if not isinstance(body, dict):
                    errors += 1
                    continue
                model_version = body.get("model_version")
                if isinstance(model_version, str):
                    model_versions.add(model_version)
                is_abstain = bool(body.get("abstain"))
                abstained += int(is_abstain)
                labels = body.get("labels")
                is_correct = (
                    isinstance(labels, list) and bool(labels) and labels[0].get("label_id") == expected_label
                )
                if is_correct:
                    correct += 1
                    accepted_correct += int(not is_abstain)
    finally:
        if owns_client:
            active_client.close()
    wall_seconds = time.perf_counter() - started
    successful = report_count - errors
    accepted = successful - abstained
    return {
        "benchmark": "http-classification-mass-outage",
        "contract_version": CONTRACT_VERSION,
        "model_versions": sorted(model_versions),
        "synthetic_config_version": config.version,
        "synthetic_config_sha256": hashlib.sha256(synthetic_config_path.read_bytes()).hexdigest(),
        "seed": seed,
        "generated_in_memory": True,
        "report_count": report_count,
        "batch_size": batch_size,
        "batch_count": math.ceil(report_count / batch_size),
        "wall_seconds": wall_seconds,
        "throughput_reports_per_second": report_count / wall_seconds,
        "batch_latency_ms": {
            "p50": _percentile(latencies, 0.50),
            "p95": _percentile(latencies, 0.95),
            "max": max(latencies),
        },
        "error_count": errors,
        "error_rate": errors / report_count,
        "top1_accuracy": correct / successful if successful else 0.0,
        "abstain_ratio": abstained / successful if successful else 1.0,
        "accepted_count": accepted,
        "accepted_top1_accuracy": accepted_correct / accepted if accepted else 0.0,
        "expected_label": expected_label,
        "limitations": [
            "Synthetic single-incident stress test; quality metrics are not a real-world estimate.",
            "Client and service run on the same host, so network latency is not representative.",
            "Batch endpoint processes items sequentially; throughput is the primary stress metric.",
        ],
    }


def _matching_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    target_rows = [row for row in rows if row["has_target"]]
    no_target_rows = [row for row in rows if not row["has_target"]]
    ranks = [int(row["first_target_rank"]) for row in target_rows if row["first_target_rank"]]
    return {
        "query_count": len(rows),
        "target_query_count": len(target_rows),
        "no_target_query_count": len(no_target_rows),
        "candidate_pair_count": sum(int(row["candidate_count"]) for row in rows),
        "recall_at_1": sum(rank <= 1 for rank in ranks) / len(target_rows) if target_rows else 0.0,
        "recall_at_3": sum(rank <= 3 for rank in ranks) / len(target_rows) if target_rows else 0.0,
        "mean_reciprocal_rank": sum(1.0 / rank for rank in ranks) / len(target_rows) if target_rows else 0.0,
        "missing_target_rate": 1.0 - len(ranks) / len(target_rows) if target_rows else 0.0,
        "abstain_ratio": sum(bool(row["abstain"]) for row in rows) / len(rows),
    }


def _incident_candidate(row: dict[str, Any]) -> IncidentCandidate:
    return IncidentCandidate(
        id=str(row["incident_id"]),
        started_at=_timestamp(str(row["started_at"])),
        category_id=str(row["category_id"]),
        fias_guids=tuple(str(item) for item in row["affected_fias_guids"]),
        title=str(row["text"]),
        status="ACTIVE",
        priority="NORMAL",
        active=True,
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _optional_string(value: object) -> str | None:
    return str(value) if value is not None else None


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * quantile) - 1))
    return ordered[index]
