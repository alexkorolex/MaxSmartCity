import gzip
import json
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path

from src.domains.ingestion.gis_zkh import archive_manifest, transform

FIXTURE = Path(__file__).parent / "fixtures" / "gis_zkh_public_houses.csv"
RETRIEVED_AT = datetime.fromisoformat("2026-09-22T20:35:00+03:00")


def official_zip(tmp_path: Path) -> Path:
    archive = tmp_path / "official-houses.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(FIXTURE, "houses.csv")
    return archive


def official_gzip(tmp_path: Path) -> Path:
    archive = tmp_path / "official-houses.csv.gz"
    with gzip.open(archive, "wb") as stream:
        stream.write(FIXTURE.read_bytes())
    return archive


def official_tar_gzip(tmp_path: Path) -> Path:
    archive = tmp_path / "official-houses.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(FIXTURE, arcname="houses.csv")
    return archive


def test_actual_public_export_fixture_is_filtered_and_normalized(tmp_path: Path) -> None:
    dataset = transform([official_zip(tmp_path)], RETRIEVED_AT)
    assert dataset["source"] == {
        "code": "gis-zkh-public-pilot",
        "url": "https://dom.gosuslugi.ru/#!/houses",
        "data_kind": "REAL",
        "retrieved_at": "2026-09-22T20:35:00+03:00",
    }
    assert [(row["street"], row["house_number"]) for row in dataset["houses"]] == [
        ("улица Евдокимова", "8"),
        ("улица Евдокимова", "10"),
        ("улица Мира", "9"),
        ("улица Мира", "3"),
    ]
    assert {row["key"] for row in dataset["organizations"]} == {
        "gis-zkh-org:ogrn:1023200000001",
        "gis-zkh-org:ogrn:1149100000001",
    }
    assert len(dataset["links"]) == 3
    assert not dataset["not_found"]
    assert dataset["houses"][0]["provenance"] == {"archive_member": "houses.csv"}


def test_manifest_has_archive_hash_member_format_and_size(tmp_path: Path) -> None:
    manifest = archive_manifest([official_zip(tmp_path)], RETRIEVED_AT)
    item = manifest["archives"][0]
    assert len(item["sha256"]) == 64
    assert item["source_page"] == "https://dom.gosuslugi.ru/#!/houses"
    assert manifest["territory_filter"] == ["Брянская область", "Республика Крым"]
    assert item["members"] == [{"name": "houses.csv", "format": "csv", "size": FIXTURE.stat().st_size}]
    json.dumps(manifest, ensure_ascii=False)


def test_public_gzip_export_is_read_without_extracting_it(tmp_path: Path) -> None:
    dataset = transform([official_gzip(tmp_path)], RETRIEVED_AT)
    assert len(dataset["houses"]) == 4
    assert dataset["houses"][0]["provenance"] == {"archive_member": "official-houses.csv"}


def test_public_tar_gzip_export_is_read_without_extracting_it(tmp_path: Path) -> None:
    dataset = transform([official_tar_gzip(tmp_path)], RETRIEVED_AT)
    assert len(dataset["houses"]) == 4
    assert not dataset["not_found"]
