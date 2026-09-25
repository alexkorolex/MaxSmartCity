"""Writing reference organizations (with contacts) and their links to houses."""

import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def write_organization(
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


async def write_link(
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
