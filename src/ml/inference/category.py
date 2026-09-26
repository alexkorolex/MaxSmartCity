"""Load a trusted local category artifact and return structured predictions."""

from __future__ import annotations

import hashlib
import json
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
        self._dataset_version = _optional_string(bundle.get("dataset_version"))
        self._dataset_hash = _optional_string(bundle.get("dataset_hash"))
        self._calibration_version = _optional_string(bundle.get("calibration_version"))

    @classmethod
    def load(cls, artifact_dir: Path) -> CategoryArtifact:
        model_path = artifact_dir / "model.joblib"
        manifest_path = artifact_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_hash = manifest.get("model_sha256")
        if not isinstance(expected_hash, str):
            raise ValueError("Artifact manifest has no model_sha256")
        actual_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError("Category artifact checksum mismatch")
        bundle = joblib.load(model_path)
        if not isinstance(bundle, dict):
            raise ValueError("Invalid category artifact bundle")
        if bundle.get("model_version") != manifest.get("model_version"):
            raise ValueError("Category artifact model version mismatch")
        if bundle.get("taxonomy_version") != manifest.get("taxonomy_version"):
            raise ValueError("Category artifact taxonomy version mismatch")
        bundle.update(
            dataset_version=manifest.get("dataset_version"),
            dataset_hash=manifest.get("dataset_hash"),
            calibration_version=manifest.get("calibration_version"),
        )
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

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def taxonomy_version(self) -> str:
        return self._taxonomy_version

    @property
    def dataset_version(self) -> str | None:
        return self._dataset_version

    @property
    def dataset_hash(self) -> str | None:
        return self._dataset_hash

    @property
    def calibration_version(self) -> str | None:
        return self._calibration_version

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self._pipeline.predict_proba(texts))


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None
