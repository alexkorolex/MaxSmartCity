from datetime import date
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, Date, Enum, ForeignKey, Index, String, Text, false, text, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.common.models import Entity
from src.database.spatial import GeographyText, GeometryText
from src.domains.geo.enums import AdministrativeAreaType


class AdministrativeArea(Entity):
    __tablename__ = "administrative_area"
    __table_args__ = (
        CheckConstraint("parent_id != id", name="ck_administrative_area_parent_not_self"),
        {"schema": "geo"},
    )

    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("geo.administrative_area.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[AdministrativeAreaType] = mapped_column(
        Enum(
            AdministrativeAreaType,
            native_enum=False,
            create_constraint=True,
            name="administrative_area_type",
        )
    )
    geometry: Mapped[str] = mapped_column(GeometryText("MULTIPOLYGON", srid=4326))


class Address(Entity):
    __tablename__ = "address"
    __table_args__ = ({"schema": "geo"},)

    formatted: Mapped[str] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(255))
    district: Mapped[str | None] = mapped_column(String(255))
    street: Mapped[str | None] = mapped_column(String(255))
    house_number: Mapped[str | None] = mapped_column(String(64))
    point: Mapped[str | None] = mapped_column(GeographyText("POINT", srid=4326))


class House(Entity):
    __tablename__ = "house"
    __table_args__ = ({"schema": "geo"},)

    address_id: Mapped[UUID] = mapped_column(ForeignKey("geo.address.id"), index=True)
    administrative_area_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("geo.administrative_area.id"), index=True
    )
    point: Mapped[str | None] = mapped_column(GeographyText("POINT", srid=4326))
    external_id: Mapped[str | None] = mapped_column(String(255))


class HouseManagement(Entity):
    """Standing "this organization manages this house" relationship - distinct from
    ``collaboration.Assignment``, which is scoped to a single incident. Only one row per
    house may be active at a time (see ``uq_house_management_active_house`` below)."""

    __tablename__ = "house_management"
    __table_args__ = (
        Index(
            "uq_house_management_active_house",
            "house_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="effective_range",
        ),
        {"schema": "geo"},
    )

    house_id: Mapped[UUID] = mapped_column(ForeignKey("geo.house.id"), index=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("identity.organization.id"), index=True)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    basis: Mapped[str | None] = mapped_column(Text)
    """Free-text basis for the assignment, e.g. "решение общего собрания №..." or
    "включение в Перечень"."""
    assigned_via_reserve_registry: Mapped[bool] = mapped_column(default=False, server_default=false())
    """True when this house had no resident-chosen manager and was assigned from the
    government's Перечень (see ``Organization.in_reserve_registry``), rather than by a
    residents' general-meeting decision."""
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)


class AffectedObject(Entity):
    __tablename__ = "affected_object"
    __table_args__ = ({"schema": "geo"},)

    type: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    address_id: Mapped[UUID | None] = mapped_column(ForeignKey("geo.address.id"), index=True)
    house_id: Mapped[UUID | None] = mapped_column(ForeignKey("geo.house.id"), index=True)
    point: Mapped[str | None] = mapped_column(GeographyText("POINT", srid=4326))
    geometry: Mapped[str | None] = mapped_column(GeometryText("GEOMETRY", srid=4326))
    object_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSON().with_variant(JSONB, "postgresql"), default=dict, server_default="{}"
    )
