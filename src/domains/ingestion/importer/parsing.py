"""Reading an ingestion dataset and normalizing its raw values (addresses, phones,
e-mails, websites) - strict JSON: duplicate fields and NaN/Infinity are rejected."""

import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

MAX_FILE_BYTES = 5 * 1024 * 1024


def _normalized_spaces(value: str) -> str:
    return " ".join(value.split())


def normalize_street(value: str) -> str:
    normalized = _normalized_spaces(value)
    match = re.fullmatch(r"(?i:ул\.?)\s+(.+)", normalized)
    if match:
        return f"улица {match.group(1)}"
    return normalized


def normalize_house_number(value: str) -> str:
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


def db_safe_string(value: str) -> str:
    return value.replace("\x00", "\\0").encode("utf-8", errors="replace").decode("utf-8")


def db_safe_json(value: object) -> object:
    if isinstance(value, str):
        return db_safe_string(value)
    if isinstance(value, list):
        return [db_safe_json(item) for item in value]
    if isinstance(value, dict):
        return {db_safe_string(str(key)): db_safe_json(item) for key, item in value.items()}
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
