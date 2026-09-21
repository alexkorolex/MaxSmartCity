"""Train and package a lightweight multi-label category classifier."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import MultiLabelBinarizer

from maxsmartcity.ml.evaluation.classification import (
    evaluate_category_predictions,
    select_abstain_threshold,
)
from maxsmartcity.ml.training.config import CategoryTrainingConfig
from maxsmartcity.ml.training.dataset import assert_scenario_disjoint, load_split


@dataclass(frozen=True, slots=True)
class TrainingResult:
    artifact_dir: Path
    manifest_path: Path
    metrics_path: Path
    validation_macro_f1: float
    test_macro_f1: float
    abstain_threshold: float


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip()


def _primary_correctness(
    y_true: np.ndarray, probabilities: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    top_indices = np.argmax(probabilities, axis=1)
    confidences = np.max(probabilities, axis=1)
    correctness = y_true[np.arange(len(y_true)), top_indices].astype(float)
    return confidences, correctness


def _latency_metrics(pipeline: Pipeline, texts: list[str]) -> dict[str, float]:
    durations: list[float] = []
    for text in texts:
        started = time.perf_counter()
        pipeline.predict_proba([text])
        durations.append((time.perf_counter() - started) * 1000.0)
    return {
        "p50_ms": float(np.percentile(durations, 50)),
        "p95_ms": float(np.percentile(durations, 95)),
        "sample_count": float(len(durations)),
    }


class CategoryTrainer:
    """Owns dataset validation, fitting, calibration selection and artifact writing."""

    def __init__(self, config: CategoryTrainingConfig, config_path: Path) -> None:
        self._config = config
        self._config_path = config_path

    def train(self) -> TrainingResult:
        splits = {
            name: load_split(self._config.dataset_dir / f"{name}.jsonl", self._config.label_field)
            for name in ("train", "validation", "test")
        }
        assert_scenario_disjoint(splits)
        taxonomy = json.loads(self._config.taxonomy_path.read_text(encoding="utf-8"))
        labels = [str(category["id"]) for category in taxonomy["categories"]]
        binarizer = MultiLabelBinarizer(classes=labels)
        binarizer.fit([labels])

        pipeline = self._build_pipeline()
        train = splits["train"]
        pipeline.fit(
            [example.text for example in train],
            binarizer.transform([example.labels for example in train]),
        )

        probabilities = {
            name: np.asarray(pipeline.predict_proba([item.text for item in examples]))
            for name, examples in splits.items()
        }
        y_true = {
            name: binarizer.transform([item.labels for item in examples])
            for name, examples in splits.items()
        }
        validation_confidence, validation_correctness = _primary_correctness(
            y_true["validation"], probabilities["validation"]
        )
        threshold_selection = select_abstain_threshold(
            validation_confidence,
            validation_correctness,
            self._config.automation_precision_target,
            self._config.minimum_coverage,
        )
        selected_abstain_threshold = float(threshold_selection["threshold"])
        abstain_threshold = max(selected_abstain_threshold, self._config.label_threshold)
        threshold_selection["selected_before_label_floor"] = selected_abstain_threshold
        threshold_selection["threshold"] = abstain_threshold
        threshold_selection["label_threshold_floor_applied"] = (
            abstain_threshold != selected_abstain_threshold
        )
        validation_accepted = validation_confidence >= abstain_threshold
        effective_coverage = float(np.mean(validation_accepted))
        effective_accuracy = (
            float(np.mean(validation_correctness[validation_accepted]))
            if np.any(validation_accepted)
            else 0.0
        )
        threshold_selection["coverage"] = effective_coverage
        threshold_selection["selective_accuracy"] = effective_accuracy
        threshold_selection["target_met"] = (
            effective_coverage >= self._config.minimum_coverage
            and effective_accuracy >= self._config.automation_precision_target
        )

        majority_label = Counter(label for item in train for label in item.labels).most_common(1)[
            0
        ][0]
        majority_index = labels.index(majority_label)
        majority_metrics: dict[str, Any] = {"label": majority_label, "splits": {}}
        for name in ("validation", "test"):
            majority_probabilities = np.zeros_like(probabilities[name])
            majority_probabilities[:, majority_index] = 1.0
            majority_metrics["splits"][name] = evaluate_category_predictions(
                y_true[name], majority_probabilities, labels, 0.5, 0.0
            )

        metrics: dict[str, Any] = {
            "experiment_name": self._config.experiment_name,
            "selection_split": "validation",
            "test_used_for_selection": False,
            "label_threshold": self._config.label_threshold,
            "abstain_threshold": abstain_threshold,
            "threshold_selection": threshold_selection,
            "baselines": {"majority_label": majority_metrics},
            "splits": {
                name: evaluate_category_predictions(
                    y_true[name],
                    probabilities[name],
                    labels,
                    self._config.label_threshold,
                    abstain_threshold,
                )
                for name in ("validation", "test")
            },
            "latency": _latency_metrics(pipeline, [item.text for item in splits["test"]]),
        }
        self._write_artifact(pipeline, labels, abstain_threshold, metrics, taxonomy)
        return TrainingResult(
            artifact_dir=self._config.artifact_dir,
            manifest_path=self._config.artifact_dir / "manifest.json",
            metrics_path=self._config.artifact_dir / "metrics.json",
            validation_macro_f1=float(metrics["splits"]["validation"]["macro_f1"]),
            test_macro_f1=float(metrics["splits"]["test"]["macro_f1"]),
            abstain_threshold=abstain_threshold,
        )

    def _build_pipeline(self) -> Pipeline:
        features = FeatureUnion(
            [
                (
                    "word",
                    TfidfVectorizer(
                        analyzer="word",
                        ngram_range=self._config.word_ngram_range,
                        max_features=self._config.word_max_features,
                        min_df=self._config.min_df,
                        sublinear_tf=True,
                    ),
                ),
                (
                    "char",
                    TfidfVectorizer(
                        analyzer="char_wb",
                        ngram_range=self._config.char_ngram_range,
                        max_features=self._config.char_max_features,
                        min_df=self._config.min_df,
                        sublinear_tf=True,
                    ),
                ),
            ]
        )
        classifier = OneVsRestClassifier(
            LogisticRegression(
                class_weight="balanced",
                max_iter=self._config.max_iter,
                random_state=self._config.seed,
                solver="liblinear",
            ),
            n_jobs=1,
        )
        return Pipeline([("features", features), ("classifier", classifier)])

    def _write_artifact(
        self,
        pipeline: Pipeline,
        labels: list[str],
        abstain_threshold: float,
        metrics: dict[str, Any],
        taxonomy: dict[str, Any],
    ) -> None:
        target = self._config.artifact_dir
        target.mkdir(parents=True, exist_ok=True)
        dataset_manifest_path = self._config.dataset_dir / "manifest.json"
        dataset_manifest = json.loads(dataset_manifest_path.read_text(encoding="utf-8"))
        manifest = {
            "model_name": "category-tfidf-logreg",
            "model_version": self._config.model_version,
            "base_model": "scikit-learn:tfidf-word-char+ovr-logistic-regression",
            "dataset_version": str(dataset_manifest["dataset_version"]),
            "dataset_hash": _sha256(dataset_manifest_path),
            "taxonomy_version": str(taxonomy["version"]),
            "training_seed": self._config.seed,
            "git_commit": _git_commit(),
            "training_config_hash": _sha256(self._config_path),
            "calibration_version": "uncalibrated-validation-threshold-v1",
            "created_at": datetime.now(UTC).isoformat(),
        }
        bundle = {
            "pipeline": pipeline,
            "labels": labels,
            "label_threshold": self._config.label_threshold,
            "abstain_threshold": abstain_threshold,
            "model_version": self._config.model_version,
            "taxonomy_version": str(taxonomy["version"]),
        }
        joblib.dump(bundle, target / "model.joblib")
        (target / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (target / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        experiment = {
            "config": asdict(self._config),
            "runtime": {
                "python": platform.python_version(),
                "scikit_learn": sklearn.__version__,
                "numpy": np.__version__,
                "joblib": joblib.__version__,
            },
            "files": {
                "model": "model.joblib",
                "manifest": "manifest.json",
                "metrics": "metrics.json",
            },
            "limitations": [
                "Top-level category classification only; subcategory hierarchy is not trained.",
                "The configured Gold dataset is synthetic/LLM-assisted pending team sign-off.",
                "Threshold is selected on validation; test is evaluation-only.",
            ],
        }
        (target / "experiment.json").write_text(
            json.dumps(experiment, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
