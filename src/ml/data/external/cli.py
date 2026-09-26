"""CLI for rebuilding canonical scenario facts from local raw datasets."""

import argparse
import json
from pathlib import Path

from src.ml.data.config import load_taxonomy
from src.ml.data.external.builder import ExternalScenarioBuilder
from src.ml.data.external.config import load_external_build_config
from src.ml.data.external.importers import BmcCsvImporter, Sf311CsvImporter
from src.ml.data.external.mapping import load_external_mapping
from src.ml.data.external.writer import ExternalScenarioWriter


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--taxonomy", type=Path, required=True)
    parser.add_argument("--sf311-mapping", type=Path, required=True)
    parser.add_argument("--bmc-mapping", type=Path, required=True)
    parser.add_argument("--sf311-csv", type=Path, required=True)
    parser.add_argument("--bmc-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    config = load_external_build_config(args.config)
    builder = ExternalScenarioBuilder(
        config,
        load_taxonomy(args.taxonomy),
        load_external_mapping(args.sf311_mapping),
        load_external_mapping(args.bmc_mapping),
    )
    scenarios = builder.build(
        Sf311CsvImporter().read(args.sf311_csv),
        BmcCsvImporter().read(args.bmc_csv),
    )
    manifest = ExternalScenarioWriter().write(scenarios, args.output_dir, config=config)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
