from geoalchemy2 import Geography, Geometry
from sqlalchemy import String, func
from sqlalchemy.engine import Dialect
from sqlalchemy.sql import ColumnElement
from sqlalchemy.types import TypeDecorator


class GeometryText(TypeDecorator[str]):
    """Native PostGIS geometry with WKT strings at the ORM and DTO boundary."""

    impl = Geometry
    cache_ok: bool = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        if value is None or value.startswith("SRID="):
            return value
        return f"SRID=4326;{value}"

    def column_expression(self, column: ColumnElement[str]) -> ColumnElement[str]:
        return func.ST_AsText(column, type_=String())


class GeographyText(GeometryText):
    """Native PostGIS geography; coordinates use longitude/latitude, EPSG:4326."""

    impl = Geography
    cache_ok: bool = True
