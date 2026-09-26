"""Semantic ranking metrics for the deterministic ``other`` candidate sets."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from maxsmartcity.ml.ports.embeddings import TextEmbeddingProvider


def evaluate_other_matching(dataset_dir: Path, provider: TextEmbeddingProvider) -> dict[str, Any]:
    candidate_sets = _read_jsonl(dataset_dir / "candidate_sets.jsonl")
    incidents = _read_jsonl(dataset_dir / "incidents.jsonl")
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    query_texts = [str(item["text"]) for item in candidate_sets]
    incident_texts = ["\n".join(item["representative_texts"]) for item in incidents]
    started = time.perf_counter()
    query_vectors = provider.embed_queries(query_texts)
    document_vectors = provider.embed_documents(incident_texts)
    elapsed = time.perf_counter() - started
    incident_index = {str(item["incident_id"]): index for index, item in enumerate(incidents)}
    rows: list[dict[str, Any]] = []
    for query_index, item in enumerate(candidate_sets):
        candidate_ids = [str(value) for value in item["candidate_incident_ids"]]
        scores = [
            float(query_vectors[query_index] @ document_vectors[incident_index[candidate_id]])
            for candidate_id in candidate_ids
        ]
        order = sorted(range(len(candidate_ids)), key=lambda index: (-scores[index], candidate_ids[index]))
        ranked_ids = [candidate_ids[index] for index in order]
        ranked_scores = [scores[index] for index in order]
        target = item.get("target_incident_id")
        rank = ranked_ids.index(target) + 1 if target in ranked_ids else None
        rows.append(
            {
                "query_id": item["query_id"],
                "split": item["split"],
                "target": target,
                "rank": rank,
                "best_id": ranked_ids[0],
                "best_score": ranked_scores[0],
                "margin": ranked_scores[0] - ranked_scores[1],
                "correct_top1": target is not None and ranked_ids[0] == target,
            }
        )
    return {
        "benchmark": "semantic-other-incident-matching",
        "dataset_version": manifest["dataset_version"],
        "model_name": provider.model_name,
        "query_count": len(rows),
        "candidate_incident_count": len(incidents),
        "embedding_seconds": round(elapsed, 4),
        "texts_per_second": round((len(query_texts) + len(incident_texts)) / elapsed, 2),
        "splits": {
            split: _metrics(rows if split == "all" else [row for row in rows if row["split"] == split])
            for split in ("train", "validation", "test", "all")
        },
        "limitations": manifest["limitations"],
    }


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    positives = [row for row in rows if row["target"] is not None]
    negatives = [row for row in rows if row["target"] is None]
    ranks = [int(row["rank"]) for row in positives if row["rank"] is not None]
    return {
        "query_count": len(rows),
        "match_query_count": len(positives),
        "create_new_query_count": len(negatives),
        "recall_at_1": _safe_ratio(sum(rank <= 1 for rank in ranks), len(positives)),
        "recall_at_3": _safe_ratio(sum(rank <= 3 for rank in ranks), len(positives)),
        "mean_reciprocal_rank": _safe_ratio(sum(1.0 / rank for rank in ranks), len(positives)),
        "policies": {
            f"score_{score:.2f}_margin_{margin:.2f}": _policy_metrics(rows, score, margin)
            for score, margin in (
                (0.84, 0.00),
                (0.88, 0.00),
                (0.90, 0.00),
                (0.92, 0.00),
                (0.88, 0.02),
                (0.88, 0.05),
            )
        },
        "score_distribution": {
            "correct_match_p10_p50_p90": _quantiles(
                [float(row["best_score"]) for row in positives if row["correct_top1"]]
            ),
            "create_new_p10_p50_p90": _quantiles([float(row["best_score"]) for row in negatives]),
        },
    }


def _policy_metrics(rows: list[dict[str, Any]], score: float, margin: float) -> dict[str, Any]:
    presented = [row for row in rows if row["best_score"] >= score and row["margin"] >= margin]
    correct = [row for row in presented if row["correct_top1"]]
    positives = [row for row in rows if row["target"] is not None]
    negatives = [row for row in rows if row["target"] is None]
    suppressed_negatives = [row for row in negatives if row["best_score"] < score or row["margin"] < margin]
    return {
        "presented_count": len(presented),
        "recommendation_precision": _safe_ratio(len(correct), len(presented)),
        "correct_recommendation_recall": _safe_ratio(len(correct), len(positives)),
        "create_new_detection_rate": _safe_ratio(len(suppressed_negatives), len(negatives)),
    }


def _quantiles(values: list[float]) -> list[float]:
    if not values:
        return []
    return [round(float(np.quantile(values, point)), 6) for point in (0.1, 0.5, 0.9)]


def _safe_ratio(numerator: float, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
