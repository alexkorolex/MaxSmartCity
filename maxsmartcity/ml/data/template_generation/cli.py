"""Generate a small local template-first preview without API calls."""

import argparse
import json
from pathlib import Path

from maxsmartcity.ml.data.template_generation.config import load_template_generation_config
from maxsmartcity.ml.data.template_generation.generator import TemplateExampleGenerator
from maxsmartcity.ml.data.template_generation.writer import write_template_preview


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    config = load_template_generation_config(args.config)
    examples = TemplateExampleGenerator(config).generate()
    manifest = write_template_preview(examples, args.output_dir)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
