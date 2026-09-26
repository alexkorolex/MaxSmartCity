"""Assemble the reviewed, backend-aligned Gold v2 dataset."""

import argparse
import json
from pathlib import Path

from src.ml.data.gold.assembly_v2 import (
    GoldV2Assembler,
    GoldV2AssemblyWriter,
    write_candidate_snapshot,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--migrated-dir", type=Path, required=True)
    parser.add_argument("--expansion-frames", type=Path, required=True)
    parser.add_argument("--expansion-seeds", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--candidate-snapshot",
        type=Path,
        help="Write a rebuildable, versioned subset of the API candidates and use it as input",
    )
    parser.add_argument("--split-seed", type=int, default=20260921)
    args = parser.parse_args()

    assembler = GoldV2Assembler(
        split_seed=args.split_seed,
        reviewer="codex-assisted-semantic-review-2026-09-21",
    )
    candidate_paths = tuple(args.candidates)
    if args.candidate_snapshot is not None:
        candidate_paths = (
            write_candidate_snapshot(
                frames_path=args.expansion_frames,
                candidate_paths=candidate_paths,
                output_path=args.candidate_snapshot,
            ),
        )
    splits = assembler.assemble(
        migrated_dir=args.migrated_dir,
        expansion_frames_path=args.expansion_frames,
        expansion_seeds_path=args.expansion_seeds,
        candidate_paths=candidate_paths,
    )
    input_paths = (
        args.migrated_dir / "manifest.json",
        args.expansion_frames,
        args.expansion_seeds,
        *candidate_paths,
    )
    manifest = GoldV2AssemblyWriter().write(splits, args.output_dir, input_paths=input_paths)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
