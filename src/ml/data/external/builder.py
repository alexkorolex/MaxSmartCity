"""Build canonical, Russian-domain scenario facts without invoking an LLM."""

import hashlib
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from src.ml.data.config import TaxonomyConfig
from src.ml.data.external.config import ExternalBuildConfig
from src.ml.data.external.mapping import ExternalTaxonomyMapping, MappingResult
from src.ml.data.external.models import (
    BmcRecord,
    CanonicalLocation,
    CanonicalScenarioSpec,
    Sf311Record,
    SourceReference,
)


@dataclass(slots=True)
class _AggregatedCandidate:
    dataset_id: str
    semantic_key: str
    record_ids: list[str]
    occurrence_count: int
    attributes: dict[str, str]
    mapping: MappingResult
    severity: str


class ExternalScenarioBuilder:
    def __init__(
        self,
        config: ExternalBuildConfig,
        taxonomy: TaxonomyConfig,
        sf311_mapping: ExternalTaxonomyMapping,
        bmc_mapping: ExternalTaxonomyMapping,
    ) -> None:
        self._config = config
        self._taxonomy = taxonomy
        self._sf311_mapping = sf311_mapping
        self._bmc_mapping = bmc_mapping
        self._validate_versions()

    def build(
        self,
        sf311_records: Iterable[Sf311Record],
        bmc_records: Iterable[BmcRecord],
    ) -> tuple[CanonicalScenarioSpec, ...]:
        sf_candidates = self._aggregate_sf311(sf311_records)
        bmc_candidates = self._aggregate_bmc(bmc_records)
        selected = [
            *self._balanced_select(sf_candidates, self._config.sf311_limit),
            *self._balanced_select(bmc_candidates, self._config.bmc_limit),
        ]
        specs = [self._to_spec(candidate) for candidate in selected]
        specs.extend(self._curated_specs())
        specs.sort(key=lambda item: item.scenario_spec_id)
        if len(specs) != self._config.expected_scenario_count:
            msg = (
                f"external builder produced {len(specs)} scenarios, "
                f"expected {self._config.expected_scenario_count}"
            )
            raise ValueError(msg)
        return tuple(specs)

    def _aggregate_sf311(self, records: Iterable[Sf311Record]) -> tuple[_AggregatedCandidate, ...]:
        candidates: dict[str, _AggregatedCandidate] = {}
        for record in records:
            attributes = {
                "category": record.category,
                "type": record.type,
                "details": record.details,
            }
            mapping = self._sf311_mapping.resolve(attributes)
            if mapping is None or not mapping.include:
                continue
            existing = candidates.get(record.semantic_key)
            if existing is None:
                candidates[record.semantic_key] = _AggregatedCandidate(
                    dataset_id="sf311-recent-cases",
                    semantic_key=record.semantic_key,
                    record_ids=[record.case_id],
                    occurrence_count=1,
                    attributes={**attributes, "agency": record.agency},
                    mapping=mapping,
                    severity="unknown",
                )
            else:
                existing.occurrence_count += 1
                if len(existing.record_ids) < 3:
                    existing.record_ids.append(record.case_id)
        return tuple(candidates.values())

    def _aggregate_bmc(self, records: Iterable[BmcRecord]) -> tuple[_AggregatedCandidate, ...]:
        candidates: dict[str, _AggregatedCandidate] = {}
        for record in records:
            attributes = {
                "complaint_category": record.complaint_category,
                "department_assigned": record.department_assigned,
                "property_type": record.property_type,
                "complaint_channel": record.complaint_channel,
            }
            mapping = self._bmc_mapping.resolve(attributes)
            if mapping is None or not mapping.include:
                continue
            existing = candidates.get(record.semantic_key)
            if existing is None:
                candidates[record.semantic_key] = _AggregatedCandidate(
                    dataset_id="bmc-synthetic-complaints",
                    semantic_key=record.semantic_key,
                    record_ids=[record.complaint_id],
                    occurrence_count=1,
                    attributes=attributes,
                    mapping=mapping,
                    severity=record.severity.lower(),
                )
            else:
                existing.occurrence_count += 1
                if len(existing.record_ids) < 3:
                    existing.record_ids.append(record.complaint_id)
        return tuple(candidates.values())

    def _balanced_select(
        self,
        candidates: tuple[_AggregatedCandidate, ...],
        limit: int,
    ) -> tuple[_AggregatedCandidate, ...]:
        buckets: dict[str, list[_AggregatedCandidate]] = defaultdict(list)
        for candidate in candidates:
            bucket = candidate.mapping.category_ids[0]
            buckets[bucket].append(candidate)
        for values in buckets.values():
            values.sort(key=lambda item: _digest(f"{self._config.seed}:{item.semantic_key}"))
        selected: list[_AggregatedCandidate] = []
        category_ids = sorted(buckets)
        position = 0
        while len(selected) < limit and category_ids:
            next_categories: list[str] = []
            for category_id in category_ids:
                values = buckets[category_id]
                if position < len(values):
                    selected.append(values[position])
                    if len(selected) == limit:
                        break
                if position + 1 < len(values):
                    next_categories.append(category_id)
            position += 1
            category_ids = next_categories
        if len(selected) < limit:
            msg = f"only {len(selected)} mapped candidates available, requested {limit}"
            raise ValueError(msg)
        return tuple(selected)

    def _to_spec(self, candidate: _AggregatedCandidate) -> CanonicalScenarioSpec:
        mapping = candidate.mapping
        self._validate_category_ids(mapping.category_ids)
        digest = _digest(f"{candidate.dataset_id}:{candidate.semantic_key}")
        return CanonicalScenarioSpec(
            schema_version=self._config.schema_version,
            scenario_spec_id=f"EXT-{candidate.dataset_id.upper()}-{digest[:12]}",
            taxonomy_version=self._config.taxonomy_version,
            category_ids=mapping.category_ids,
            subcategory_id=mapping.subcategory_id,
            problem=mapping.problem,
            object_type=mapping.object_type,
            severity=candidate.severity,
            organization_type=mapping.organization_type,
            location=self._location(candidate.semantic_key),
            source=SourceReference(
                dataset_id=candidate.dataset_id,
                record_ids=tuple(candidate.record_ids),
                semantic_key=candidate.semantic_key,
                occurrence_count=candidate.occurrence_count,
            ),
            source_attributes=tuple(
                sorted(
                    {
                        **candidate.attributes,
                        "mapping_rule_id": mapping.rule_id,
                    }.items()
                )
            ),
            context_tags=mapping.context_tags,
        )

    def _curated_specs(self) -> list[CanonicalScenarioSpec]:
        specs: list[CanonicalScenarioSpec] = []
        for item in self._config.curated:
            self._validate_category_ids(item.category_ids)
            specs.append(
                CanonicalScenarioSpec(
                    schema_version=self._config.schema_version,
                    scenario_spec_id=f"CURATED-{item.id}",
                    taxonomy_version=self._config.taxonomy_version,
                    category_ids=item.category_ids,
                    subcategory_id=item.subcategory_id,
                    problem=item.problem,
                    object_type=item.object_type,
                    severity=item.severity,
                    organization_type=item.organization_type,
                    location=self._location(item.id),
                    source=SourceReference(
                        dataset_id="ml-data-curated-facts",
                        record_ids=(item.id,),
                        semantic_key=item.id,
                        occurrence_count=1,
                    ),
                    source_attributes=(("curated_fact_id", item.id),),
                    context_tags=item.context_tags,
                    danger_signals=item.danger_signals,
                    needs_clarification=item.needs_clarification,
                    ambiguity=item.ambiguity,
                )
            )
        return specs

    def _location(self, key: str) -> CanonicalLocation:
        digest = _digest(f"{self._config.seed}:location:{key}")
        number = int(digest[:8], 16)
        street = self._config.streets[number % len(self._config.streets)]
        house_number = str(number % 200 + 1)
        return CanonicalLocation(
            city_id=self._config.city_id,
            house_id=f"EXT-HOUSE-{digest[:12]}",
            street=street,
            house_number=house_number,
        )

    def _validate_versions(self) -> None:
        versions = {
            self._taxonomy.version,
            self._sf311_mapping.taxonomy_version,
            self._bmc_mapping.taxonomy_version,
            self._config.taxonomy_version,
        }
        if len(versions) != 1:
            msg = f"taxonomy version mismatch in external pipeline: {sorted(versions)}"
            raise ValueError(msg)

    def _validate_category_ids(self, category_ids: tuple[str, ...]) -> None:
        unknown = set(category_ids) - self._taxonomy.category_ids
        if unknown:
            msg = f"external scenario references unknown category ids: {sorted(unknown)}"
            raise ValueError(msg)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
