"""Table metadata for ingestion-owned reference and provenance records."""

from sqlalchemy import (
    CHAR,
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

from src.common.models import Entity

metadata = Entity.metadata

source = Table(
    "source",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("code", String(128), nullable=False, unique=True),
    Column("url", Text),
    Column("data_kind", String(4), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="ingestion",
)
house_source = Table(
    "house_source",
    metadata,
    Column("source_id", Uuid, ForeignKey("ingestion.source.id"), primary_key=True),
    Column("source_key", String(255), primary_key=True),
    Column("house_id", Uuid, ForeignKey("geo.house.id"), nullable=False),
    Column("retrieved_at", DateTime(timezone=True), nullable=False),
    Column("external_id", String(255)),
    Index("ix_house_source_house_id", "house_id"),
    schema="ingestion",
)
organization = Table(
    "organization",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("name", String(255), nullable=False),
    Column("type", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="ingestion",
)
organization_source = Table(
    "organization_source",
    metadata,
    Column("source_id", Uuid, ForeignKey("ingestion.source.id"), primary_key=True),
    Column("source_key", String(255), primary_key=True),
    Column("organization_id", Uuid, ForeignKey("ingestion.organization.id"), nullable=False),
    Column("retrieved_at", DateTime(timezone=True), nullable=False),
    Column("external_id", String(255)),
    Index("ix_organization_source_organization_id", "organization_id"),
    schema="ingestion",
)
house_organization = Table(
    "house_organization",
    metadata,
    Column("source_id", Uuid, ForeignKey("ingestion.source.id"), primary_key=True),
    Column("house_id", Uuid, ForeignKey("geo.house.id"), primary_key=True),
    Column("organization_id", Uuid, ForeignKey("ingestion.organization.id"), primary_key=True),
    Column("relationship", String(64), primary_key=True),
    Column("retrieved_at", DateTime(timezone=True), nullable=False),
    Index("ix_house_organization_house_id", "house_id"),
    schema="ingestion",
)
run = Table(
    "run",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("source_id", Uuid, ForeignKey("ingestion.source.id"), nullable=False),
    Column("file_sha256", CHAR(64), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("completed_at", DateTime(timezone=True)),
    Column("houses_created", Integer, nullable=False, server_default="0"),
    Column("houses_updated", Integer, nullable=False, server_default="0"),
    Column("organizations_created", Integer, nullable=False, server_default="0"),
    Column("organizations_updated", Integer, nullable=False, server_default="0"),
    Column("links_created", Integer, nullable=False, server_default="0"),
    Column("error_count", Integer, nullable=False, server_default="0"),
    schema="ingestion",
)
error = Table(
    "error",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("run_id", Uuid, ForeignKey("ingestion.run.id"), nullable=False),
    Column("entity_type", String(32), nullable=False),
    Column("row_number", Integer, nullable=False),
    Column("reason", Text, nullable=False),
    Column("payload", JSON().with_variant(JSONB, "postgresql"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Index("ix_ingestion_error_run_id", "run_id"),
    schema="ingestion",
)
