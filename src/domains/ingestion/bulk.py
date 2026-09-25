"""Batched import of a large ingestion dataset, e.g. a whole-region GIS ЖКХ export made by
``src.domains.ingestion.gis_zkh`` (tens of thousands of houses).

Run with::

    python -m src.domains.ingestion.bulk var/gis_zkh_bryansk_bakhchysarai.json
    python -m src.domains.ingestion.bulk var/... --only-linked --batch-size 1000
    python -m src.domains.ingestion.bulk var/... --dry-run

The dataset goes through exactly the same validation, address matching and provenance
rules as ``python -m src.domains.ingestion`` - it is just split into batches, each its own
transaction and ``ingestion.run`` (all against the SHA-256 of the whole file): first the
organizations, then the houses, then the links, since a link resolves its house and
organization by source key from earlier runs. Every write is an idempotent upsert, so an
interrupted import is resumed by simply running the command again.
"""

import argparse
import asyncio
import json
import time
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.database.config import DatabaseSettings
from src.domains.ingestion.importer import (
    import_dataset,
    read_dataset,
    validate_house,
    validate_link,
    validate_organization,
)

DEFAULT_BATCH_SIZE = 2000
ANALYZED_TABLES = (
    "geo.address",
    "geo.house",
    "ingestion.house_source",
    "ingestion.organization_source",
    "ingestion.house_organization",
)
"""Refreshed between phases: a bulk import grows these tables by orders of magnitude in
minutes, faster than autovacuum re-analyzes them, and with stale statistics the planner
keeps picking plans made for a near-empty table - a repeat import then took ~10x longer."""
COUNTERS = (
    "houses_created",
    "houses_updated",
    "organizations_created",
    "organizations_updated",
    "links_created",
    "error_count",
)


def only_linked(dataset: dict[str, Any]) -> dict[str, Any]:
    """Drop houses no organization manages (in GIS ЖКХ mostly «способ управления не
    выбран») - they add nothing a resident could act on."""
    linked = {link.get("house_key") for link in dataset["links"] if isinstance(link, dict)}
    return {
        **dataset,
        "houses": [
            house for house in dataset["houses"] if isinstance(house, dict) and house.get("key") in linked
        ],
    }


def validate_rows(dataset: dict[str, Any]) -> dict[str, Any]:
    """Check every row with the importer's own validators, plus source keys duplicated
    across the whole file (a single import run only sees its own batch)."""
    report: dict[str, Any] = {}
    for kind, validator in (
        ("houses", validate_house),
        ("organizations", validate_organization),
        ("links", validate_link),
    ):
        reasons: Counter[str] = Counter()
        keys: Counter[str] = Counter()
        for row in dataset[kind]:
            try:
                validated = validator(row)
            except (ValueError, TypeError) as exc:
                reasons[str(exc)] += 1
                continue
            if kind != "links":
                keys[validated["key"]] += 1
        duplicates = sum(count - 1 for count in keys.values() if count > 1)
        report[kind] = {
            "invalid": sum(reasons.values()),
            "duplicate_keys": duplicates,
            "reasons": dict(reasons),
        }
    return report


def split_dataset(dataset: dict[str, Any], batch_size: int) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(label, batch)`` datasets: organizations, then houses, then links - in that
    order, because links reference houses and organizations imported by earlier batches."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    header = {"version": dataset["version"], "source": dataset["source"]}
    for kind in ("organizations", "houses", "links"):
        rows = dataset[kind]
        total = len(rows)
        for start in range(0, total, batch_size):
            batch = {**header, "houses": [], "organizations": [], "links": []}
            batch[kind] = rows[start : start + batch_size]
            end = min(start + batch_size, total)
            yield f"{kind} {start + 1}-{end}/{total}", batch


async def bulk_import(
    path: Path,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    linked_only: bool = False,
    dry_run: bool = False,
    database_url: str | None = None,
) -> dict[str, int]:
    dataset, digest = read_dataset(path, max_bytes=None)
    if linked_only:
        dataset = only_linked(dataset)
    print(
        json.dumps(
            {
                "file": str(path),
                "sha256": digest,
                "source": dataset["source"]["code"],
                "houses": len(dataset["houses"]),
                "organizations": len(dataset["organizations"]),
                "links": len(dataset["links"]),
                "batch_size": batch_size,
                "dry_run": dry_run,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    if dry_run:
        print(json.dumps({"validation": validate_rows(dataset)}, ensure_ascii=False), flush=True)
    totals: Counter[str] = Counter()
    previous_kind = None
    for label, batch in split_dataset(dataset, batch_size):
        if dry_run:
            print(json.dumps({"batch": label}, ensure_ascii=False), flush=True)
            continue
        kind = label.split(" ", 1)[0]
        if previous_kind is not None and kind != previous_kind:
            await analyze_tables(database_url)
        previous_kind = kind
        started = time.monotonic()
        result = await import_dataset(batch, digest, database_url)
        for key in COUNTERS:
            totals[key] += int(result[key])
        print(
            json.dumps(
                {"batch": label, "seconds": round(time.monotonic() - started, 1), **result},
                ensure_ascii=False,
            ),
            flush=True,
        )
    if not dry_run:
        await analyze_tables(database_url)
    return {key: totals[key] for key in COUNTERS}


async def analyze_tables(database_url: str | None = None) -> None:
    engine = create_async_engine(database_url or DatabaseSettings.from_environment().url)
    try:
        async with engine.connect() as connection:
            await connection.execute(text(f"ANALYZE {', '.join(ANALYZED_TABLES)}"))
            await connection.commit()
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a large houses/organizations dataset in batches")
    parser.add_argument("file", type=Path)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"rows per transaction (default {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--only-linked",
        action="store_true",
        help="import only houses that have a managing organization in the file",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="validate every row and show the batches, without writing"
    )
    args = parser.parse_args()
    load_dotenv()
    totals = asyncio.run(
        bulk_import(args.file, batch_size=args.batch_size, linked_only=args.only_linked, dry_run=args.dry_run)
    )
    print(json.dumps({"total": totals}, ensure_ascii=False))
    if totals["error_count"]:
        print(
            "Rejected rows are in ingestion.error: "
            "SELECT entity_type, row_number, reason FROM ingestion.error e "
            "JOIN ingestion.run r ON r.id = e.run_id WHERE r.file_sha256 = '<sha256 above>';"
        )


if __name__ == "__main__":
    main()
