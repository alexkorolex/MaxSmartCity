"""Generate deterministic additional Gold v2 frames and grounded text seeds."""

import argparse
import json
from pathlib import Path

from maxsmartcity.ml.data.gold.expansion import (
    ExpansionConfig,
    GoldV2ExpansionGenerator,
    GoldV2ExpansionWriter,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    config = ExpansionConfig.load(args.config)
    frames, examples = GoldV2ExpansionGenerator(config).generate()
    manifest = GoldV2ExpansionWriter().write(
        frames, examples, args.output_dir, config_path=args.config
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
