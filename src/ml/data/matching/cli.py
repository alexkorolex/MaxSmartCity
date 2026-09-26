"""Build retrieval and pairwise reranking datasets from a synthetic world."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ml.data.config import load_json_object, required_string
from src.ml.data.matching.builder import MatchingDatasetBuilder


def main() -> None:
    parser = argparse.ArgumentParser(description="Build synthetic matching datasets")
    parser.add_argument("--config", type=Path, default=Path("ml/configs/matching-dataset.v1.json"))
    args = parser.parse_args()
    config = load_json_object(args.config)
    builder = MatchingDatasetBuilder(
        version=required_string(config, "version"), split_seed=int(config["split_seed"])
    )
    manifest = builder.build(Path(config["source_dir"]), Path(config["output_dir"]))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
