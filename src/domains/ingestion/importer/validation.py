"""Row validation: a house, an organization, a house-organization link - each row is
checked on its own so one bad row is quarantined without failing the run."""

from datetime import datetime
from typing import Any, cast

from src.domains.ingestion.importer.parsing import (
    db_safe_json,
    normalize_house_number,
    normalize_street,
    optional_email,
    optional_phones,
    optional_string,
    optional_website,
    required_string,
)


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
    fields["street"] = normalize_street(fields["street"])
    fields["house_number"] = normalize_house_number(fields["house_number"])
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
    return cast(dict[str, Any], db_safe_json(value))


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
