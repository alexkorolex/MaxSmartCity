"""Build the reviewed MVP report-text dataset and leakage-safe splits."""

import argparse
import json
from pathlib import Path

from src.ml.data.config import load_taxonomy
from src.ml.data.gold.builder import (
    ReviewedDatasetBuilder,
    ReviewedDatasetWriter,
    load_reviewed_dataset_config,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--taxonomy", type=Path, required=True)
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--seed-config", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    config = load_reviewed_dataset_config(args.config)
    records = ReviewedDatasetBuilder(config, load_taxonomy(args.taxonomy)).build(
        canonical_path=args.canonical,
        seed_config_path=args.seed_config,
        candidate_paths=tuple(args.candidates),
    )
    input_paths = (
        args.config,
        args.taxonomy,
        args.canonical,
        args.seed_config,
        *args.candidates,
    )
    manifest = ReviewedDatasetWriter().write(
        records,
        args.output_dir,
        config=config,
        input_paths=input_paths,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
