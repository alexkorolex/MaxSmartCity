"""Smoke-test a local category model artifact."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from maxsmartcity.ml.inference.category import CategoryArtifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local category inference")
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--top-k", type=int, default=3)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    prediction = CategoryArtifact.load(args.artifact).predict(args.text, args.top_k)
    print(json.dumps(asdict(prediction), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
