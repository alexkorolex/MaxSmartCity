"""Controlled LLM paraphrasing of grounded template seeds."""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from maxsmartcity.ml.data.config import load_json_object, required_string
from maxsmartcity.ml.data.llm.client import LexicalizationClient
from maxsmartcity.ml.data.llm.models import GeneratedVariant
from maxsmartcity.ml.data.llm.prompt import response_json_schema
from maxsmartcity.ml.data.llm.validator import contains_address, mentions_danger
from maxsmartcity.ml.data.template_generation.models import TemplateExample


@dataclass(frozen=True, slots=True)
class TemplateParaphraseConfig:
    version: str
    prompt_version: str
    prompt_file: Path
    model: str
    base_url: str
    timeout_seconds: float
    max_retries: int
    max_output_tokens: int
    temperature: float
    top_p: float
    input_rubles_per_million: float
    output_rubles_per_million: float


def load_template_paraphrase_config(path: Path) -> TemplateParaphraseConfig:
    payload = load_json_object(path)
    pricing = _required_object(payload, "pricing_rub_per_million_tokens")
    return TemplateParaphraseConfig(
        version=required_string(payload, "version"),
        prompt_version=required_string(payload, "prompt_version"),
        prompt_file=Path(required_string(payload, "prompt_file")),
        model=required_string(payload, "model"),
        base_url=required_string(payload, "base_url"),
        timeout_seconds=_positive_number(payload, "timeout_seconds"),
        max_retries=_nonnegative_int(payload, "max_retries"),
        max_output_tokens=_positive_int(payload, "max_output_tokens"),
        temperature=_probability(payload, "temperature"),
        top_p=_probability(payload, "top_p"),
        input_rubles_per_million=_positive_number(pricing, "input"),
        output_rubles_per_million=_positive_number(pricing, "output"),
    )


def select_one_seed_per_frame(
    examples: tuple[TemplateExample, ...],
) -> tuple[TemplateExample, ...]:
    selected: dict[str, TemplateExample] = {}
    for example in examples:
        selected.setdefault(example.frame_id, example)
    return tuple(selected[key] for key in sorted(selected))


def select_scenarios(
    examples: tuple[TemplateExample, ...], scenario_ids: frozenset[str]
) -> tuple[TemplateExample, ...]:
    selected = tuple(example for example in examples if example.frame_id in scenario_ids)
    found = {example.frame_id for example in selected}
    missing = scenario_ids - found
    if missing:
        msg = f"requested scenarios are absent from template seeds: {sorted(missing)}"
        raise ValueError(msg)
    return selected


def build_paraphrase_messages(
    system_prompt: str,
    example: TemplateExample,
) -> tuple[dict[str, str], ...]:
    payload = {
        "task": "controlled_paraphrase",
        "scenario_spec_id": example.example_id,
        "locked_contract": {
            "seed_text": example.text,
            "problem": example.base_problem,
            "location": {
                "street": example.street,
                "house_number": example.house_number,
                "required": example.address_required,
            },
            "context_tags": list(example.context_tags),
            "danger_signals": list(example.danger_signals),
            "location_scope": example.location_scope,
        },
        "required_outputs": ["neutral", "natural"],
        "must_not_add": [
            "duration_or_time",
            "cause",
            "organization_not_present_in_seed",
            "another_location",
            "entrance_floor_or_apartment",
            "affected_people",
            "actions_already_taken",
            "priority_or_severity",
        ],
    }
    return (
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    )


class TemplateParaphraseValidator:
    _emoji = re.compile(r"[\u2600-\u27bf\U0001f300-\U0001faff]")
    _slang = re.compile(r"\b(?:блин|капец|жесть|офиг\w*|чё|че|бред|здрасьте)\b", re.IGNORECASE)
    _invented_time = re.compile(
        r"\b(?:уже\s+)?(?:\d+|несколько|один|два|две|три|четыре|пять|"
        r"первый|второй|третий)\s*"
        r"(?:минут(?:у|ы)?|час(?:а|ов)?|дн(?:я|ей)|сут(?:ки|ок)|"
        r"недел(?:ю|и|ь)|месяц(?:а|ев)?)\b|"
        r"\b(?:давно|всю ночь|уже долго)\b",
        re.IGNORECASE,
    )
    _invented_urgency = re.compile(r"\b(?:срочно|немедленно|критически)\b", re.IGNORECASE)
    _unsupported_intensity = re.compile(
        r"\b(?:сильн\w*|слишком|важн\w*|серьезн\w*|значительн\w*)\b",
        re.IGNORECASE,
    )
    _invented_organization = re.compile(
        r"\b(?:водоканал|администраци\w*|мчс|пожарн\w*|управляющ\w+\s+компани\w*)\b",
        re.IGNORECASE,
    )

    def validate(
        self,
        example: TemplateExample,
        variants: tuple[GeneratedVariant, ...],
    ) -> tuple[tuple[GeneratedVariant, tuple[str, ...]], ...]:
        style_counts = {
            style: sum(item.style_id == style for item in variants) for style in self.styles
        }
        return tuple(
            (variant, self._errors(example, variant, style_counts)) for variant in variants
        )

    @property
    def styles(self) -> tuple[str, ...]:
        return ("neutral", "natural")

    def _errors(
        self,
        example: TemplateExample,
        variant: GeneratedVariant,
        style_counts: dict[str, int],
    ) -> tuple[str, ...]:
        text = variant.text.strip()
        errors: list[str] = []
        if variant.style_id not in self.styles:
            errors.append("STYLE_NOT_ALLOWED")
        elif style_counts[variant.style_id] != 1:
            errors.append("STYLE_NOT_UNIQUE")
        if len(text) < 3:
            errors.append("TEXT_TOO_SHORT")
        if len(text) > 240:
            errors.append("TEXT_TOO_LONG")
        if _normalize(text) == _normalize(example.text):
            errors.append("TEXT_UNCHANGED")
        if set(re.findall(r"\b\d+\b", text)) != set(re.findall(r"\b\d+\b", example.text)):
            errors.append("NUMERIC_FACTS_NOT_PRESERVED")
        if self._emoji.search(text):
            errors.append("EMOJI_FORBIDDEN")
        if self._slang.search(text):
            errors.append("SLANG_FORBIDDEN")
        if self._invented_time.search(text):
            errors.append("UNSUPPORTED_TIME")
        if self._invented_urgency.search(text):
            errors.append("UNSUPPORTED_URGENCY")
        if self._unsupported_intensity.search(text) and not self._unsupported_intensity.search(
            example.text
        ):
            errors.append("UNSUPPORTED_INTENSITY")
        organization_allowed = (
            "misleading_organization_mention" in example.context_tags
            or self._invented_organization.search(example.text) is not None
        )
        if self._invented_organization.search(text) and not organization_allowed:
            errors.append("UNSUPPORTED_ORGANIZATION")
        if re.search(r"[!?]{2,}|\.{3,}", text):
            errors.append("EXCESSIVE_PUNCTUATION")
        if example.address_required and not contains_address(
            text, example.street, example.house_number
        ):
            errors.append("REQUIRED_ADDRESS_MISSING")
        if not example.address_required and re.search(
            r"\b(?:(?:дом|д\.)\s*\d+|улиц\w*|ул\.\s|проспект\w*|переул\w*|шоссе)\b",
            text,
            re.IGNORECASE,
        ):
            errors.append("FORBIDDEN_ADDRESS_ADDED")
        if example.danger_signals and not mentions_danger(text, example.danger_signals):
            errors.append("DANGER_SIGNAL_NOT_PRESERVED")
        if example.location_scope == "OUTDOOR" and re.search(r"\bв доме\b", text, re.IGNORECASE):
            errors.append("OUTDOOR_EVENT_PLACED_INSIDE_BUILDING")
        if example.location_scope == "NONE" and re.search(
            r"\b(?:в доме|у дома|возле дома)\b", text, re.IGNORECASE
        ):
            errors.append("LOCATION_SCOPE_INFERRED")
        if "repeated_user" in example.context_tags and not re.search(
            r"\b(?:повтор\w*|снова|опять|ещё раз)\b", text, re.IGNORECASE
        ):
            errors.append("REPETITION_CONTEXT_NOT_PRESERVED")
        if "self_correction" in example.context_tags and not re.search(
            r"\b(?:ошиб\w*|исправ\w*)\b", text, re.IGNORECASE
        ):
            errors.append("SELF_CORRECTION_NOT_PRESERVED")
        if "external_event_conflict" in example.context_tags and not re.search(
            r"\b(?:объяв\w*|спис\w*|зон\w*)\b", text, re.IGNORECASE
        ):
            errors.append("EXTERNAL_EVIDENCE_NOT_PRESERVED")
        if "requires_verification" in example.context_tags and not re.search(
            r"\b(?:предполож\w*|возмож\w*|похож\w*|каж(?:ется|утся))\b", text, re.IGNORECASE
        ):
            errors.append("UNCERTAINTY_NOT_PRESERVED")
        if " или " in f" {_normalize(example.text)} " and not re.search(
            r"\b(?:или|либо)\b", text, re.IGNORECASE
        ):
            errors.append("DISJUNCTION_NOT_PRESERVED")
        if "актуаль" in example.text.casefold() and "актуаль" not in text.casefold():
            errors.append("CURRENT_RELEVANCE_NOT_PRESERVED")
        if "адрес указан" in text.casefold() and "адрес указан" not in example.text.casefold():
            errors.append("UNSUPPORTED_ADDRESS_META")
        if {"negated_danger", "negated_fire"} & set(
            example.context_tags
        ) and not _preserves_required_negation(example, text):
            errors.append("NEGATION_NOT_PRESERVED")
        if _sentence_count(text) > 2:
            errors.append("TOO_MANY_SENTENCES")
        return tuple(errors)


class TemplateParaphraseRunner:
    def __init__(
        self,
        *,
        config: TemplateParaphraseConfig,
        system_prompt: str,
        client: LexicalizationClient | None,
    ) -> None:
        self._config = config
        self._system_prompt = system_prompt
        self._client = client
        self._validator = TemplateParaphraseValidator()

    def write_plan(
        self,
        examples: tuple[TemplateExample, ...],
        output_dir: Path,
    ) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        plan = {
            "config_version": self._config.version,
            "prompt_version": self._config.prompt_version,
            "model": self._config.model,
            "api_call_count": len(examples),
            "requested_variant_count": len(examples) * 2,
            "example_ids": [example.example_id for example in examples],
        }
        _write_json(output_dir / "plan.json", plan)
        return plan

    def execute(
        self,
        examples: tuple[TemplateExample, ...],
        output_dir: Path,
    ) -> dict[str, Any]:
        if self._client is None:
            msg = "LLM client is required for paraphrase execution"
            raise RuntimeError(msg)
        progress_path = output_dir / "generations.jsonl"
        records = _load_jsonl(progress_path)
        completed = {
            str(record.get("task_key"))
            for record in records
            if record.get("config_version") == self._config.version
            and record.get("prompt_version") == self._config.prompt_version
            and record.get("requested_model") == self._config.model
        }
        for example in examples:
            if example.example_id in completed:
                continue
            response = self._client.generate(
                model=self._config.model,
                messages=build_paraphrase_messages(self._system_prompt, example),
                response_schema=response_json_schema(2, self._validator.styles),
                temperature=self._config.temperature,
                top_p=self._config.top_p,
                max_output_tokens=self._config.max_output_tokens,
            )
            if response.scenario_spec_id != example.example_id:
                msg = f"provider changed example id: {example.example_id}"
                raise ValueError(msg)
            record = {
                "task_key": example.example_id,
                "config_version": self._config.version,
                "prompt_version": self._config.prompt_version,
                "requested_model": self._config.model,
                "model": response.model,
                "response_id": response.response_id,
                "created_at": datetime.now(UTC).isoformat(),
                "usage": asdict(response.usage),
                "variants": [asdict(variant) for variant in response.variants],
            }
            _append_jsonl(progress_path, record)
            records.append(record)
        return self._materialize(examples, records, output_dir)

    def _materialize(
        self,
        examples: tuple[TemplateExample, ...],
        records: list[dict[str, Any]],
        output_dir: Path,
    ) -> dict[str, Any]:
        examples_by_id = {example.example_id: example for example in examples}
        accepted: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        input_tokens = output_tokens = total_tokens = 0
        relevant_records = [
            record
            for record in records
            if str(record.get("task_key")) in examples_by_id
            and record.get("config_version") == self._config.version
            and record.get("prompt_version") == self._config.prompt_version
            and record.get("requested_model") == self._config.model
        ]
        for record in relevant_records:
            example = examples_by_id[str(record["task_key"])]
            usage = record.get("usage", {})
            if isinstance(usage, dict):
                input_tokens += _integer(usage.get("input_tokens"))
                output_tokens += _integer(usage.get("output_tokens"))
                total_tokens += _integer(usage.get("total_tokens"))
            raw_variants = record.get("variants", [])
            variants = tuple(
                GeneratedVariant(
                    text=str(item.get("text", "")),
                    style_id=str(item.get("style_id", "")),
                    address_included=item.get("address_included") is True,
                )
                for item in raw_variants
                if isinstance(item, dict)
            )
            validations = self._validator.validate(example, variants)
            if len(variants) != 2:
                validations = tuple(
                    (variant, (*errors, "WRONG_VARIANT_COUNT")) for variant, errors in validations
                )
            for index, (variant, errors) in enumerate(validations):
                payload = {
                    "candidate_id": _candidate_id(example.example_id, record, index),
                    "example_id": example.example_id,
                    "frame_id": example.frame_id,
                    "seed_text": example.text,
                    "base_problem": example.base_problem,
                    "street": example.street,
                    "house_number": example.house_number,
                    "danger_signals": list(example.danger_signals),
                    "context_tags": list(example.context_tags),
                    "location_scope": example.location_scope,
                    "address_required": example.address_required,
                    "style_id": variant.style_id,
                    "text": variant.text,
                    "validation_errors": list(errors),
                    "review_status": "CANDIDATE_REQUIRES_HUMAN_REVIEW",
                }
                (rejected if errors else accepted).append(payload)
        _write_jsonl(output_dir / "candidates.jsonl", accepted)
        _write_jsonl(output_dir / "quarantine.jsonl", rejected)
        cost = (
            input_tokens * self._config.input_rubles_per_million
            + output_tokens * self._config.output_rubles_per_million
        ) / 1_000_000
        manifest = {
            "status": "CANDIDATES_REQUIRE_HUMAN_REVIEW",
            "config_version": self._config.version,
            "prompt_version": self._config.prompt_version,
            "model": self._config.model,
            "completed_call_count": len(relevant_records),
            "accepted_candidate_count": len(accepted),
            "quarantined_candidate_count": len(rejected),
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            },
            "estimated_cost_rub": round(cost, 4),
        }
        _write_json(output_dir / "manifest.json", manifest)
        return manifest


def _preserves_required_negation(example: TemplateExample, text: str) -> bool:
    normalized = _normalize(text)
    source = _normalize(f"{example.base_problem} {example.text}")
    preserved: list[bool] = []
    if "искр" in source:
        preserved.append(
            bool(
                re.search(
                    r"(?:не искр\w*|искрен\w*(?:\s+\w+){0,3}\s+нет|нет\s+искрен\w*|"
                    r"без\s+искрен\w*)",
                    normalized,
                )
            )
        )
    if any(token in source for token in ("огн", "пламен")):
        preserved.append(
            any(
                marker in normalized
                for marker in (
                    "огня не видно",
                    "не видно огня",
                    "огня нет",
                    "пламени нет",
                    "нет пламени",
                    "без открытого огня",
                    "открытого огня нет",
                    "открытого пламени не наблюдается",
                    "открытого огня не наблюдается",
                    "пламени не наблюдается",
                    "огня не наблюдается",
                )
            )
        )
    return bool(preserved) and all(preserved)


def _sentence_count(text: str) -> int:
    return len([part for part in re.split(r"[.!?]+", text) if part.strip()])


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[а-яёa-z0-9]+", value.casefold()))


def _candidate_id(example_id: str, record: dict[str, Any], index: int) -> str:
    identity = f"{example_id}:{record.get('response_id', '')}:{index}"
    return f"PAR-{hashlib.sha256(identity.encode()).hexdigest()[:16]}"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            payload = json.loads(line)
            if not isinstance(payload, dict):
                msg = f"non-object JSONL record: {path}"
                raise ValueError(msg)
            records.append(payload)
    return records


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _write_jsonl(path: Path, payloads: list[dict[str, Any]]) -> None:
    content = "".join(
        json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n" for payload in payloads
    )
    path.write_text(content, encoding="utf-8", newline="\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _required_object(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        msg = f"{key} must be an object"
        raise ValueError(msg)
    return value


def _positive_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        msg = f"{key} must be a positive integer"
        raise ValueError(msg)
    return value


def _nonnegative_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        msg = f"{key} must be a non-negative integer"
        raise ValueError(msg)
    return value


def _positive_number(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool) or value <= 0:
        msg = f"{key} must be a positive number"
        raise ValueError(msg)
    return float(value)


def _probability(payload: dict[str, Any], key: str) -> float:
    value = _positive_number(payload, key)
    if value > 1:
        msg = f"{key} must be in (0, 1]"
        raise ValueError(msg)
    return value


def _integer(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0
