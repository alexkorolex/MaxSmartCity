"""Run reproducible ML benchmarks without modifying source datasets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.ml.evaluation.benchmark import (
    evaluate_rule_matching,
    run_http_stress_benchmark,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    matching = subparsers.add_parser("matching", help="Evaluate the rule incident ranker")
    matching.add_argument("--dataset-dir", type=Path, default=Path("ml/data/matching/dev-v1"))
    matching.add_argument("--rule-config", type=Path, default=Path("ml/configs/rule-baseline.v1.json"))

    stress = subparsers.add_parser("stress", help="Benchmark the running ML HTTP service")
    stress.add_argument("--base-url", default="http://127.0.0.1:8001")
    stress.add_argument("--synthetic-config", type=Path, default=Path("ml/configs/synthetic.v2.json"))
    stress.add_argument("--reports", type=int, default=10_000)
    stress.add_argument("--batch-size", type=int, default=256)
    stress.add_argument("--seed", type=int, default=20260920)
    stress.add_argument("--timeout-seconds", type=float, default=120.0)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result: dict[str, Any]
    if args.mode == "matching":
        result = evaluate_rule_matching(args.dataset_dir, args.rule_config)
    else:
        result = run_http_stress_benchmark(
            base_url=args.base_url,
            synthetic_config_path=args.synthetic_config,
            report_count=args.reports,
            batch_size=args.batch_size,
            seed=args.seed,
            timeout_seconds=args.timeout_seconds,
        )
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")


if __name__ == "__main__":
    main()
