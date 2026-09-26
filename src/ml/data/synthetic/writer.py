"""Versioned JSONL serialization and manifests for synthetic bundles."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.ml.data.synthetic.config import SyntheticConfig
from src.ml.data.synthetic.models import SyntheticBundle, SyntheticDataRecord


class SyntheticDatasetWriter:
    def write(
        self,
        bundle: SyntheticBundle,
        output_dir: Path,
        *,
        config: SyntheticConfig,
        master_seed: int,
        dataset_kind: str,
    ) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        collections: dict[str, tuple[SyntheticDataRecord, ...]] = {
            "scenarios": bundle.scenarios,
            "houses": bundle.houses,
            "organizations": bundle.organizations,
            "external_events": bundle.external_events,
            "incidents": bundle.incidents,
            "reports": bundle.reports,
            "decisions": bundle.decisions,
            "counterfactuals": bundle.counterfactuals,
        }
        file_hashes: dict[str, str] = {}
        for name, records in collections.items():
            file_hashes[f"{name}.jsonl"] = self._write_jsonl(output_dir / f"{name}.jsonl", records)
        config_hash = hashlib.sha256(
            json.dumps(asdict(config), ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        dataset_hash = hashlib.sha256(json.dumps(file_hashes, sort_keys=True).encode()).hexdigest()
        manifest: dict[str, Any] = {
            "dataset_hash": dataset_hash,
            "dataset_kind": dataset_kind,
            "dataset_version": f"{config.version}-{dataset_kind}-seed-{master_seed}",
            "generator_version": config.version,
            "config_hash": config_hash,
            "master_seed": master_seed,
            "schema_version": config.schema_version,
            "taxonomy_version": config.taxonomy_version,
            "counts": {name: len(records) for name, records in collections.items()},
            "files": file_hashes,
            "limitations": [
                "synthetic data is not a quality benchmark",
                "TODO[ingestion]: replace demo canonical entities with versioned export",
                "TODO[ml-data]: add human-reviewed Gold before model acceptance",
            ],
        }
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return manifest

    @staticmethod
    def _write_jsonl(path: Path, records: tuple[SyntheticDataRecord, ...]) -> str:
        digest = hashlib.sha256()
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            for record in records:
                line = json.dumps(asdict(record), ensure_ascii=False, sort_keys=True) + "\n"
                stream.write(line)
                digest.update(line.encode())
        return digest.hexdigest()
