"""Classification, calibration and selective-risk metrics."""

from __future__ import annotations

from itertools import pairwise
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    hamming_loss,
    multilabel_confusion_matrix,
    precision_recall_fscore_support,
)


def expected_calibration_error(
    confidences: np.ndarray, correctness: np.ndarray, bins: int = 10
) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    value = 0.0
    for lower, upper in pairwise(edges):
        inclusive = upper == 1.0
        mask = (confidences >= lower) & (confidences <= upper if inclusive else confidences < upper)
        if np.any(mask):
            value += float(np.mean(mask)) * abs(
                float(np.mean(correctness[mask])) - float(np.mean(confidences[mask]))
            )
    return value


def risk_coverage_curve(confidences: np.ndarray, correctness: np.ndarray) -> list[dict[str, float]]:
    order = np.argsort(-confidences)
    ordered_correctness = correctness[order]
    ordered_confidences = confidences[order]
    cumulative_accuracy = np.cumsum(ordered_correctness) / np.arange(1, len(order) + 1)
    return [
        {
            "coverage": float((index + 1) / len(order)),
            "risk": float(1.0 - cumulative_accuracy[index]),
            "threshold": float(ordered_confidences[index]),
        }
        for index in range(len(order))
    ]


def select_abstain_threshold(
    confidences: np.ndarray,
    correctness: np.ndarray,
    precision_target: float,
    minimum_coverage: float,
) -> dict[str, float | bool]:
    candidates = risk_coverage_curve(confidences, correctness)
    feasible = [
        point
        for point in candidates
        if 1.0 - point["risk"] >= precision_target and point["coverage"] >= minimum_coverage
    ]
    if not feasible:
        return {
            "threshold": 1.0,
            "coverage": 0.0,
            "selective_accuracy": 0.0,
            "target_met": False,
        }
    selected = max(feasible, key=lambda point: point["coverage"])
    return {
        "threshold": selected["threshold"],
        "coverage": selected["coverage"],
        "selective_accuracy": 1.0 - selected["risk"],
        "target_met": True,
    }


def evaluate_category_predictions(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    labels: list[str],
    label_threshold: float,
    abstain_threshold: float,
) -> dict[str, Any]:
    y_pred = (probabilities >= label_threshold).astype(int)
    top_indices = np.argmax(probabilities, axis=1)
    confidences = np.max(probabilities, axis=1)
    correctness = y_true[np.arange(len(y_true)), top_indices].astype(float)
    has_prediction = np.any(y_pred, axis=1)
    accepted = (confidences >= abstain_threshold) & has_prediction
    precision, recall, class_f1, support = precision_recall_fscore_support(
        y_true, y_pred, average=None, zero_division=0
    )
    matrices = multilabel_confusion_matrix(y_true, y_pred)
    per_class = {
        label: {
            "precision": float(precision[index]),
            "recall": float(recall[index]),
            "f1": float(class_f1[index]),
            "support": int(support[index]),
            "confusion_matrix": matrices[index].tolist(),
        }
        for index, label in enumerate(labels)
    }
    selective_accuracy = float(np.mean(correctness[accepted])) if np.any(accepted) else 0.0
    return {
        "sample_count": len(y_true),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "subset_accuracy": float(accuracy_score(y_true, y_pred)),
        "hamming_loss": float(hamming_loss(y_true, y_pred)),
        "top1_accuracy": float(np.mean(correctness)),
        "brier_score": float(np.mean((probabilities - y_true) ** 2)),
        "ece": expected_calibration_error(confidences, correctness),
        "coverage": float(np.mean(accepted)),
        "selective_accuracy": selective_accuracy,
        "abstain_ratio": float(1.0 - np.mean(accepted)),
        "per_class": per_class,
        "risk_coverage": risk_coverage_curve(confidences, correctness),
        "confusion_matrix_kind": "one-vs-rest 2x2 per class: [[tn, fp], [fn, tp]]",
    }
