"""One import run: source registration, the transaction and advisory lock, per-row
savepoints and the ``ingestion.error`` log, and the run's counters."""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from src.database.config import DatabaseSettings
from src.domains.ingestion.importer.houses import write_house
from src.domains.ingestion.importer.organizations import write_link, write_organization
from src.domains.ingestion.importer.parsing import db_safe_json, db_safe_string, read_dataset, required_string
from src.domains.ingestion.importer.validation import validate_house, validate_link, validate_organization


async def ensure_source(connection: AsyncConnection, source: dict[str, Any]) -> UUID:
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
            source_id = await ensure_source(connection, dataset["source"])
            await connection.execute(
                text("INSERT INTO ingestion.run(id,source_id,file_sha256) VALUES (:id,:source_id,:digest)"),
                {"id": run_id, "source_id": source_id, "digest": digest},
            )
            seen: dict[str, set[str]] = {"house": set(), "organization": set()}
            for label, rows, validator, writer in (
                ("house", dataset["houses"], validate_house, write_house),
                ("organization", dataset["organizations"], validate_organization, write_organization),
                ("link", dataset["links"], validate_link, write_link),
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
                                "reason": db_safe_string(str(exc)),
                                "payload": json.dumps(db_safe_json(raw), ensure_ascii=False),
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
