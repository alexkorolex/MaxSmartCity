"""Load a trusted local category artifact and return structured predictions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np


@dataclass(frozen=True, slots=True)
class CategoryScore:
    label_id: str
    score: float


@dataclass(frozen=True, slots=True)
class CategoryPrediction:
    labels: tuple[CategoryScore, ...]
    abstain: bool
    abstain_reason: str | None
    model_version: str
    taxonomy_version: str


class CategoryArtifact:
    """Inference facade. Only load joblib files produced by this repository."""

    def __init__(self, bundle: dict[str, Any]) -> None:
        self._pipeline = bundle["pipeline"]
        self._labels = tuple(str(label) for label in bundle["labels"])
        self._label_threshold = float(bundle["label_threshold"])
        self._abstain_threshold = float(bundle["abstain_threshold"])
        self._model_version = str(bundle["model_version"])
        self._taxonomy_version = str(bundle["taxonomy_version"])

    @classmethod
    def load(cls, artifact_dir: Path) -> CategoryArtifact:
        bundle = joblib.load(artifact_dir / "model.joblib")
        if not isinstance(bundle, dict):
            raise ValueError("Invalid category artifact bundle")
        return cls(bundle)

    def predict(self, text: str, top_k: int = 3) -> CategoryPrediction:
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        if not text.strip():
            return CategoryPrediction(
                labels=(),
                abstain=True,
                abstain_reason="EMPTY_TEXT",
                model_version=self._model_version,
                taxonomy_version=self._taxonomy_version,
            )
        probabilities = np.asarray(self._pipeline.predict_proba([text]))[0]
        order = np.argsort(-probabilities)
        selected = [
            CategoryScore(self._labels[index], float(probabilities[index]))
            for index in order
            if probabilities[index] >= self._label_threshold
        ][:top_k]
        has_label_above_threshold = bool(selected)
        if not has_label_above_threshold:
            selected = [CategoryScore(self._labels[int(order[0])], float(probabilities[order[0]]))]
        best_score = selected[0].score
        abstain = not has_label_above_threshold or best_score < self._abstain_threshold
        abstain_reason = None
        if not has_label_above_threshold:
            abstain_reason = "NO_LABEL_ABOVE_THRESHOLD"
        elif abstain:
            abstain_reason = "LOW_CONFIDENCE"
        return CategoryPrediction(
            labels=tuple(selected),
            abstain=abstain,
            abstain_reason=abstain_reason,
            model_version=self._model_version,
            taxonomy_version=self._taxonomy_version,
        )

    @property
    def labels(self) -> tuple[str, ...]:
        return self._labels

    @property
    def label_threshold(self) -> float:
        return self._label_threshold

    @property
    def abstain_threshold(self) -> float:
        return self._abstain_threshold

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self._pipeline.predict_proba(texts))
