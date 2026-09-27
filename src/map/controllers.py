from typing import Annotated, Any

from litestar import Controller, Response, get
from litestar.di import NamedDependency
from litestar.exceptions import ClientException
from litestar.params import Parameter
from sqlalchemy.ext.asyncio import AsyncSession

from src.map import queries
from src.map.schemas import MapLayerZooms, MapSummary
from src.security.guards import require_roles

MVT_MEDIA_TYPE = "application/vnd.mapbox-vector-tile"
HOUSES_CACHE_CONTROL = "private, max-age=60"
BUILDINGS_CACHE_CONTROL = "private, max-age=86400"
ATTRIBUTION = [
    "© OpenStreetMap contributors (ODbL)",
    "Microsoft Global ML Building Footprints (CDLA Permissive 2.0)",
]


def _tile_response(tile: bytes, cache_control: str) -> Response[bytes]:
    headers = {"Cache-Control": cache_control}
    if not tile:
        return Response(content=b"", status_code=204, headers=headers)
    return Response(content=tile, media_type=MVT_MEDIA_TYPE, headers=headers)


class MapController(Controller):
    path = "/map"
    tags = ("map",)
    guards = (require_roles("admin", "district_admin"),)

    @get("/summary", name="map:summary")
    async def summary(self, db_session: NamedDependency[AsyncSession]) -> MapSummary:
        cities = await queries.cities_summary(db_session)
        return MapSummary(
            cities=cities,
            zooms=MapLayerZooms(
                houses_min_zoom=queries.HOUSES_MIN_ZOOM,
                house_footprints_min_zoom=queries.HOUSE_FOOTPRINTS_MIN_ZOOM,
                buildings_min_zoom=queries.BUILDINGS_MIN_ZOOM,
                max_zoom=queries.MAX_ZOOM,
            ),
            attribution=ATTRIBUTION,
        )

    @get("/districts", name="map:districts")
    async def districts(self, db_session: NamedDependency[AsyncSession]) -> dict[str, Any]:
        return await queries.districts_feature_collection(db_session)

    @get("/incidents", name="map:incidents")
    async def incidents(
        self,
        db_session: NamedDependency[AsyncSession],
        bbox: Annotated[str | None, Parameter(max_length=100)] = None,
        include_closed: bool = False,
    ) -> dict[str, Any]:
        try:
            bounds = queries.parse_bbox(bbox)
        except queries.InvalidBboxError as exc:
            raise ClientException(str(exc)) from exc
        return await queries.incident_houses_feature_collection(
            db_session, bbox=bounds, include_closed=include_closed
        )

    @get("/tiles/houses/{z:int}/{x:int}/{y:int}", name="map:tiles:houses")
    async def houses_tile(
        self, db_session: NamedDependency[AsyncSession], z: int, x: int, y: int
    ) -> Response[bytes]:
        try:
            tile = await queries.houses_tile(db_session, z, x, y)
        except queries.InvalidTileError as exc:
            raise ClientException(str(exc)) from exc
        return _tile_response(tile, HOUSES_CACHE_CONTROL)

    @get("/tiles/buildings/{z:int}/{x:int}/{y:int}", name="map:tiles:buildings")
    async def buildings_tile(
        self, db_session: NamedDependency[AsyncSession], z: int, x: int, y: int
    ) -> Response[bytes]:
        try:
            tile = await queries.buildings_tile(db_session, z, x, y)
        except queries.InvalidTileError as exc:
            raise ClientException(str(exc)) from exc
        return _tile_response(tile, BUILDINGS_CACHE_CONTROL)
