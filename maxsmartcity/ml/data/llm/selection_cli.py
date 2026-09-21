"""Build a deterministic scenario selection manifest for an LLM batch."""

import argparse
import json
from pathlib import Path

from maxsmartcity.ml.data.llm.input import load_scenario_facts
from maxsmartcity.ml.data.llm.selection import (
    build_selection_manifest,
    load_selection_config,
    select_facts,
    write_selection_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    config = load_selection_config(args.config)
    selected = select_facts(load_scenario_facts(args.input), config)
    manifest = build_selection_manifest(selected, config=config, canonical_path=args.input)
    write_selection_manifest(args.output, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
