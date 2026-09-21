"""Prompt construction with labels kept outside the model decision space."""

import json
from pathlib import Path
from typing import Any

from maxsmartcity.ml.data.llm.models import GenerationPass, ScenarioFact


def load_system_prompt(path: Path) -> str:
    prompt = path.read_text(encoding="utf-8").strip()
    if not prompt:
        msg = f"system prompt is empty: {path}"
        raise ValueError(msg)
    return prompt


def build_messages(
    system_prompt: str,
    fact: ScenarioFact,
    generation_pass: GenerationPass,
) -> tuple[dict[str, str], ...]:
    task: dict[str, Any] = {
        "task": "lexicalize_locked_fact",
        "scenario_spec_id": fact.scenario_spec_id,
        "locked_fact": {
            "problem": fact.problem,
            "context_tags": list(fact.context_tags),
            "danger_signals": list(fact.danger_signals),
            "needs_clarification": fact.needs_clarification,
            "ambiguity": fact.ambiguity,
        },
        "location": {
            "street": fact.street,
            "house_number": fact.house_number,
            "requirement": fact.address_requirement,
        },
        "generation": {
            "variant_count": generation_pass.variants_per_scenario,
            "allowed_styles": list(generation_pass.styles),
            "language": "ru",
        },
    }
    return (
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(task, ensure_ascii=False, sort_keys=True)},
    )


def response_json_schema(variant_count: int, styles: tuple[str, ...]) -> dict[str, Any]:
    return {
        "name": "report_lexicalization",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["scenario_spec_id", "variants"],
            "properties": {
                "scenario_spec_id": {"type": "string"},
                "variants": {
                    "type": "array",
                    "minItems": variant_count,
                    "maxItems": variant_count,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["text", "style_id", "address_included"],
                        "properties": {
                            "text": {"type": "string"},
                            "style_id": {"type": "string", "enum": list(styles)},
                            "address_included": {"type": "boolean"},
                        },
                    },
                },
            },
        },
    }
