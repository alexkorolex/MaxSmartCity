"""Writing a house: matched to an existing one by source key or exact normalized address,
never overwriting fresher or official (REAL) data with older or DEMO data."""

import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


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


async def write_house(
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
