from pathlib import Path

from maxsmartcity.ml.data.config import load_rule_baseline, load_taxonomy

CONFIG_DIR = Path("ml/configs")


def test_taxonomy_is_loaded_from_versioned_data() -> None:
    taxonomy = load_taxonomy(CONFIG_DIR / "taxonomy.v1.json")

    assert taxonomy.version == "city-incidents-draft-v1"
    assert "water" in taxonomy.category_ids
    assert len(taxonomy.category_ids) == len(taxonomy.categories)


def test_rule_baseline_is_disabled_for_automation() -> None:
    config = load_rule_baseline(CONFIG_DIR / "rule-baseline.v1.json")

    assert config.automation_enabled is False
    assert config.taxonomy_version == "city-incidents-draft-v1"
