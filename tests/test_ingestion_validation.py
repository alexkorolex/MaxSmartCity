import json
from pathlib import Path

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

from src.domains.ingestion.importer import (
    MAX_FILE_BYTES,
    read_dataset,
    validate_house,
    validate_link,
    validate_organization,
)
from src.domains.ingestion.models import house_source, organization_source


def dataset() -> dict[str, object]:
    return {
        "version": 1,
        "source": {
            "code": " pilot ",
            "url": " https://example.test/pilot ",
            "data_kind": "DEMO",
            "retrieved_at": " 2026-09-22T12:00:00+03:00 ",
        },
        "houses": [],
        "organizations": [],
        "links": [],
    }


def write(tmp_path: Path, content: dict[str, object] | str) -> Path:
    path = tmp_path / "dataset.json"
    path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
    return path


def test_file_metadata_is_validated_and_normalized(tmp_path: Path) -> None:
    content, digest = read_dataset(write(tmp_path, dataset()))
    assert content["source"] == {
        "code": "pilot",
        "url": "https://example.test/pilot",
        "data_kind": "DEMO",
        "retrieved_at": "2026-09-22T12:00:00+03:00",
    }
    assert len(digest) == 64


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"version": 2}, "version 1"),
        ({"source": None}, "source must"),
        ({"houses": None}, "houses must"),
        ({"organizations": None}, "organizations must"),
        ({"links": None}, "links must"),
    ],
)
def test_invalid_envelope_is_rejected(tmp_path: Path, change: dict[str, object], message: str) -> None:
    content = dataset()
    content.update(change)
    with pytest.raises(ValueError, match=message):
        read_dataset(write(tmp_path, content))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("code", ""),
        ("data_kind", "UNKNOWN"),
        ("retrieved_at", "2026-09-22T12:00:00"),
        ("retrieved_at", "not-a-date"),
        ("url", 123),
    ],
)
def test_invalid_source_metadata_is_rejected(tmp_path: Path, field: str, value: object) -> None:
    content = dataset()
    source = content["source"]
    assert isinstance(source, dict)
    source[field] = value
    with pytest.raises(ValueError):
        read_dataset(write(tmp_path, content))


@pytest.mark.parametrize("content", ['{"version":1,"version":1}', '{"value":NaN}'])
def test_nonstandard_or_ambiguous_json_is_rejected(tmp_path: Path, content: str) -> None:
    with pytest.raises(ValueError):
        read_dataset(write(tmp_path, content))


def test_non_json_and_oversize_files_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "dataset.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match=r"\.json"):
        read_dataset(path)
    path = tmp_path / "dataset.json"
    path.write_bytes(b" " * (MAX_FILE_BYTES + 1))
    with pytest.raises(ValueError, match="5 MiB"):
        read_dataset(path)


def test_house_coordinates_are_optional_but_validated_as_a_pair() -> None:
    row = {"key": "one", "city": " Город ", "street": " улица  Мира ", "house_number": "1"}
    assert validate_house(row)["point"] is None
    assert validate_house(row)["street"] == "улица Мира"
    assert validate_house({**row, "latitude": 53.2, "longitude": 34.3})["point"] == (
        "SRID=4326;POINT(34.3 53.2)"
    )
    for values in (
        {"latitude": 53.2},
        {"latitude": 91, "longitude": 34.3},
        {"latitude": True, "longitude": 34.3},
        {"latitude": 53.2, "longitude": -181},
    ):
        with pytest.raises(ValueError):
            validate_house({**row, **values})


def test_required_row_fields_and_link_keys_are_validated() -> None:
    with pytest.raises(ValueError, match="city"):
        validate_house({"key": "one", "street": "Мира", "house_number": "1"})
    with pytest.raises(ValueError, match="name"):
        validate_organization({"key": "one", "type": "MANAGING_COMPANY"})
    with pytest.raises(ValueError, match="organization_key"):
        validate_link({"house_key": "one", "relationship": "MANAGES"})


def test_gis_zkh_fields_and_deterministic_address_aliases_are_validated() -> None:
    house = validate_house(
        {
            "key": "official-1",
            "city": "Брянск",
            "street": "ул. Евдокимова",
            "house_number": "8 корпус 2",
            "fias_id": "fias-1",
            "official_status": "Исправен",
            "management_method": "Управляющая организация",
            "provenance": {"archive_member": "houses.csv"},
        }
    )
    assert house["street"] == "улица Евдокимова"
    assert house["house_number"] == "8 КОРП. 2"
    assert house["fias_id"] == "fias-1"
    assert (
        validate_organization(
            {
                "key": "org",
                "name": "УК",
                "type": "MANAGING_COMPANY",
                "inn": "3201000001",
                "ogrn": "1023200000001",
            }
        )["inn"]
        == "3201000001"
    )
    with pytest.raises(ValueError, match="inn"):
        validate_organization({"key": "org", "name": "УК", "type": "MANAGING_COMPANY", "inn": "by-name"})
    with pytest.raises(ValueError, match="period_to"):
        validate_link(
            {
                "house_key": "house",
                "organization_key": "org",
                "relationship": "MANAGES",
                "period_from": "2026-02-01",
                "period_to": "2026-01-01",
            }
        )


def test_gis_zkh_partial_indexes_match_the_migration() -> None:
    indexes = {
        index.name: str(CreateIndex(index).compile(dialect=postgresql.dialect()))
        for index in house_source.indexes
    }
    indexes.update(
        {
            index.name: str(CreateIndex(index).compile(dialect=postgresql.dialect()))
            for index in organization_source.indexes
        }
    )
    assert indexes["ix_house_source_fias_id"] == (
        "CREATE INDEX ix_house_source_fias_id ON ingestion.house_source (fias_id) WHERE fias_id IS NOT NULL"
    )
    assert indexes["ix_organization_source_inn"] == (
        "CREATE INDEX ix_organization_source_inn ON ingestion.organization_source (inn) WHERE inn IS NOT NULL"
    )
