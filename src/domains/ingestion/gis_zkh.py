"""Transform public GIS ЖКХ archives into the versioned ingestion JSON contract."""

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import tarfile
import zipfile
from collections.abc import Buffer, Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

from src.domains.ingestion.importer import normalize_house_number, normalize_street

SOURCE_CODE = "gis-zkh-public-pilot"
SOURCE_PAGE = "https://dom.gosuslugi.ru/#!/houses"

PILOT_HOUSES = (
    ("Брянск", "улица Евдокимова", "8"),
    ("Брянск", "улица Евдокимова", "10"),
    ("Бахчисарай", "улица Мира", "9"),
    ("Бахчисарай", "улица Мира", "3"),
)
PILOT_MEMBER_TERRITORIES = ("брянск", "крым")

HOUSE_ALIASES = {
    "external_id": (
        "Идентификационный код адреса дома в ГИС ЖКХ",
        "Уникальный номер дома",
        "Идентификатор дома",
        "house_id",
    ),
    "fias_id": (
        "Глобальный уникальный идентификатор дома по ФИАС",
        "Идентификатор ФИАС",
        "FIAS",
        "fias_id",
    ),
    "canonical_address": ("Адрес ОЖФ", "Адрес", "Адрес дома", "address"),
    "city": ("Город", "Населенный пункт", "city"),
    "street": ("Улица", "street"),
    "house_number": ("Номер дома", "Номер здания", "house_number"),
    "official_status": ("Состояние", "Статус", "status"),
    "management_method": ("Способ управления", "management_method"),
    "organization_id": ("Идентификатор организации", "organization_id"),
    "organization_name": (
        "Наименование организации, осуществляющей управление домом",
        "Наименование организации",
        "Управляющая организация",
        "organization_name",
    ),
    "inn": ("ИНН", "inn"),
    "ogrn": ("ОГРН организации, осуществляющей управление домом", "ОГРН", "ogrn"),
    "basis": ("Основание", "basis"),
    "period_from": ("Дата начала", "period_from"),
    "period_to": ("Дата окончания", "period_to"),
}


def _value(row: dict[str, str], aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        value = row.get(alias)
        if value and value.strip():
            return " ".join(value.split())
    return None


def _key(city: str, street: str, house_number: str) -> tuple[str, str, str]:
    return city.casefold(), normalize_street(street).casefold(), normalize_house_number(house_number)


PILOT_KEYS = {_key(*address): address for address in PILOT_HOUSES}


def _address_key(address: str) -> tuple[str, str, str] | None:
    compact = " ".join(address.casefold().replace(",", " ").split())
    for key, (city, street, number) in PILOT_KEYS.items():
        street_tail = normalize_street(street).removeprefix("улица ").casefold()
        pattern = (
            rf"\b{re.escape(city.casefold())}\b.*\b(?:ул\.?|улица)\s+{re.escape(street_tail)}\b"
            rf".*\b(?:д\.?|дом)\s*{re.escape(number)}(?![0-9а-я])"
        )
        if re.search(pattern, compact):
            return key
    return None


class _BinaryReadable(Protocol):
    def read(self, size: int = -1, /) -> bytes: ...


def _open_csv(stream: _BinaryReadable, member_name: str = "CSV") -> Iterator[dict[str, str]]:
    sample = stream.read(4096)
    for encoding in ("utf-8-sig", "utf-16", "cp1251"):
        try:
            text_sample = sample.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("CSV member has an unsupported text encoding")
    if "|" in text_sample:
        delimiter = "|"
    elif ";" in text_sample:
        delimiter = ";"
    else:
        return
    prefixed = io.BufferedReader(cast(Any, _PrefixedBinary(sample, stream)))
    yield from csv.DictReader(io.TextIOWrapper(prefixed, encoding=encoding), delimiter=delimiter)


class _PrefixedBinary(io.RawIOBase):
    def __init__(self, prefix: bytes, stream: _BinaryReadable) -> None:
        self._prefix = memoryview(prefix)
        self._stream = stream

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return False

    def readinto(self, buffer: Buffer) -> int:
        target = memoryview(buffer)
        if self._prefix:
            count = min(len(target), len(self._prefix))
            target[:count] = self._prefix[:count]
            self._prefix = self._prefix[count:]
            return count
        data = self._stream.read(len(target))
        if not data:
            return 0
        target[: len(data)] = data
        return len(data)


def iter_rows(archives: Iterable[Path]) -> Iterator[tuple[str, dict[str, str]]]:
    for archive in archives:
        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive) as bundle:
                for info in bundle.infolist():
                    if info.is_dir() or not info.filename.lower().endswith(".csv"):
                        continue
                    with bundle.open(info) as stream:
                        for row in _open_csv(stream, info.filename):
                            yield info.filename, row
        elif tarfile.is_tarfile(archive):
            with tarfile.open(archive, "r|gz") as bundle:
                for info in bundle:
                    if not info.isfile() or not info.name.lower().endswith(".csv"):
                        continue
                    if (
                        not any(territory in info.name.casefold() for territory in PILOT_MEMBER_TERRITORIES)
                        and info.name != "houses.csv"
                    ):
                        continue
                    stream = bundle.extractfile(info)
                    if stream is None:
                        continue
                    with stream:
                        for row in _open_csv(stream, info.name):
                            yield info.name, row
        else:
            with gzip.open(archive, "rb") as stream:
                for row in _open_csv(stream, archive.name):
                    yield archive.stem, row


def archive_manifest(archives: Iterable[Path], retrieved_at: datetime) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for archive in archives:
        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive) as bundle:
                members = [
                    {
                        "name": info.filename,
                        "format": Path(info.filename).suffix.lower().removeprefix("."),
                        "size": info.file_size,
                    }
                    for info in bundle.infolist()
                    if not info.is_dir()
                ]
        elif tarfile.is_tarfile(archive):
            with tarfile.open(archive, "r:gz") as bundle:
                members = [
                    {"name": info.name, "format": Path(info.name).suffix.removeprefix("."), "size": info.size}
                    for info in bundle.getmembers()
                    if info.isfile()
                ]
        else:
            members = [{"name": archive.stem, "format": "csv", "size": None}]
        records.append(
            {
                "archive_name": archive.name,
                "source_page": SOURCE_PAGE,
                "retrieved_at": retrieved_at.isoformat(),
                "sha256": _sha256(archive),
                "size": archive.stat().st_size,
                "members": members,
            }
        )
    return {
        "version": 1,
        "source": "GIS ЖКХ public registry",
        "territory_filter": ["Брянская область", "Республика Крым"],
        "address_filter": [
            {"city": city, "street": street, "house_number": number} for city, street, number in PILOT_HOUSES
        ],
        "available_ids": [
            "Идентификационный код адреса дома в ГИС ЖКХ",
            "Глобальный уникальный идентификатор дома по ФИАС",
            "ОГРН организации, осуществляющей управление домом",
        ],
        "archives": records,
    }


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def transform(archives: list[Path], retrieved_at: datetime) -> dict[str, Any]:
    found: dict[tuple[str, str, str], dict[str, Any]] = {}
    organizations: dict[str, dict[str, Any]] = {}
    links: list[dict[str, Any]] = []
    for member, raw in iter_rows(archives):
        canonical = _value(raw, HOUSE_ALIASES["canonical_address"])
        city = _value(raw, HOUSE_ALIASES["city"])
        street = _value(raw, HOUSE_ALIASES["street"])
        number = _value(raw, HOUSE_ALIASES["house_number"])
        address_key = (
            _key(city, street, number)
            if city is not None and street is not None and number is not None
            else None
        )
        if address_key not in PILOT_KEYS and canonical:
            address_key = _address_key(canonical)
        if address_key not in PILOT_KEYS or address_key in found:
            continue
        external_id = _value(raw, HOUSE_ALIASES["external_id"])
        if not external_id:
            continue
        house_key = f"gis-zkh:{external_id}"
        provenance = {"archive_member": member}
        found[address_key] = {
            "key": house_key,
            "city": PILOT_KEYS[address_key][0],
            "street": PILOT_KEYS[address_key][1],
            "house_number": PILOT_KEYS[address_key][2],
            "external_id": external_id,
            "fias_id": _value(raw, HOUSE_ALIASES["fias_id"]),
            "formatted": canonical,
            "canonical_address": canonical,
            "official_status": _value(raw, HOUSE_ALIASES["official_status"]),
            "management_method": _value(raw, HOUSE_ALIASES["management_method"]),
            "provenance": provenance,
        }
        org_id = _value(raw, HOUSE_ALIASES["organization_id"])
        org_name = _value(raw, HOUSE_ALIASES["organization_name"])
        ogrn = _value(raw, HOUSE_ALIASES["ogrn"])
        if (org_id or ogrn) and org_name:
            org_key = f"gis-zkh-org:{org_id or f'ogrn:{ogrn}'}"
            organizations.setdefault(
                org_key,
                {
                    "key": org_key,
                    "name": org_name,
                    "type": "MANAGING_COMPANY",
                    "external_id": org_id,
                    "inn": _value(raw, HOUSE_ALIASES["inn"]),
                    "ogrn": ogrn,
                    "provenance": provenance,
                },
            )
            links.append(
                {
                    "house_key": house_key,
                    "organization_key": org_key,
                    "relationship": "MANAGES",
                    "basis": _value(raw, HOUSE_ALIASES["basis"]),
                    "period_from": _value(raw, HOUSE_ALIASES["period_from"]),
                    "period_to": _value(raw, HOUSE_ALIASES["period_to"]),
                    "provenance": provenance,
                }
            )
        if len(found) == len(PILOT_KEYS):
            break
    archive_names = [archive.name for archive in archives]
    return {
        "version": 1,
        "source": {
            "code": SOURCE_CODE,
            "url": SOURCE_PAGE,
            "data_kind": "REAL",
            "retrieved_at": retrieved_at.isoformat(),
        },
        "houses": list(found.values()),
        "organizations": list(organizations.values()),
        "links": links,
        "not_found": [
            {
                "city": city,
                "street": street,
                "house_number": number,
                "status": "NOT_FOUND",
                "searched_archives": archive_names,
            }
            for key, (city, street, number) in PILOT_KEYS.items()
            if key not in found
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Transform manually downloaded GIS ЖКХ ZIP exports")
    parser.add_argument("--archive", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--retrieved-at", type=datetime.fromisoformat, default=datetime.now(UTC))
    args = parser.parse_args()
    for archive in args.archive:
        if not archive.is_file():
            parser.error(f"archive does not exist: {archive}")
    dataset = json.dumps(transform(args.archive, args.retrieved_at), ensure_ascii=False, indent=2) + "\n"
    manifest = (
        json.dumps(archive_manifest(args.archive, args.retrieved_at), ensure_ascii=False, indent=2) + "\n"
    )
    args.output.write_text(dataset, encoding="utf-8")
    args.manifest.write_text(manifest, encoding="utf-8")


if __name__ == "__main__":
    main()
