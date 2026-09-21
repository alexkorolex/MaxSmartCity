"""Create backend-aligned Gold v2 candidates from reviewed Gold v1."""

import argparse
import json
from pathlib import Path

from maxsmartcity.ml.data.gold.v2 import GoldV2MigrationConfig, GoldV2Migrator, GoldV2Writer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    config = GoldV2MigrationConfig.load(args.config)
    manifest = GoldV2Writer().write(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        migrator=GoldV2Migrator(config),
        config=config,
        config_path=args.config,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
