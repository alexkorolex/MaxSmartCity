"""CLI for standard development and mass-outage synthetic datasets."""

import argparse
from pathlib import Path

from src.ml.data.synthetic.config import load_synthetic_config
from src.ml.data.synthetic.generator import SyntheticWorldGenerator
from src.ml.data.synthetic.writer import SyntheticDatasetWriter


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    standard = subparsers.add_parser("standard")
    standard.add_argument("--scenarios", type=int, default=200)
    standard.add_argument("--reports-per-scenario", type=int, default=5)
    standard.add_argument("--noise-reports", type=int, default=100)
    mass = subparsers.add_parser("mass-outage")
    mass.add_argument("--reports", type=int, default=10_000)
    args = parser.parse_args()

    config = load_synthetic_config(args.config)
    generator = SyntheticWorldGenerator(config, master_seed=args.seed)
    if args.mode == "standard":
        bundle = generator.generate_standard(
            scenario_count=args.scenarios,
            reports_per_scenario=args.reports_per_scenario,
            noise_reports=args.noise_reports,
        )
        dataset_kind = "dev"
    else:
        bundle = generator.generate_mass_outage(report_count=args.reports)
        dataset_kind = "stress-mass-outage"
    SyntheticDatasetWriter().write(
        bundle,
        args.output_dir,
        config=config,
        master_seed=args.seed,
        dataset_kind=dataset_kind,
    )


if __name__ == "__main__":
    main()
