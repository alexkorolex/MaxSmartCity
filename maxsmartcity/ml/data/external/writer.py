"""Stable JSONL and manifest writer for canonical external scenarios."""

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from maxsmartcity.ml.data.external.config import ExternalBuildConfig
from maxsmartcity.ml.data.external.models import CanonicalScenarioSpec


class ExternalScenarioWriter:
    def write(
        self,
        scenarios: tuple[CanonicalScenarioSpec, ...],
        output_dir: Path,
        *,
        config: ExternalBuildConfig,
    ) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        scenario_path = output_dir / "scenarios.jsonl"
        lines = [
            json.dumps(_scenario_payload(item), ensure_ascii=False, sort_keys=True) for item in scenarios
        ]
        content = "\n".join(lines) + "\n"
        scenario_path.write_text(content, encoding="utf-8", newline="\n")
        dataset_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        source_counts = Counter(item.source.dataset_id for item in scenarios)
        category_counts = Counter(category for item in scenarios for category in item.category_ids)
        manifest: dict[str, Any] = {
            "dataset_name": "external-canonical-scenario-specs",
            "dataset_version": config.version,
            "schema_version": config.schema_version,
            "taxonomy_version": config.taxonomy_version,
            "status": "PRE_LLM_FACTS_REQUIRES_REVIEW",
            "record_count": len(scenarios),
            "source_counts": dict(sorted(source_counts.items())),
            "category_counts": dict(sorted(category_counts.items())),
            "seed": config.seed,
            "file": scenario_path.name,
            "sha256": dataset_hash,
        }
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return manifest


def _scenario_payload(item: CanonicalScenarioSpec) -> dict[str, Any]:
    return {
        "schema_version": item.schema_version,
        "scenario_spec_id": item.scenario_spec_id,
        "taxonomy_version": item.taxonomy_version,
        "category_ids": list(item.category_ids),
        "subcategory_id": item.subcategory_id,
        "problem": item.problem,
        "object_type": item.object_type,
        "severity": item.severity,
        "organization_type": item.organization_type,
        "location": {
            "city_id": item.location.city_id,
            "house_id": item.location.house_id,
            "street": item.location.street,
            "house_number": item.location.house_number,
            "synthetic": item.location.synthetic,
        },
        "source": {
            "dataset_id": item.source.dataset_id,
            "record_ids": list(item.source.record_ids),
            "semantic_key": item.source.semantic_key,
            "occurrence_count": item.source.occurrence_count,
        },
        "source_attributes": dict(item.source_attributes),
        "context_tags": list(item.context_tags),
        "danger_signals": list(item.danger_signals),
        "needs_clarification": item.needs_clarification,
        "ambiguity": item.ambiguity,
    }
