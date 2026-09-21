"""Streaming reader for the synthetic BMC complaint table."""

import csv
from collections.abc import Iterator
from pathlib import Path

from maxsmartcity.ml.data.external.models import BmcRecord


class BmcCsvImporter:
    required_columns = frozenset(
        {
            "complaint_id",
            "complaint_category",
            "department_assigned",
            "severity",
            "property_type",
            "complaint_channel",
        }
    )

    def read(self, path: Path) -> Iterator[BmcRecord]:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            missing = self.required_columns - set(reader.fieldnames or ())
            if missing:
                msg = f"BMC export misses required columns: {sorted(missing)}"
                raise ValueError(msg)
            for row in reader:
                yield BmcRecord(
                    complaint_id=_required(row, "complaint_id"),
                    complaint_category=_required(row, "complaint_category"),
                    department_assigned=_required(row, "department_assigned"),
                    severity=_required(row, "severity"),
                    property_type=_required(row, "property_type"),
                    complaint_channel=_required(row, "complaint_channel"),
                )


def _required(row: dict[str, str | None], key: str) -> str:
    value = (row.get(key) or "").strip()
    if not value:
        msg = f"BMC row has empty required field: {key}"
        raise ValueError(msg)
    return value
