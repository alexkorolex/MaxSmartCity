"""Run the local E5 benchmark on ``other`` incident candidate sets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ml.adapters.embeddings import FastEmbedProvider
from src.ml.evaluation.other_matching import evaluate_other_matching


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, default=Path("ml/models"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    result = evaluate_other_matching(
        args.dataset_dir,
        FastEmbedProvider(cache_dir=args.cache_dir, threads=args.threads),
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")


if __name__ == "__main__":
    main()
