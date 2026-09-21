"""Build two deterministic template seeds for every canonical scenario fact."""

import argparse
import json
from pathlib import Path

from maxsmartcity.ml.data.llm.input import load_scenario_facts
from maxsmartcity.ml.data.template_generation.canonical import (
    CanonicalTemplateSeedGenerator,
    load_canonical_seed_config,
)
from maxsmartcity.ml.data.template_generation.writer import write_template_preview


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    examples = CanonicalTemplateSeedGenerator(load_canonical_seed_config(args.config)).generate(
        load_scenario_facts(args.canonical)
    )
    manifest = write_template_preview(examples, args.output_dir)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
