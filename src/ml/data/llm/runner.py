"""Resumable offline LLM generation and candidate materialization."""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.ml.data.llm.client import LexicalizationClient
from src.ml.data.llm.config import LlmGenerationConfig
from src.ml.data.llm.models import GeneratedVariant, GenerationPass, ScenarioFact
from src.ml.data.llm.prompt import build_messages, response_json_schema
from src.ml.data.llm.validator import GeneratedVariantValidator


@dataclass(frozen=True, slots=True)
class GenerationTask:
    fact: ScenarioFact
    generation_pass: GenerationPass

    @property
    def key(self) -> str:
        return f"{self.fact.scenario_spec_id}:{self.generation_pass.id}"


class LlmGenerationRunner:
    def __init__(
        self,
        *,
        config: LlmGenerationConfig,
        system_prompt: str,
        client: LexicalizationClient | None,
    ) -> None:
        self._config = config
        self._system_prompt = system_prompt
        self._client = client
        self._validator = GeneratedVariantValidator(config)

    def plan(self, facts: tuple[ScenarioFact, ...]) -> tuple[GenerationTask, ...]:
        return tuple(
            GenerationTask(fact, generation_pass)
            for fact in sorted(facts, key=lambda item: item.scenario_spec_id)
            for generation_pass in self._config.passes
            if generation_pass.applies_to(fact.source_dataset_id)
        )

    def write_plan(self, tasks: tuple[GenerationTask, ...], output_dir: Path) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        requested_variants = sum(task.generation_pass.variants_per_scenario for task in tasks)
        max_output_tokens = len(tasks) * self._config.max_output_tokens
        plan: dict[str, Any] = {
            "config_version": self._config.version,
            "prompt_version": self._config.prompt_version,
            "model": self._config.model,
            "scenario_count": len({task.fact.scenario_spec_id for task in tasks}),
            "api_call_count": len(tasks),
            "requested_variant_count": requested_variants,
            "max_output_tokens": max_output_tokens,
            "max_output_cost_rub": round(
                max_output_tokens * self._config.output_rubles_per_million / 1_000_000,
                4,
            ),
            "tasks": [
                {
                    "key": task.key,
                    "scenario_spec_id": task.fact.scenario_spec_id,
                    "pass_id": task.generation_pass.id,
                    "temperature": task.generation_pass.temperature,
                    "variant_count": task.generation_pass.variants_per_scenario,
                }
                for task in tasks
            ],
        }
        _write_json(output_dir / "plan.json", plan)
        return plan

    def execute(
        self,
        tasks: tuple[GenerationTask, ...],
        output_dir: Path,
    ) -> dict[str, Any]:
        if self._client is None:
            msg = "LLM client is required for execution"
            raise RuntimeError(msg)
        output_dir.mkdir(parents=True, exist_ok=True)
        progress_path = output_dir / "generations.jsonl"
        records = _load_records(progress_path)
        completed = {
            str(record["task_key"]) for record in records if self._record_matches_current_run(record)
        }
        for task in tasks:
            if task.key in completed:
                continue
            messages = build_messages(self._system_prompt, task.fact, task.generation_pass)
            response = self._client.generate(
                model=self._config.model,
                messages=messages,
                response_schema=response_json_schema(
                    task.generation_pass.variants_per_scenario,
                    task.generation_pass.styles,
                ),
                temperature=task.generation_pass.temperature,
                top_p=self._config.top_p,
                max_output_tokens=self._config.max_output_tokens,
            )
            if response.scenario_spec_id != task.fact.scenario_spec_id:
                msg = (
                    "AI Tunnel changed scenario_spec_id: "
                    f"{task.fact.scenario_spec_id} -> {response.scenario_spec_id}"
                )
                raise ValueError(msg)
            validations = self._validator.validate(
                task.fact,
                task.generation_pass,
                response.variants,
            )
            response_errors = (
                ()
                if len(response.variants) == task.generation_pass.variants_per_scenario
                else ("WRONG_VARIANT_COUNT",)
            )
            record = {
                "task_key": task.key,
                "scenario_spec_id": task.fact.scenario_spec_id,
                "pass_id": task.generation_pass.id,
                "response_id": response.response_id,
                "model": response.model,
                "requested_model": self._config.model,
                "config_version": self._config.version,
                "prompt_version": self._config.prompt_version,
                "created_at": datetime.now(UTC).isoformat(),
                "usage": asdict(response.usage),
                "response_errors": list(response_errors),
                "variants": [
                    {
                        **asdict(item.variant),
                        "errors": [*response_errors, *item.errors],
                    }
                    for item in validations
                ],
            }
            _append_jsonl(progress_path, record)
            records.append(record)
        return self._materialize(tasks, records, output_dir)

    def _materialize(
        self,
        tasks: tuple[GenerationTask, ...],
        records: list[dict[str, Any]],
        output_dir: Path,
    ) -> dict[str, Any]:
        tasks_by_key = {task.key: task for task in tasks}
        relevant = [
            record
            for record in records
            if str(record["task_key"]) in tasks_by_key and self._record_matches_current_run(record)
        ]
        accepted: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        input_tokens = output_tokens = total_tokens = 0
        for record in relevant:
            task = tasks_by_key[str(record["task_key"])]
            usage = record.get("usage", {})
            if isinstance(usage, dict):
                input_tokens += _integer(usage.get("input_tokens"))
                output_tokens += _integer(usage.get("output_tokens"))
                total_tokens += _integer(usage.get("total_tokens"))
            variants = record.get("variants", [])
            if not isinstance(variants, list):
                continue
            generated_variants = tuple(
                GeneratedVariant(
                    text=str(variant.get("text", "")),
                    style_id=str(variant.get("style_id", "")),
                    address_included=variant.get("address_included") is True,
                )
                for variant in variants
                if isinstance(variant, dict)
            )
            validations = self._validator.validate(
                task.fact,
                task.generation_pass,
                generated_variants,
            )
            response_errors = record.get("response_errors", [])
            if not isinstance(response_errors, list):
                response_errors = ["MALFORMED_RESPONSE_ERRORS"]
            for index, validation in enumerate(validations):
                errors = [*response_errors, *validation.errors]
                variant = {
                    **asdict(validation.variant),
                    "errors": errors,
                }
                candidate = _candidate_payload(task, record, variant, index)
                if errors:
                    rejected.append(candidate)
                else:
                    accepted.append(candidate)
        accepted.sort(key=lambda item: str(item["candidate_id"]))
        rejected.sort(key=lambda item: str(item["candidate_id"]))
        accepted_hash = _write_payloads(output_dir / "candidates.jsonl", accepted)
        rejected_hash = _write_payloads(output_dir / "quarantine.jsonl", rejected)
        estimated_cost = (
            input_tokens * self._config.input_rubles_per_million
            + output_tokens * self._config.output_rubles_per_million
        ) / 1_000_000
        manifest: dict[str, Any] = {
            "dataset_name": "llm-report-candidates",
            "status": "CANDIDATES_REQUIRE_HUMAN_REVIEW",
            "config_version": self._config.version,
            "prompt_version": self._config.prompt_version,
            "model": self._config.model,
            "planned_call_count": len(tasks),
            "completed_call_count": len(relevant),
            "accepted_candidate_count": len(accepted),
            "quarantined_candidate_count": len(rejected),
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            },
            "estimated_cost_rub": round(estimated_cost, 4),
            "files": {
                "candidates.jsonl": accepted_hash,
                "quarantine.jsonl": rejected_hash,
            },
        }
        _write_json(output_dir / "manifest.json", manifest)
        return manifest

    def _record_matches_current_run(self, record: dict[str, Any]) -> bool:
        """Prevent stale responses from being reused after config or model changes."""
        return (
            record.get("config_version") == self._config.version
            and record.get("prompt_version") == self._config.prompt_version
            and record.get("requested_model") == self._config.model
        )


def _candidate_payload(
    task: GenerationTask,
    record: dict[str, Any],
    variant: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    identity = f"{task.key}:{record.get('response_id', '')}:{index}"
    return {
        "candidate_id": f"LLM-{hashlib.sha256(identity.encode()).hexdigest()[:16]}",
        "scenario_spec_id": task.fact.scenario_spec_id,
        "text": variant.get("text", ""),
        "style_id": variant.get("style_id", ""),
        "address_included": variant.get("address_included", False),
        "category_ids": list(task.fact.category_ids),
        "subcategory_id": task.fact.subcategory_id,
        "organization_type": task.fact.organization_type,
        "danger_signals": list(task.fact.danger_signals),
        "needs_clarification": task.fact.needs_clarification,
        "ambiguity": task.fact.ambiguity,
        "location": {
            "street": task.fact.street,
            "house_number": task.fact.house_number,
        },
        "generation": {
            "source": "LLM_SYNTHETIC",
            "model": record.get("model"),
            "response_id": record.get("response_id"),
            "pass_id": task.generation_pass.id,
            "config_version": record.get("config_version"),
            "prompt_version": record.get("prompt_version"),
        },
        "validation_errors": variant.get("errors", []),
        "review_status": "CANDIDATE_REQUIRES_HUMAN_REVIEW",
    }


def _load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            msg = f"generation progress contains a non-object record: {path}"
            raise ValueError(msg)
        records.append(payload)
    return records


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _write_payloads(path: Path, payloads: list[dict[str, Any]]) -> str:
    content = "".join(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n" for payload in payloads)
    path.write_text(content, encoding="utf-8", newline="\n")
    return hashlib.sha256(content.encode()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _integer(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0
