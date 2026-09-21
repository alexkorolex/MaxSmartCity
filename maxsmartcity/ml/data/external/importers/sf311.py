"""Streaming reader for the SF311 Recent Cases export."""

import csv
from collections.abc import Iterator
from pathlib import Path

from maxsmartcity.ml.data.external.models import Sf311Record


class Sf311CsvImporter:
    required_columns = frozenset({"CASE ID", "CATEGORY", "TYPE", "DETAILS", "AGENCY"})

    def read(self, path: Path) -> Iterator[Sf311Record]:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            missing = self.required_columns - set(reader.fieldnames or ())
            if missing:
                msg = f"SF311 export misses required columns: {sorted(missing)}"
                raise ValueError(msg)
            for row in reader:
                yield Sf311Record(
                    case_id=_required(row, "CASE ID"),
                    category=_required(row, "CATEGORY"),
                    type=_clean(row.get("TYPE")),
                    details=_clean(row.get("DETAILS")),
                    agency=_clean(row.get("AGENCY")),
                )


def _clean(value: str | None) -> str:
    return value.strip() if value else ""


def _required(row: dict[str, str | None], key: str) -> str:
    value = _clean(row.get(key))
    if not value:
        msg = f"SF311 row has empty required field: {key}"
        raise ValueError(msg)
    return value
