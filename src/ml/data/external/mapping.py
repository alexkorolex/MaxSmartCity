"""Versioned, data-driven mapping from source taxonomies to the project taxonomy."""

from dataclasses import dataclass
from pathlib import Path

from src.ml.data.config import load_json_object, required_string


@dataclass(frozen=True, slots=True)
class MappingResult:
    rule_id: str
    category_ids: tuple[str, ...]
    subcategory_id: str
    problem: str
    object_type: str
    organization_type: str | None
    context_tags: tuple[str, ...]
    include: bool


@dataclass(frozen=True, slots=True)
class MappingRule:
    id: str
    match: tuple[tuple[str, str], ...]
    result: MappingResult

    def matches(self, attributes: dict[str, str]) -> bool:
        return all(attributes.get(key) == value for key, value in self.match)

    @property
    def specificity(self) -> int:
        return len(self.match)


@dataclass(frozen=True, slots=True)
class ExternalTaxonomyMapping:
    version: str
    source_dataset: str
    taxonomy_version: str
    rules: tuple[MappingRule, ...]

    def resolve(self, attributes: dict[str, str]) -> MappingResult | None:
        matches = [rule for rule in self.rules if rule.matches(attributes)]
        if not matches:
            return None
        matches.sort(key=lambda rule: (-rule.specificity, rule.id))
        best = matches[0]
        tied = [rule for rule in matches if rule.specificity == best.specificity]
        if len(tied) > 1:
            ids = ", ".join(rule.id for rule in tied)
            msg = f"ambiguous external mapping rules with equal specificity: {ids}"
            raise ValueError(msg)
        return best.result


def load_external_mapping(path: Path) -> ExternalTaxonomyMapping:
    payload = load_json_object(path)
    raw_rules = payload.get("rules")
    if not isinstance(raw_rules, list):
        msg = "external mapping rules must be a list"
        raise ValueError(msg)
    rules = tuple(_parse_rule(item) for item in raw_rules)
    ids = [rule.id for rule in rules]
    if len(ids) != len(set(ids)):
        msg = "external mapping rule ids must be unique"
        raise ValueError(msg)
    return ExternalTaxonomyMapping(
        version=required_string(payload, "version"),
        source_dataset=required_string(payload, "source_dataset"),
        taxonomy_version=required_string(payload, "taxonomy_version"),
        rules=rules,
    )


def _parse_rule(raw: object) -> MappingRule:
    if not isinstance(raw, dict):
        msg = "every external mapping rule must be an object"
        raise ValueError(msg)
    match = raw.get("match")
    output = raw.get("output")
    if not isinstance(match, dict) or not match:
        msg = "external mapping rule match must be a non-empty object"
        raise ValueError(msg)
    if not isinstance(output, dict):
        msg = "external mapping rule output must be an object"
        raise ValueError(msg)
    category_ids = output.get("category_ids")
    if (
        not isinstance(category_ids, list)
        or not category_ids
        or not all(isinstance(item, str) and item for item in category_ids)
    ):
        msg = "external mapping output category_ids must be a non-empty string list"
        raise ValueError(msg)
    tags = output.get("context_tags", [])
    if not isinstance(tags, list) or not all(isinstance(item, str) for item in tags):
        msg = "external mapping output context_tags must be a string list"
        raise ValueError(msg)
    organization_type = output.get("organization_type")
    if organization_type is not None and not isinstance(organization_type, str):
        msg = "external mapping output organization_type must be a string or null"
        raise ValueError(msg)
    rule_id = required_string(raw, "id")
    return MappingRule(
        id=rule_id,
        match=tuple(sorted((str(key), str(value)) for key, value in match.items())),
        result=MappingResult(
            rule_id=rule_id,
            category_ids=tuple(category_ids),
            subcategory_id=required_string(output, "subcategory_id"),
            problem=required_string(output, "problem"),
            object_type=required_string(output, "object_type"),
            organization_type=organization_type,
            context_tags=tuple(tags),
            include=bool(output.get("include", True)),
        ),
    )
