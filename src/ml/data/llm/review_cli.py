"""Create a local CSV queue for human review of LLM candidates."""

import argparse
import json
from pathlib import Path

from src.ml.data.llm.input import load_scenario_facts
from src.ml.data.llm.review import (
    build_review_rows,
    build_review_summary,
    load_jsonl_objects,
    write_review_queue,
    write_review_summary,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = build_review_rows(
        load_jsonl_objects(args.candidates),
        load_scenario_facts(args.canonical),
    )
    summary = build_review_summary(rows)
    write_review_queue(args.output, rows)
    summary_path = args.output.with_suffix(".summary.json")
    write_review_summary(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
