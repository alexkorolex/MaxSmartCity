import json
import re
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from maxsmartcity.ml.data.llm.input import load_scenario_facts
from maxsmartcity.ml.data.llm.models import (
    GeneratedVariant,
    GenerationResponse,
    GenerationUsage,
)
from maxsmartcity.ml.data.template_generation.canonical import (
    CanonicalTemplateSeedGenerator,
    load_canonical_seed_config,
)
from maxsmartcity.ml.data.template_generation.config import load_template_generation_config
from maxsmartcity.ml.data.template_generation.generator import TemplateExampleGenerator
from maxsmartcity.ml.data.template_generation.paraphrase import (
    TemplateParaphraseRunner,
    TemplateParaphraseValidator,
    build_paraphrase_messages,
    load_template_paraphrase_config,
    select_one_seed_per_frame,
)
from maxsmartcity.ml.data.template_generation.writer import (
    load_template_examples,
    write_template_preview,
)

ROOT = Path(__file__).parents[2]
CONFIG_PATH = ROOT / "ml/configs/template-generation.preview-v1.json"
PARAPHRASE_CONFIG_PATH = ROOT / "ml/configs/template-paraphrase.pilot-v2.json"
CANONICAL_CONFIG_PATH = ROOT / "ml/configs/canonical-template-seeds.v1.json"
CANONICAL_FACTS_PATH = ROOT / "ml/data/external/canonical/v1/scenarios.jsonl"


class FakeParaphraseClient:
    def __init__(self) -> None:
        self.calls = 0

    def generate(
        self,
        *,
        model: str,
        messages: Sequence[dict[str, str]],
        response_schema: dict[str, Any],
        temperature: float,
        top_p: float,
        max_output_tokens: int,
    ) -> GenerationResponse:
        del response_schema, temperature, top_p, max_output_tokens
        self.calls += 1
        payload = json.loads(messages[1]["content"])
        locked = payload["locked_contract"]
        location = locked["location"]
        prefix = f"{location['street']}, дом {location['house_number']}"
        return GenerationResponse(
            response_id=f"response-{self.calls}",
            model=model,
            scenario_spec_id=payload["scenario_spec_id"],
            variants=(
                GeneratedVariant(
                    f"По адресу {prefix} наблюдается проблема: {locked['problem']}.",
                    "neutral",
                    True,
                ),
                GeneratedVariant(
                    f"Сообщаю: {prefix}, {locked['problem']}.",
                    "natural",
                    True,
                ),
            ),
            usage=GenerationUsage(200, 80, 280),
        )


def test_template_preview_is_deterministic_grounded_and_small(tmp_path: Path) -> None:
    config = load_template_generation_config(CONFIG_PATH)

    first = TemplateExampleGenerator(config).generate()
    second = TemplateExampleGenerator(config).generate()

    assert first == second
    assert len(first) == 20
    assert len({example.example_id for example in first}) == 20
    assert all(
        example.street.casefold() in example.text.casefold()
        for example in first
        if example.template_id != "building_at"
    )
    assert all(example.house_number in example.text for example in first)

    manifest = write_template_preview(first, tmp_path)

    assert manifest["example_count"] == 20
    assert manifest["frame_count"] == 10
    assert (tmp_path / "examples.jsonl").is_file()
    assert (tmp_path / "PREVIEW.md").is_file()


def test_template_preview_has_no_creative_style_markers() -> None:
    examples = TemplateExampleGenerator(load_template_generation_config(CONFIG_PATH)).generate()
    forbidden = re.compile(r"🔥|😱|😤|\b(?:блин|капец|чё)\b|!{3,}|\?{3,}", re.IGNORECASE)

    assert all(forbidden.search(example.text) is None for example in examples)


def test_canonical_template_seeds_cover_every_fact_twice(tmp_path: Path) -> None:
    facts = load_scenario_facts(CANONICAL_FACTS_PATH)
    examples = CanonicalTemplateSeedGenerator(
        load_canonical_seed_config(CANONICAL_CONFIG_PATH)
    ).generate(facts)

    assert len(facts) == 181
    assert len(examples) == 362
    assert len({example.frame_id for example in examples}) == 181
    assert all(
        sum(candidate.frame_id == example.frame_id for candidate in examples) == 2
        for example in examples
    )
    assert all(
        example.house_number in example.text for example in examples if example.address_required
    )
    assert all(
        not example.street and not example.house_number
        for example in examples
        if not example.address_required
    )

    write_template_preview(examples, tmp_path)
    assert load_template_examples(tmp_path / "examples.jsonl") == examples


def test_paraphrase_pilot_selects_one_clean_seed_per_frame() -> None:
    examples = TemplateExampleGenerator(load_template_generation_config(CONFIG_PATH)).generate()

    selected = select_one_seed_per_frame(examples)

    assert len(selected) == 10
    assert len({example.frame_id for example in selected}) == 10


def test_paraphrase_prompt_contains_fact_contract_without_labels() -> None:
    example = TemplateExampleGenerator(load_template_generation_config(CONFIG_PATH)).generate()[0]
    messages = build_paraphrase_messages("system", example)
    payload = json.loads(messages[1]["content"])

    assert payload["locked_contract"]["seed_text"] == example.text
    assert payload["required_outputs"] == ["neutral", "natural"]
    assert "category_ids" not in payload["locked_contract"]
    assert "subcategory_id" not in payload["locked_contract"]


def test_paraphrase_validator_rejects_creative_additions() -> None:
    example = TemplateExampleGenerator(load_template_generation_config(CONFIG_PATH)).generate()[0]
    variants = (
        GeneratedVariant(
            f"{example.street}, дом {example.house_number}: воды нет уже три дня 😱",
            "neutral",
            True,
        ),
        GeneratedVariant(
            f"По адресу {example.street}, дом {example.house_number}, нет холодной воды.",
            "natural",
            True,
        ),
    )

    results = TemplateParaphraseValidator().validate(example, variants)

    assert "EMOJI_FORBIDDEN" in results[0][1]
    assert "UNSUPPORTED_TIME" in results[0][1]
    assert results[1][1] == ()


def test_paraphrase_validator_respects_location_scope_and_negation() -> None:
    examples = TemplateExampleGenerator(load_template_generation_config(CONFIG_PATH)).generate()
    outdoor = next(example for example in examples if example.frame_id == "dangerous_tree")
    smoke = next(example for example in examples if example.frame_id == "smoke_without_fire")
    validator = TemplateParaphraseValidator()

    outdoor_results = validator.validate(
        outdoor,
        (
            GeneratedVariant(
                f"В доме {outdoor.house_number} на {outdoor.street} дерево нависло над тротуаром.",
                "natural",
                True,
            ),
            GeneratedVariant(
                f"У дома {outdoor.house_number} на {outdoor.street} дерево нависло над тротуаром.",
                "neutral",
                True,
            ),
        ),
    )
    smoke_results = validator.validate(
        smoke,
        (
            GeneratedVariant(
                f"{smoke.street}, дом {smoke.house_number}: пахнет дымом, открытого огня нет.",
                "neutral",
                True,
            ),
            GeneratedVariant(
                f"По адресу {smoke.street}, дом {smoke.house_number}, "
                "ощущается дым, огня не видно.",
                "natural",
                True,
            ),
        ),
    )

    assert "OUTDOOR_EVENT_PLACED_INSIDE_BUILDING" in outdoor_results[0][1]
    assert "OUTDOOR_EVENT_PLACED_INSIDE_BUILDING" not in outdoor_results[1][1]
    assert all("NEGATION_NOT_PRESERVED" not in errors for _, errors in smoke_results)


def test_paraphrase_validator_preserves_spark_negation_and_forbids_added_address() -> None:
    example = TemplateExampleGenerator(load_template_generation_config(CONFIG_PATH)).generate()[0]
    spark_example = replace(
        example,
        base_problem="нет электричества, щиток не искрит",
        text=f"{example.street}, дом {example.house_number}: щиток не искрит.",
        context_tags=("negated_danger",),
        danger_signals=(),
    )
    no_address_example = replace(
        example,
        base_problem="нет воды",
        text="У нас нет воды.",
        street="",
        house_number="",
        address_required=False,
        location_scope="NONE",
    )
    validator = TemplateParaphraseValidator()

    spark_results = validator.validate(
        spark_example,
        (
            GeneratedVariant(
                f"По адресу {example.street}, дом {example.house_number}, "
                "нет света, искрения в щитке нет.",
                "neutral",
                True,
            ),
            GeneratedVariant(
                f"В доме {example.house_number} на {example.street} отключился свет, "
                "щиток не искрит.",
                "natural",
                True,
            ),
        ),
    )
    no_address_results = validator.validate(
        no_address_example,
        (
            GeneratedVariant("Воды нет, адрес в сообщении отсутствует.", "neutral", False),
            GeneratedVariant("На Советской улице нет воды.", "natural", True),
        ),
    )

    assert all("NEGATION_NOT_PRESERVED" not in errors for _, errors in spark_results)
    assert "FORBIDDEN_ADDRESS_ADDED" not in no_address_results[0][1]
    assert "FORBIDDEN_ADDRESS_ADDED" in no_address_results[1][1]


def test_paraphrase_validator_rejects_inferred_scope_intensity_and_lost_repetition() -> None:
    example = TemplateExampleGenerator(load_template_generation_config(CONFIG_PATH)).generate()[0]
    validator = TemplateParaphraseValidator()
    none_scope = replace(example, location_scope="NONE")
    repeated = replace(example, context_tags=("repeated_user",))

    none_results = validator.validate(
        none_scope,
        (
            GeneratedVariant(
                f"У дома {example.house_number} на {example.street} есть проблема.",
                "neutral",
                True,
            ),
            GeneratedVariant(
                f"На {example.street}, {example.house_number} есть проблема.",
                "natural",
                True,
            ),
        ),
    )
    repeated_results = validator.validate(
        repeated,
        (
            GeneratedVariant(
                f"По адресу {example.street}, дом {example.house_number}, сильная проблема.",
                "neutral",
                True,
            ),
            GeneratedVariant(
                f"Снова сообщаю о проблеме по адресу {example.street}, дом {example.house_number}.",
                "natural",
                True,
            ),
        ),
    )

    assert "LOCATION_SCOPE_INFERRED" in none_results[0][1]
    assert "LOCATION_SCOPE_INFERRED" not in none_results[1][1]
    assert "UNSUPPORTED_INTENSITY" in repeated_results[0][1]
    assert "REPETITION_CONTEXT_NOT_PRESERVED" in repeated_results[0][1]
    assert "REPETITION_CONTEXT_NOT_PRESERVED" not in repeated_results[1][1]


def test_paraphrase_runner_is_resumable(tmp_path: Path) -> None:
    config = load_template_paraphrase_config(PARAPHRASE_CONFIG_PATH)
    example = TemplateExampleGenerator(load_template_generation_config(CONFIG_PATH)).generate()[0]
    client = FakeParaphraseClient()
    runner = TemplateParaphraseRunner(config=config, system_prompt="system", client=client)

    first = runner.execute((example,), tmp_path)
    second = runner.execute((example,), tmp_path)

    assert client.calls == 1
    assert first == second
    assert first["accepted_candidate_count"] == 2
    assert first["quarantined_candidate_count"] == 0
