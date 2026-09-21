"""Evaluate a trained category artifact on a versioned Gold split."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sklearn.preprocessing import MultiLabelBinarizer

from maxsmartcity.ml.evaluation.classification import evaluate_category_predictions
from maxsmartcity.ml.inference.category import CategoryArtifact
from maxsmartcity.ml.training.dataset import load_split


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate a local category artifact")
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--dataset-dir", type=Path, default=Path("ml/data/gold/v1"))
    parser.add_argument("--split", choices=("validation", "test"), default="test")
    parser.add_argument("--output", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    artifact = CategoryArtifact.load(args.artifact)
    examples = load_split(args.dataset_dir / f"{args.split}.jsonl")
    labels = list(artifact.labels)
    binarizer = MultiLabelBinarizer(classes=labels)
    binarizer.fit([labels])
    metrics = evaluate_category_predictions(
        binarizer.transform([example.labels for example in examples]),
        artifact.predict_proba([example.text for example in examples]),
        labels,
        artifact.label_threshold,
        artifact.abstain_threshold,
    )
    rendered = json.dumps(metrics, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
