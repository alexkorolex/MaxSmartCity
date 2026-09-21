from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, Enum, ForeignKey, String, Text
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
    administrative_area_id: Mapped[UUID] = mapped_column(ForeignKey("geo.administrative_area.id"), index=True)
    point: Mapped[str] = mapped_column(GeographyText("POINT", srid=4326))
    external_id: Mapped[str | None] = mapped_column(String(255))


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
