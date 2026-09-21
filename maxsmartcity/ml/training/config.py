"""Configuration for the laptop-friendly category baseline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CategoryTrainingConfig:
    experiment_name: str
    model_version: str
    dataset_dir: Path
    artifact_dir: Path
    taxonomy_path: Path
    seed: int
    word_ngram_range: tuple[int, int]
    char_ngram_range: tuple[int, int]
    word_max_features: int
    char_max_features: int
    min_df: int
    max_iter: int
    label_threshold: float
    automation_precision_target: float
    minimum_coverage: float
    label_field: str = "category_ids"

    @classmethod
    def load(cls, path: Path) -> CategoryTrainingConfig:
        payload = json.loads(path.read_text(encoding="utf-8"))
        config = cls(
            experiment_name=str(payload["experiment_name"]),
            model_version=str(payload["model_version"]),
            dataset_dir=Path(payload["dataset_dir"]),
            artifact_dir=Path(payload["artifact_dir"]),
            taxonomy_path=Path(payload["taxonomy_path"]),
            seed=int(payload["seed"]),
            word_ngram_range=tuple(payload["word_ngram_range"]),
            char_ngram_range=tuple(payload["char_ngram_range"]),
            word_max_features=int(payload["word_max_features"]),
            char_max_features=int(payload["char_max_features"]),
            min_df=int(payload["min_df"]),
            max_iter=int(payload["max_iter"]),
            label_threshold=float(payload["label_threshold"]),
            automation_precision_target=float(payload["automation_precision_target"]),
            minimum_coverage=float(payload["minimum_coverage"]),
            label_field=str(payload.get("label_field", "category_ids")),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if not 0.0 < self.label_threshold < 1.0:
            raise ValueError("label_threshold must be between 0 and 1")
        if not 0.0 < self.automation_precision_target <= 1.0:
            raise ValueError("automation_precision_target must be in (0, 1]")
        if not 0.0 <= self.minimum_coverage <= 1.0:
            raise ValueError("minimum_coverage must be in [0, 1]")
        if self.min_df < 1:
            raise ValueError("min_df must be at least 1")
        if self.label_field not in {"category_ids", "primary_category"}:
            raise ValueError("label_field must be category_ids or primary_category")
