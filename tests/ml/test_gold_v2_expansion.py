from pathlib import Path

from maxsmartcity.ml.data.gold.expansion import ExpansionConfig, GoldV2ExpansionGenerator


def test_gold_v2_expansion_is_balanced_deterministic_and_grounded() -> None:
    config = ExpansionConfig.load(Path("ml/configs/gold-v2-expansion.json"))
    generator = GoldV2ExpansionGenerator(config)

    frames, examples = generator.generate()

    assert generator.generate() == (frames, examples)
    assert len(frames) == 80
    assert len(examples) == 160
    assert len({frame.scenario_id for frame in frames}) == 80
    assert all(sum(example.frame_id == frame.scenario_id for example in examples) == 2 for frame in frames)
    assert all(
        frame.house_number in example.text and frame.street in example.text
        for frame in frames
        for example in examples
        if example.frame_id == frame.scenario_id and frame.address_required
    )
    assert all(
        not example.street and not example.house_number
        for example in examples
        if not example.address_required
    )
