import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from maxsmartcity.ml.data.llm.config import load_llm_generation_config
from maxsmartcity.ml.data.llm.input import load_scenario_facts
from maxsmartcity.ml.data.llm.models import (
    GeneratedVariant,
    GenerationPass,
    GenerationResponse,
    GenerationUsage,
    ScenarioFact,
)
from maxsmartcity.ml.data.llm.prompt import build_messages, load_system_prompt
from maxsmartcity.ml.data.llm.review import build_review_rows, build_review_summary
from maxsmartcity.ml.data.llm.runner import LlmGenerationRunner
from maxsmartcity.ml.data.llm.selection import (
    build_selection_manifest,
    load_selection_config,
    load_selection_ids,
    select_facts,
    write_selection_manifest,
)
from maxsmartcity.ml.data.llm.validator import GeneratedVariantValidator

ROOT = Path(__file__).parents[2]
CONFIG = load_llm_generation_config(ROOT / "ml/configs/llm-augmentation.v2.json")
PROMPT = load_system_prompt(ROOT / CONFIG.prompt_file)
SELECTION_CONFIG = load_selection_config(ROOT / "ml/configs/llm-selection.v1.json")


class FakeClient:
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
        del messages, temperature, top_p, max_output_tokens
        self.calls += 1
        count = response_schema["schema"]["properties"]["variants"]["minItems"]
        return GenerationResponse(
            response_id="response-1",
            model=model,
            scenario_spec_id="FACT-1",
            variants=tuple(
                GeneratedVariant(
                    text=f"На улице Ленина, дом 12 нет холодной воды, вариант {index}",
                    style_id="neutral",
                    address_included=True,
                )
                for index in range(count)
            ),
            usage=GenerationUsage(100, 50, 150),
        )


def make_fact() -> ScenarioFact:
    return ScenarioFact(
        scenario_spec_id="FACT-1",
        taxonomy_version="taxonomy-v1",
        category_ids=("water",),
        subcategory_id="no_water",
        problem="нет холодной воды",
        object_type="residential_building",
        severity="medium",
        organization_type="WATER_UTILITY",
        street="улица Ленина",
        house_number="12",
        source_dataset_id="test-source",
        source_attributes=(),
        context_tags=(),
        danger_signals=(),
        needs_clarification=False,
        ambiguity=False,
    )


def test_config_and_canonical_input_define_safe_pilot() -> None:
    facts = load_scenario_facts(ROOT / "ml/data/external/canonical/v1/scenarios.jsonl")
    ids = {fact.scenario_spec_id for fact in facts}

    assert CONFIG.model == "mistral-small-3.2-24b-instruct"
    assert set(CONFIG.pilot_scenario_ids) <= ids
    assert len(CONFIG.passes) == 3


def test_main_batch_selection_is_balanced_and_reproducible(tmp_path: Path) -> None:
    canonical_path = ROOT / "ml/data/external/canonical/v1/scenarios.jsonl"
    facts = load_scenario_facts(canonical_path)

    selected = select_facts(facts, SELECTION_CONFIG)
    repeated = select_facts(tuple(reversed(facts)), SELECTION_CONFIG)
    source_counts = Counter(fact.source_dataset_id for fact in selected)
    curated_ids = {
        fact.scenario_spec_id for fact in facts if fact.source_dataset_id == "ml-data-curated-facts"
    }

    assert len(selected) == 60
    assert source_counts == {
        "bmc-synthetic-complaints": 20,
        "ml-data-curated-facts": 20,
        "sf311-recent-cases": 20,
    }
    expected_curated_ids = curated_ids - set(SELECTION_CONFIG.exclude_scenario_ids)
    assert expected_curated_ids <= {fact.scenario_spec_id for fact in selected}
    assert not set(SELECTION_CONFIG.exclude_scenario_ids) & {
        fact.scenario_spec_id for fact in selected
    }
    assert [fact.scenario_spec_id for fact in selected] == [
        fact.scenario_spec_id for fact in repeated
    ]

    manifest = build_selection_manifest(
        selected,
        config=SELECTION_CONFIG,
        canonical_path=canonical_path,
    )
    output = tmp_path / "selection.json"
    write_selection_manifest(output, manifest)

    assert manifest["scenario_count"] == 60
    assert load_selection_ids(output) == tuple(manifest["scenario_ids"])


def test_prompt_contains_locked_fact_but_not_model_owned_labels() -> None:
    generation_pass = GenerationPass("test", 0.25, 1, ("neutral",), ("*",))

    messages = build_messages(PROMPT, make_fact(), generation_pass)
    task = json.loads(messages[1]["content"])

    assert task["locked_fact"]["problem"] == "нет холодной воды"
    assert task["location"]["requirement"] == "REQUIRED"
    assert "category_ids" not in task["locked_fact"]
    assert "object_type" not in task["locked_fact"]
    assert "severity" not in task["locked_fact"]
    assert "organization_type" not in task["locked_fact"]
    assert task["scenario_spec_id"] == "FACT-1"


def test_validator_accepts_grounded_address_and_rejects_source_leak() -> None:
    generation_pass = GenerationPass("test", 0.25, 2, ("neutral",), ("*",))
    validator = GeneratedVariantValidator(CONFIG)

    results = validator.validate(
        make_fact(),
        generation_pass,
        (
            GeneratedVariant("На улице Ленина, дом 12 нет воды", "neutral", True),
            GeneratedVariant(
                "В SF311 написано, что на улице Ленина, дом 12 нет воды",
                "neutral",
                True,
            ),
        ),
    )

    assert results[0].accepted is True
    assert "FORBIDDEN_SOURCE_TERM" in results[1].errors


def test_validator_recognizes_naberezhnaya_as_a_street_name() -> None:
    fact = replace(make_fact(), street="Набережная улица", house_number="46")
    generation_pass = GenerationPass("test", 0.25, 1, ("neutral",), ("*",))

    result = GeneratedVariantValidator(CONFIG).validate(
        fact,
        generation_pass,
        (GeneratedVariant("Набережная улица, дом 46: нет воды", "neutral", True),),
    )[0]

    assert "ADDRESS_FLAG_MISMATCH" not in result.errors
    assert "REQUIRED_ADDRESS_MISSING" not in result.errors


def test_validator_accepts_common_street_abbreviation_with_exact_house() -> None:
    fact = replace(make_fact(), street="Советская улица", house_number="168")
    generation_pass = GenerationPass("test", 0.25, 1, ("typo",), ("*",))

    result = GeneratedVariantValidator(CONFIG).validate(
        fact,
        generation_pass,
        (GeneratedVariant("На сов. ул. 168 проблема с домом", "typo", True),),
    )[0]

    assert "ADDRESS_FLAG_MISMATCH" not in result.errors
    assert "REQUIRED_ADDRESS_MISSING" not in result.errors


def test_validator_recognizes_inflected_exposed_wire_signal() -> None:
    fact = replace(make_fact(), danger_signals=("EXPOSED_WIRE",))
    generation_pass = GenerationPass("test", 0.25, 1, ("short",), ("*",))

    result = GeneratedVariantValidator(CONFIG).validate(
        fact,
        generation_pass,
        (GeneratedVariant("Ленина 12: провод оголился", "short", True),),
    )[0]

    assert "DANGER_SIGNAL_NOT_LEXICALIZED" not in result.errors


def test_clarification_fact_forbids_invented_address() -> None:
    fact = replace(make_fact(), needs_clarification=True)

    assert fact.address_requirement == "FORBIDDEN"


def test_validator_requires_both_parts_of_combined_danger() -> None:
    fact = replace(make_fact(), danger_signals=("WATER_NEAR_ELECTRICITY",))
    generation_pass = GenerationPass("test", 0.25, 1, ("neutral",), ("*",))

    result = GeneratedVariantValidator(CONFIG).validate(
        fact,
        generation_pass,
        (GeneratedVariant("На улице Ленина, дом 12 течёт вода", "neutral", True),),
    )[0]

    assert "DANGER_SIGNAL_NOT_LEXICALIZED" in result.errors


def test_validator_preserves_explicitly_negated_danger() -> None:
    fact = replace(make_fact(), context_tags=("negated_danger",))
    generation_pass = GenerationPass("test", 0.25, 1, ("neutral",), ("*",))
    validator = GeneratedVariantValidator(CONFIG)

    missing = validator.validate(
        fact,
        generation_pass,
        (GeneratedVariant("На улице Ленина, дом 12 нет света", "neutral", True),),
    )[0]
    preserved = validator.validate(
        fact,
        generation_pass,
        (GeneratedVariant("На улице Ленина, дом 12 нет света, щиток не искрит", "neutral", True),),
    )[0]

    assert "NEGATED_DANGER_NOT_PRESERVED" in missing.errors
    assert "NEGATED_DANGER_NOT_PRESERVED" not in preserved.errors


def test_validator_checks_machine_verifiable_style_claims() -> None:
    generation_pass = GenerationPass(
        "test",
        0.9,
        3,
        ("caps", "emoji", "self_correction"),
        ("*",),
    )

    results = GeneratedVariantValidator(CONFIG).validate(
        make_fact(),
        generation_pass,
        (
            GeneratedVariant("На улице Ленина, дом 12 нет воды", "caps", True),
            GeneratedVariant("Улица Ленина, дом 12: нет воды", "emoji", True),
            GeneratedVariant("Улица Ленина, дом 12: нет воды, ой!", "self_correction", True),
        ),
    )

    assert all("STYLE_CONSTRAINT_NOT_MET" in result.errors for result in results)


def test_runner_resumes_without_repeating_api_calls(tmp_path: Path) -> None:
    generation_pass = GenerationPass("test", 0.25, 3, ("neutral",), ("*",))
    config = replace(CONFIG, passes=(generation_pass,))
    client = FakeClient()
    runner = LlmGenerationRunner(config=config, system_prompt=PROMPT, client=client)
    tasks = runner.plan((make_fact(),))

    first = runner.execute(tasks, tmp_path)
    second = runner.execute(tasks, tmp_path)

    assert client.calls == 1
    assert first == second
    assert first["accepted_candidate_count"] == 3
    assert first["quarantined_candidate_count"] == 0
    assert first["estimated_cost_rub"] > 0


def test_runner_does_not_resume_response_from_another_model(tmp_path: Path) -> None:
    generation_pass = GenerationPass("test", 0.25, 1, ("neutral",), ("*",))
    first_client = FakeClient()
    first_runner = LlmGenerationRunner(
        config=replace(CONFIG, passes=(generation_pass,), model="model-a"),
        system_prompt=PROMPT,
        client=first_client,
    )
    tasks = first_runner.plan((make_fact(),))
    first_runner.execute(tasks, tmp_path)

    second_client = FakeClient()
    second_runner = LlmGenerationRunner(
        config=replace(CONFIG, passes=(generation_pass,), model="model-b"),
        system_prompt=PROMPT,
        client=second_client,
    )
    second_runner.execute(tasks, tmp_path)

    assert first_client.calls == 1
    assert second_client.calls == 1


def test_review_queue_joins_candidate_with_locked_fact() -> None:
    candidate = {
        "candidate_id": "CANDIDATE-1",
        "scenario_spec_id": "FACT-1",
        "text": "На улице Ленина, дом 12 нет воды",
        "style_id": "neutral",
        "generation": {"pass_id": "controlled"},
    }

    rows = build_review_rows((candidate,), (make_fact(),))
    summary = build_review_summary(rows)

    assert rows[0]["locked_problem"] == "нет холодной воды"
    assert rows[0]["generated_text"] == candidate["text"]
    assert rows[0]["review_decision"] == ""
    assert summary["candidate_count"] == 1
    assert summary["scenario_count"] == 1
