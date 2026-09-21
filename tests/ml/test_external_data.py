import json
from dataclasses import replace
from pathlib import Path

import pytest

from maxsmartcity.ml.data.config import load_taxonomy
from maxsmartcity.ml.data.external.builder import ExternalScenarioBuilder
from maxsmartcity.ml.data.external.config import load_external_build_config
from maxsmartcity.ml.data.external.importers import BmcCsvImporter, Sf311CsvImporter
from maxsmartcity.ml.data.external.mapping import load_external_mapping
from maxsmartcity.ml.data.external.models import BmcRecord, Sf311Record
from maxsmartcity.ml.data.external.writer import ExternalScenarioWriter

ROOT = Path(__file__).parents[2]
CONFIG = load_external_build_config(ROOT / "ml/configs/external-scenarios.v1.json")
TAXONOMY = load_taxonomy(ROOT / "ml/configs/taxonomy.v1.json")
SF_MAPPING = load_external_mapping(ROOT / "ml/data/external/mappings/sf311-taxonomy.v1.json")
BMC_MAPPING = load_external_mapping(ROOT / "ml/data/external/mappings/bmc-taxonomy.v1.json")


def test_sf311_importer_reads_required_fields(tmp_path: Path) -> None:
    source = tmp_path / "sf311.csv"
    source.write_text(
        "CASE ID,CATEGORY,TYPE,DETAILS,AGENCY\n42,Street Defect,pothole,deep_hole,Public Works\n",
        encoding="utf-8",
    )

    assert tuple(Sf311CsvImporter().read(source)) == (
        Sf311Record("42", "Street Defect", "pothole", "deep_hole", "Public Works"),
    )


def test_bmc_importer_streams_rows(tmp_path: Path) -> None:
    source = tmp_path / "bmc.csv"
    source.write_text(
        "complaint_id,complaint_category,department_assigned,severity,property_type,"
        "complaint_channel\n"
        "B-1,Pothole / Road Damage,Roads,High,Street,App\n",
        encoding="utf-8",
    )

    records = BmcCsvImporter().read(source)

    assert iter(records) is records
    assert tuple(records) == (BmcRecord("B-1", "Pothole / Road Damage", "Roads", "High", "Street", "App"),)


def test_mapping_prefers_more_specific_rule() -> None:
    result = SF_MAPPING.resolve(
        {
            "category": "Request for City Services",
            "type": "public_utilities_commission",
            "details": "water",
        }
    )

    assert result is not None
    assert result.rule_id == "sf311-public-utilities-water"
    assert result.category_ids == ("water",)


def test_sf311_container_types_keep_distinct_problem_meanings() -> None:
    overflowing = SF_MAPPING.resolve(
        {
            "category": "Litter Receptacle Maintenance",
            "type": "debris_box_maintenance_overflowing",
            "details": "",
        }
    )
    left_out = SF_MAPPING.resolve(
        {
            "category": "Litter Receptacle Maintenance",
            "type": "toters_left_out_24x7",
            "details": "",
        }
    )

    assert overflowing is not None
    assert left_out is not None
    assert overflowing.problem == "уличный контейнер для мусора переполнен"
    assert left_out.problem == "мусорный контейнер оставлен на улице вне установленного времени вывоза"


def test_builder_is_deterministic_and_replaces_external_locations() -> None:
    config = replace(CONFIG, sf311_limit=1, bmc_limit=1, curated=())
    builder = ExternalScenarioBuilder(config, TAXONOMY, SF_MAPPING, BMC_MAPPING)
    sf_records = (Sf311Record("SF-1", "Street Defect", "pothole", "deep", "Public Works"),)
    bmc_records = (BmcRecord("BMC-1", "Water Supply Disruption", "Water", "High", "House", "App"),)

    first = builder.build(iter(sf_records), iter(bmc_records))
    second = builder.build(iter(sf_records), iter(bmc_records))

    assert first == second
    assert all(item.location.synthetic for item in first)
    assert all(item.location.city_id == "demo-city" for item in first)
    assert all(item.location.street in config.streets for item in first)


def test_writer_creates_stable_manifest(tmp_path: Path) -> None:
    config = replace(CONFIG, sf311_limit=1, bmc_limit=1, curated=())
    builder = ExternalScenarioBuilder(config, TAXONOMY, SF_MAPPING, BMC_MAPPING)
    scenarios = builder.build(
        [Sf311Record("SF-1", "Street Defect", "pothole", "deep", "Public Works")],
        [BmcRecord("BMC-1", "Solid Waste / Garbage", "Waste", "Low", "Road", "App")],
    )

    manifest = ExternalScenarioWriter().write(scenarios, tmp_path, config=config)
    payloads = [
        json.loads(line) for line in (tmp_path / "scenarios.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert manifest["record_count"] == 2
    assert len(manifest["sha256"]) == 64
    assert len(payloads) == 2
    assert all(item["location"]["synthetic"] is True for item in payloads)


def test_importer_rejects_missing_columns(tmp_path: Path) -> None:
    source = tmp_path / "broken.csv"
    source.write_text("CASE ID,CATEGORY\n1,Sewer\n", encoding="utf-8")

    with pytest.raises(ValueError, match="misses required columns"):
        tuple(Sf311CsvImporter().read(source))
