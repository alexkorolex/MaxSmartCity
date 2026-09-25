import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from src.database.config import DatabaseSettings

MAX_FILE_BYTES = 5 * 1024 * 1024


def _normalized_spaces(value: str) -> str:
    return " ".join(value.split())


def _normalize_street(value: str) -> str:
    normalized = _normalized_spaces(value)
    match = re.fullmatch(r"(?i:ул\.?)\s+(.+)", normalized)
    if match:
        return f"улица {match.group(1)}"
    return normalized


def _normalize_house_number(value: str) -> str:
    normalized = _normalized_spaces(value).upper()
    normalized = re.sub(r"(?i)\bКОРПУС\.?\s*", "КОРП. ", normalized)
    normalized = re.sub(r"(?i)\bК\.?\s*(?=\d)", "КОРП. ", normalized)
    return _normalized_spaces(normalized)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _invalid_number(value: str) -> None:
    raise ValueError(f"invalid JSON number: {value}")


def _db_safe_string(value: str) -> str:
    return value.replace("\x00", "\\0").encode("utf-8", errors="replace").decode("utf-8")


def _db_safe_json(value: object) -> object:
    if isinstance(value, str):
        return _db_safe_string(value)
    if isinstance(value, list):
        return [_db_safe_json(item) for item in value]
    if isinstance(value, dict):
        return {_db_safe_string(str(key)): _db_safe_json(item) for key, item in value.items()}
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def required_string(row: dict[str, Any], field: str, maximum: int) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{field} must be a nonempty string of at most {maximum} characters")
    return _normalized_spaces(value)


def optional_string(row: dict[str, Any], field: str, maximum: int) -> str | None:
    value = row.get(field)
    if value is None:
        return None
    return required_string(row, field, maximum)


def _normalize_phone(value: str) -> str:
    normalized = re.sub(r"[\s()\-.]", "", value)
    if normalized.startswith("8") and len(normalized) == 11:
        normalized = "+7" + normalized[1:]
    if not re.fullmatch(r"\+[1-9]\d{9,14}", normalized):
        raise ValueError("phone must be an international phone number")
    return normalized


def optional_phones(row: dict[str, Any]) -> list[str]:
    value = row.get("phones")
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 10:
        raise ValueError("phones must be an array of at most 10 phone numbers")
    normalized: list[str] = []
    for phone in value:
        if not isinstance(phone, str):
            raise ValueError("phone must be a string")
        item = _normalize_phone(phone)
        if item not in normalized:
            normalized.append(item)
    return normalized


def optional_email(row: dict[str, Any]) -> str | None:
    value = optional_string(row, "email", 320)
    if value is None:
        return None
    value = value.casefold()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise ValueError("email must be a valid address")
    return value


def optional_website(row: dict[str, Any]) -> str | None:
    value = optional_string(row, "website", 2048)
    if value is None:
        return None
    parsed = urlsplit(value)
    if (
        any(character.isspace() for character in value)
        or parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("website must be an HTTP(S) URL without credentials")
    return value


def read_dataset(path: Path, *, max_bytes: int | None = MAX_FILE_BYTES) -> tuple[dict[str, Any], str]:
    """``max_bytes=None`` lifts the size guard - only for the batched bulk importer
    (``src.domains.ingestion.bulk``), which never loads a whole large file in one run."""
    if path.suffix.lower() != ".json":
        raise ValueError("input must be a .json file")
    if max_bytes is not None and path.stat().st_size > max_bytes:
        raise ValueError(f"input exceeds {max_bytes // (1024 * 1024)} MiB")
    content = path.read_bytes()
    dataset = json.loads(
        content.decode("utf-8-sig"),
        object_pairs_hook=_unique_object,
        parse_constant=_invalid_number,
    )
    if not isinstance(dataset, dict) or dataset.get("version") != 1:
        raise ValueError("dataset must be a version 1 JSON object")
    source = dataset.get("source")
    if not isinstance(source, dict):
        raise ValueError("source must be an object")
    source["code"] = required_string(source, "code", 128)
    if source.get("data_kind") not in ("REAL", "DEMO"):
        raise ValueError("source.data_kind must be REAL or DEMO")
    source["url"] = optional_string(source, "url", 2048)
    try:
        retrieved_at = datetime.fromisoformat(required_string(source, "retrieved_at", 64))
    except ValueError as exc:
        raise ValueError("source.retrieved_at must be an ISO 8601 timestamp") from exc
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
        raise ValueError("source.retrieved_at must contain a time zone")
    source["retrieved_at"] = retrieved_at.isoformat()
    for key in ("houses", "organizations", "links"):
        if not isinstance(dataset.get(key), list):
            raise ValueError(f"{key} must be an array")
    return dataset, hashlib.sha256(content).hexdigest()


def validate_house(row: object) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError("house must be an object")
    fields: dict[str, Any] = {
        key: required_string(row, key, limit)
        for key, limit in (("key", 255), ("city", 255), ("street", 255), ("house_number", 64))
    }
    fields["formatted"] = optional_string(row, "formatted", 1000) or (
        f"{fields['city']}, {fields['street']}, д. {fields['house_number']}"
    )
    fields["external_id"] = optional_string(row, "external_id", 255)
    fields["fias_id"] = optional_string(row, "fias_id", 255)
    fields["official_status"] = optional_string(row, "official_status", 128)
    fields["management_method"] = optional_string(row, "management_method", 128)
    fields["canonical_address"] = optional_string(row, "canonical_address", 1000)
    fields["provenance"] = optional_object(row, "provenance")
    fields["street"] = _normalize_street(fields["street"])
    fields["house_number"] = _normalize_house_number(fields["house_number"])
    lat, lon = row.get("latitude"), row.get("longitude")
    if (lat is None) != (lon is None):
        raise ValueError("latitude and longitude must be supplied together")
    if lat is not None:
        if (
            isinstance(lat, bool)
            or isinstance(lon, bool)
            or not isinstance(lat, (int, float))
            or not isinstance(lon, (int, float))
            or not (-90 <= lat <= 90 and -180 <= lon <= 180)
        ):
            raise ValueError("invalid latitude or longitude")
        fields["point"] = f"SRID=4326;POINT({lon} {lat})"
    else:
        fields["point"] = None
    return fields


def validate_organization(row: object) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError("organization must be an object")
    result = {
        "key": required_string(row, "key", 255),
        "name": required_string(row, "name", 255),
        "type": required_string(row, "type", 64),
        "external_id": optional_string(row, "external_id", 255),
        "inn": optional_string(row, "inn", 12),
        "ogrn": optional_string(row, "ogrn", 15),
        "phones": optional_phones(row),
        "email": optional_email(row),
        "website": optional_website(row),
        "provenance": optional_object(row, "provenance"),
    }
    if result["inn"] is not None and (not result["inn"].isdigit() or len(result["inn"]) not in (10, 12)):
        raise ValueError("inn must contain 10 or 12 digits")
    if result["ogrn"] is not None and (not result["ogrn"].isdigit() or len(result["ogrn"]) not in (13, 15)):
        raise ValueError("ogrn must contain 13 or 15 digits")
    return result


def optional_object(row: dict[str, Any], field: str) -> dict[str, Any]:
    value = row.get(field)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return cast(dict[str, Any], _db_safe_json(value))


def optional_date(row: dict[str, Any], field: str) -> str | None:
    value = optional_string(row, field, 10)
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value).date().isoformat()
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO 8601 date") from exc


def validate_link(row: object) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError("link must be an object")
    result: dict[str, Any] = {
        key: required_string(row, key, limit)
        for key, limit in (("house_key", 255), ("organization_key", 255), ("relationship", 64))
    }
    result["basis"] = optional_string(row, "basis", 2000)
    result["period_from"] = optional_date(row, "period_from")
    result["period_to"] = optional_date(row, "period_to")
    result["provenance"] = optional_object(row, "provenance")
    if result["period_from"] and result["period_to"] and result["period_to"] < result["period_from"]:
        raise ValueError("period_to cannot precede period_from")
    return result


async def _source(connection: AsyncConnection, source: dict[str, Any]) -> UUID:
    code = required_string(source, "code", 128)
    old = (
        (
            await connection.execute(
                text("SELECT id, data_kind FROM ingestion.source WHERE code=:code"), {"code": code}
            )
        )
        .mappings()
        .first()
    )
    if old:
        if old["data_kind"] != source["data_kind"]:
            raise ValueError("source.data_kind cannot change for an existing source")
        await connection.execute(
            text("UPDATE ingestion.source SET url=COALESCE(url, :url), updated_at=now() WHERE id=:id"),
            {"id": old["id"], "url": source.get("url")},
        )
        return old["id"]
    source_id = uuid4()
    await connection.execute(
        text("INSERT INTO ingestion.source(id, code, url, data_kind) VALUES (:id,:code,:url,:kind)"),
        {"id": source_id, "code": code, "url": source.get("url"), "kind": source["data_kind"]},
    )
    return source_id


async def _create_address(connection: AsyncConnection, row: dict[str, Any]) -> UUID:
    address_id = uuid4()
    await connection.execute(
        text(
            "INSERT INTO geo.address"
            "(id,formatted,city,street,house_number,point,created_at,updated_at) "
            "VALUES (:id,:formatted,:city,:street,:number,ST_GeogFromText(:point),now(),now())"
        ),
        {
            "id": address_id,
            "formatted": row["formatted"],
            "city": row["city"],
            "street": row["street"],
            "number": row["house_number"],
            "point": row["point"],
        },
    )
    return address_id


async def _house(
    connection: AsyncConnection, source_id: UUID, retrieved_at: datetime, row: dict[str, Any]
) -> str:
    old = (
        (
            await connection.execute(
                text(
                    "SELECT house_id, retrieved_at FROM ingestion.house_source "
                    "WHERE source_id=:source_id AND source_key=:key"
                ),
                {"source_id": source_id, "key": row["key"]},
            )
        )
        .mappings()
        .first()
    )
    if old and old["retrieved_at"] > retrieved_at:
        raise ValueError("record is older than the existing source version")
    if old:
        house_id = old["house_id"]
        conflicting_house = (
            await connection.execute(
                text(
                    "SELECT h.id FROM geo.house h JOIN geo.address a ON a.id=h.address_id "
                    "WHERE h.id<>:house_id AND lower(trim(a.city))=lower(:city) "
                    "AND lower(trim(a.street))=lower(:street) "
                    "AND lower(trim(a.house_number))=lower(:number) LIMIT 1"
                ),
                {
                    "house_id": house_id,
                    "city": row["city"],
                    "street": row["street"],
                    "number": row["house_number"],
                },
            )
        ).scalar_one_or_none()
        if conflicting_house is not None:
            raise ValueError("address belongs to another house")
        address_id = (
            await connection.execute(text("SELECT address_id FROM geo.house WHERE id=:id"), {"id": house_id})
        ).scalar_one()
        status = "houses_updated"
    else:
        matches = (
            await connection.execute(
                text(
                    "SELECT h.id, h.address_id FROM geo.house h JOIN geo.address a ON a.id=h.address_id "
                    "WHERE lower(trim(a.city))=lower(:city) AND lower(trim(a.street))=lower(:street) "
                    "AND lower(trim(a.house_number))=lower(:number) LIMIT 2"
                ),
                {"city": row["city"], "street": row["street"], "number": row["house_number"]},
            )
        ).all()
        if len(matches) > 1:
            raise ValueError("address matches multiple houses")
        if matches:
            house_id, address_id = matches[0]
            status = "houses_updated"
        else:
            house_id = uuid4()
            status = "houses_created"
            address_id = await _create_address(connection, row)
            await connection.execute(
                text(
                    "INSERT INTO geo.house(id,address_id,point,external_id,created_at,updated_at) "
                    "VALUES (:id,:address_id,ST_GeogFromText(:point),:external_id,now(),now())"
                ),
                {
                    "id": house_id,
                    "address_id": address_id,
                    "point": row["point"],
                    "external_id": row["external_id"],
                },
            )
    if status == "houses_updated":
        incoming_kind = (
            await connection.execute(
                text("SELECT data_kind FROM ingestion.source WHERE id=:source_id"),
                {"source_id": source_id},
            )
        ).scalar_one()
        preferred_source_exists = (
            await connection.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM ingestion.house_source hs "
                    "JOIN ingestion.source s ON s.id=hs.source_id "
                    "WHERE hs.house_id=:house_id AND hs.source_id<>:source_id "
                    "AND ((s.data_kind='REAL' AND :incoming_kind='DEMO') "
                    "OR (s.data_kind=:incoming_kind AND hs.retrieved_at>:retrieved_at)))"
                ),
                {
                    "house_id": house_id,
                    "source_id": source_id,
                    "retrieved_at": retrieved_at,
                    "incoming_kind": incoming_kind,
                },
            )
        ).scalar_one()
        if not preferred_source_exists:
            shared_address = (
                await connection.execute(
                    text("SELECT count(*) > 1 FROM geo.house WHERE address_id=:address_id"),
                    {"address_id": address_id},
                )
            ).scalar_one()
            if shared_address:
                address_id = await _create_address(connection, row)
                await connection.execute(
                    text("UPDATE geo.house SET address_id=:address_id WHERE id=:house_id"),
                    {"address_id": address_id, "house_id": house_id},
                )
            else:
                await connection.execute(
                    text(
                        "UPDATE geo.address SET formatted=:formatted,city=:city,street=:street,"
                        "house_number=:number,point=COALESCE(ST_GeogFromText(:point),point),"
                        "updated_at=now() WHERE id=:id"
                    ),
                    {
                        "id": address_id,
                        "formatted": row["formatted"],
                        "city": row["city"],
                        "street": row["street"],
                        "number": row["house_number"],
                        "point": row["point"],
                    },
                )
            await connection.execute(
                text(
                    "UPDATE geo.house SET point=COALESCE(ST_GeogFromText(:point),point),"
                    "external_id=COALESCE(:external_id,external_id),updated_at=now() WHERE id=:id"
                ),
                {"id": house_id, "point": row["point"], "external_id": row["external_id"]},
            )
    await connection.execute(
        text(
            "INSERT INTO ingestion.house_source("
            "source_id,source_key,house_id,retrieved_at,external_id,fias_id,canonical_address,"
            "official_status,management_method,provenance) "
            "VALUES (:source_id,:key,:house_id,:retrieved_at,:external_id,:fias_id,:canonical_address,"
            ":official_status,:management_method,CAST(:provenance AS jsonb)) "
            "ON CONFLICT(source_id,source_key) DO UPDATE SET retrieved_at=excluded.retrieved_at, "
            "external_id=COALESCE(excluded.external_id,ingestion.house_source.external_id),"
            "fias_id=COALESCE(excluded.fias_id,ingestion.house_source.fias_id),"
            "canonical_address=COALESCE(excluded.canonical_address,ingestion.house_source.canonical_address),"
            "official_status=COALESCE(excluded.official_status,ingestion.house_source.official_status),"
            "management_method=COALESCE(excluded.management_method,ingestion.house_source.management_method),"
            "provenance=ingestion.house_source.provenance || excluded.provenance"
        ),
        {
            "source_id": source_id,
            "key": row["key"],
            "house_id": house_id,
            "retrieved_at": retrieved_at,
            "external_id": row["external_id"],
            "fias_id": row["fias_id"],
            "canonical_address": row["canonical_address"],
            "official_status": row["official_status"],
            "management_method": row["management_method"],
            "provenance": json.dumps(row["provenance"], ensure_ascii=False),
        },
    )
    return status


async def _organization(
    connection: AsyncConnection, source_id: UUID, retrieved_at: datetime, row: dict[str, Any]
) -> str:
    old = (
        (
            await connection.execute(
                text(
                    "SELECT organization_id,retrieved_at FROM ingestion.organization_source "
                    "WHERE source_id=:source_id AND source_key=:key"
                ),
                {"source_id": source_id, "key": row["key"]},
            )
        )
        .mappings()
        .first()
    )
    if old and old["retrieved_at"] > retrieved_at:
        raise ValueError("record is older than the existing source version")
    if old:
        organization_id = old["organization_id"]
        await connection.execute(
            text("UPDATE ingestion.organization SET name=:name,type=:type,updated_at=now() WHERE id=:id"),
            {"id": organization_id, "name": row["name"], "type": row["type"]},
        )
        status = "organizations_updated"
    else:
        organization_id = uuid4()
        await connection.execute(
            text("INSERT INTO ingestion.organization(id,name,type) VALUES (:id,:name,:type)"),
            {"id": organization_id, "name": row["name"], "type": row["type"]},
        )
        status = "organizations_created"
    await connection.execute(
        text(
            "INSERT INTO ingestion.organization_source"
            "(source_id,source_key,organization_id,retrieved_at,external_id,inn,ogrn,phones,email,"
            "website,provenance) "
            "VALUES (:source_id,:key,:organization_id,:retrieved_at,:external_id,:inn,:ogrn,"
            "CAST(:phones AS jsonb),:email,:website,CAST(:provenance AS jsonb)) "
            "ON CONFLICT(source_id,source_key) DO UPDATE SET retrieved_at=excluded.retrieved_at, "
            "external_id=COALESCE(excluded.external_id,ingestion.organization_source.external_id),"
            "inn=COALESCE(excluded.inn,ingestion.organization_source.inn),"
            "ogrn=COALESCE(excluded.ogrn,ingestion.organization_source.ogrn),"
            "phones=CASE WHEN excluded.phones='[]'::jsonb THEN ingestion.organization_source.phones "
            "ELSE excluded.phones END,"
            "email=COALESCE(excluded.email,ingestion.organization_source.email),"
            "website=COALESCE(excluded.website,ingestion.organization_source.website),"
            "provenance=ingestion.organization_source.provenance || excluded.provenance"
        ),
        {
            "source_id": source_id,
            "key": row["key"],
            "organization_id": organization_id,
            "retrieved_at": retrieved_at,
            "external_id": row["external_id"],
            "inn": row["inn"],
            "ogrn": row["ogrn"],
            "phones": json.dumps(row["phones"], ensure_ascii=False),
            "email": row["email"],
            "website": row["website"],
            "provenance": json.dumps(row["provenance"], ensure_ascii=False),
        },
    )
    return status


async def _link(
    connection: AsyncConnection, source_id: UUID, retrieved_at: datetime, row: dict[str, str]
) -> bool:
    house_mapping = (
        (
            await connection.execute(
                text(
                    "SELECT house_id,retrieved_at FROM ingestion.house_source "
                    "WHERE source_id=:source_id AND source_key=:key"
                ),
                {"source_id": source_id, "key": row["house_key"]},
            )
        )
        .mappings()
        .first()
    )
    organization_mapping = (
        (
            await connection.execute(
                text(
                    "SELECT organization_id,retrieved_at FROM ingestion.organization_source "
                    "WHERE source_id=:source_id AND source_key=:key"
                ),
                {"source_id": source_id, "key": row["organization_key"]},
            )
        )
        .mappings()
        .first()
    )
    if house_mapping is None or organization_mapping is None:
        raise ValueError("house_key or organization_key is absent from this source")
    if house_mapping["retrieved_at"] > retrieved_at or organization_mapping["retrieved_at"] > retrieved_at:
        raise ValueError("link is older than the referenced source records")
    house_id = house_mapping["house_id"]
    organization_id = organization_mapping["organization_id"]
    existing = (
        await connection.execute(
            text(
                "SELECT retrieved_at FROM ingestion.house_organization "
                "WHERE source_id=:source_id AND house_id=:house_id "
                "AND organization_id=:organization_id AND relationship=:relationship"
            ),
            {
                "source_id": source_id,
                "house_id": house_id,
                "organization_id": organization_id,
                "relationship": row["relationship"],
            },
        )
    ).scalar_one_or_none()
    if existing is not None and existing > retrieved_at:
        raise ValueError("link is older than the existing source version")
    created = (
        await connection.execute(
            text(
                "INSERT INTO ingestion.house_organization"
                "(source_id,house_id,organization_id,relationship,retrieved_at,basis,period_from,"
                "period_to,provenance) "
                "VALUES (:source_id,:house_id,:organization_id,:relationship,:retrieved_at,:basis,"
                ":period_from,:period_to,CAST(:provenance AS jsonb)) "
                "ON CONFLICT(source_id,house_id,organization_id,relationship) DO UPDATE "
                "SET retrieved_at=GREATEST(ingestion.house_organization.retrieved_at,excluded.retrieved_at),"
                "basis=COALESCE(excluded.basis,ingestion.house_organization.basis),"
                "period_from=COALESCE(excluded.period_from,ingestion.house_organization.period_from),"
                "period_to=COALESCE(excluded.period_to,ingestion.house_organization.period_to),"
                "provenance=ingestion.house_organization.provenance || excluded.provenance "
                "RETURNING (xmax = 0)"
            ),
            {
                "source_id": source_id,
                "house_id": house_id,
                "organization_id": organization_id,
                "relationship": row["relationship"],
                "retrieved_at": retrieved_at,
                "basis": row["basis"],
                "period_from": row["period_from"],
                "period_to": row["period_to"],
                "provenance": json.dumps(row["provenance"], ensure_ascii=False),
            },
        )
    ).scalar_one()
    return bool(created)


async def import_file(path: Path, database_url: str | None = None) -> dict[str, int | str]:
    dataset, digest = read_dataset(path)
    return await import_dataset(dataset, digest, database_url)


async def import_dataset(
    dataset: dict[str, Any], digest: str, database_url: str | None = None
) -> dict[str, int | str]:
    """Import an already validated (``read_dataset``) dataset in one transaction, recorded
    as one ``ingestion.run`` against ``digest`` (the SHA-256 of the file it came from)."""
    retrieved_at = datetime.fromisoformat(dataset["source"]["retrieved_at"])
    engine = create_async_engine(database_url or DatabaseSettings.from_environment().url)
    counts: Counter[str] = Counter()
    run_id = uuid4()
    try:
        async with engine.begin() as connection:
            await connection.execute(text("SELECT pg_advisory_xact_lock(61744, 1)"))
            source_id = await _source(connection, dataset["source"])
            await connection.execute(
                text("INSERT INTO ingestion.run(id,source_id,file_sha256) VALUES (:id,:source_id,:digest)"),
                {"id": run_id, "source_id": source_id, "digest": digest},
            )
            seen: dict[str, set[str]] = {"house": set(), "organization": set()}
            for label, rows, validator, writer in (
                ("house", dataset["houses"], validate_house, _house),
                ("organization", dataset["organizations"], validate_organization, _organization),
                ("link", dataset["links"], validate_link, _link),
            ):
                for number, raw in enumerate(rows, 1):
                    try:
                        row = validator(raw)
                        if label != "link":
                            if row["key"] in seen[label]:
                                raise ValueError("duplicate source key in file")
                            seen[label].add(row["key"])
                        async with connection.begin_nested():
                            result = await writer(connection, source_id, retrieved_at, row)
                        if label == "link":
                            counts["links_created"] += int(result)
                        elif isinstance(result, str):
                            counts[result] += 1
                    except (ValueError, TypeError, SQLAlchemyError) as exc:
                        counts["error_count"] += 1
                        await connection.execute(
                            text(
                                "INSERT INTO ingestion.error"
                                "(id,run_id,entity_type,row_number,reason,payload) "
                                "VALUES (:id,:run_id,:entity_type,:row_number,:reason,"
                                "CAST(:payload AS jsonb))"
                            ),
                            {
                                "id": uuid4(),
                                "run_id": run_id,
                                "entity_type": label,
                                "row_number": number,
                                "reason": _db_safe_string(str(exc)),
                                "payload": json.dumps(_db_safe_json(raw), ensure_ascii=False),
                            },
                        )
            await connection.execute(
                text(
                    "UPDATE ingestion.run SET completed_at=now(),houses_created=:houses_created,"
                    "houses_updated=:houses_updated,organizations_created=:organizations_created,"
                    "organizations_updated=:organizations_updated,links_created=:links_created,"
                    "error_count=:error_count WHERE id=:id"
                ),
                {
                    "id": run_id,
                    **{
                        key: counts[key]
                        for key in (
                            "houses_created",
                            "houses_updated",
                            "organizations_created",
                            "organizations_updated",
                            "links_created",
                            "error_count",
                        )
                    },
                },
            )
    finally:
        await engine.dispose()
    return {
        "run_id": str(run_id),
        **{
            key: counts[key]
            for key in (
                "houses_created",
                "houses_updated",
                "organizations_created",
                "organizations_updated",
                "links_created",
                "error_count",
            )
        },
    }
