"""Command-line entry point for category model training."""

from __future__ import annotations

import argparse
from pathlib import Path

from maxsmartcity.ml.training.config import CategoryTrainingConfig
from maxsmartcity.ml.training.trainer import CategoryTrainer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the category TF-IDF baseline")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("ml/configs/training/category-tfidf-logreg.v2.json"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = CategoryTrainingConfig.load(args.config)
    result = CategoryTrainer(config, args.config).train()
    print(f"artifact={result.artifact_dir}")
    print(f"validation_macro_f1={result.validation_macro_f1:.4f}")
    print(f"test_macro_f1={result.test_macro_f1:.4f}")
    print(f"abstain_threshold={result.abstain_threshold:.4f}")


if __name__ == "__main__":
    main()
