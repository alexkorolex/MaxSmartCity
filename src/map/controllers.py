from typing import Annotated, Any
from uuid import UUID

from litestar import Controller, Response, Router, get
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ClientException, PermissionDeniedException
from litestar.params import Parameter
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.geo.services.territories import TerritoryForbiddenError, visible_territory_root
from src.domains.identity.admin_scope import is_platform_admin
from src.map import queries
from src.map.schemas import MapLayerZooms, MapSummary
from src.security.dependency import provide_principal
from src.security.guards import require_roles
from src.security.principal import Principal

MVT_MEDIA_TYPE = "application/vnd.mapbox-vector-tile"
HOUSES_CACHE_CONTROL = "private, max-age=60"
BUILDINGS_CACHE_CONTROL = "private, max-age=86400"
ATTRIBUTION = [
    "© OpenStreetMap contributors (ODbL)",
    "Microsoft Global ML Building Footprints (CDLA Permissive 2.0)",
]


async def provide_map_scope(
    db_session: NamedDependency[AsyncSession], principal: NamedDependency[Principal]
) -> UUID | None:
    try:
        return await visible_territory_root(
            db_session, is_admin=is_platform_admin(principal), organization_id=principal.organization_id
        )
    except TerritoryForbiddenError as exc:
        raise PermissionDeniedException(str(exc)) from exc


def _tile_response(tile: bytes, cache_control: str) -> Response[bytes]:
    headers = {"Cache-Control": cache_control}
    if not tile:
        return Response(content=b"", status_code=204, headers=headers)
    return Response(content=tile, media_type=MVT_MEDIA_TYPE, headers=headers)


class MapController(Controller):
    path = "/map"
    tags = ("map",)
    guards = (require_roles("admin", "district_admin"),)

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "principal": Provide(provide_principal),
            "map_scope": Provide(provide_map_scope),
        }

    @get("/summary", name="map:summary")
    async def summary(
        self, db_session: NamedDependency[AsyncSession], map_scope: NamedDependency[UUID | None]
    ) -> MapSummary:
        return MapSummary(
            cities=await queries.cities_summary(db_session, scope_root=map_scope),
            zooms=MapLayerZooms(
                houses_min_zoom=queries.HOUSES_MIN_ZOOM,
                house_footprints_min_zoom=queries.HOUSE_FOOTPRINTS_MIN_ZOOM,
                buildings_min_zoom=queries.BUILDINGS_MIN_ZOOM,
                max_zoom=queries.MAX_ZOOM,
            ),
            attribution=ATTRIBUTION,
            scope=await queries.scope_territory(db_session, map_scope),
        )

    @get("/districts", name="map:districts")
    async def districts(
        self, db_session: NamedDependency[AsyncSession], map_scope: NamedDependency[UUID | None]
    ) -> dict[str, Any]:
        return await queries.districts_feature_collection(db_session, scope_root=map_scope)

    @get("/incidents", name="map:incidents")
    async def incidents(
        self,
        db_session: NamedDependency[AsyncSession],
        map_scope: NamedDependency[UUID | None],
        bbox: Annotated[str | None, Parameter(max_length=100)] = None,
        include_closed: bool = False,
    ) -> dict[str, Any]:
        try:
            bounds = queries.parse_bbox(bbox)
        except queries.InvalidBboxError as exc:
            raise ClientException(str(exc)) from exc
        return await queries.incident_houses_feature_collection(
            db_session, bbox=bounds, include_closed=include_closed, scope_root=map_scope
        )

    @get("/tiles/houses/{z:int}/{x:int}/{y:int}", name="map:tiles:houses")
    async def houses_tile(
        self,
        db_session: NamedDependency[AsyncSession],
        map_scope: NamedDependency[UUID | None],
        z: int,
        x: int,
        y: int,
    ) -> Response[bytes]:
        try:
            tile = await queries.houses_tile(db_session, z, x, y, scope_root=map_scope)
        except queries.InvalidTileError as exc:
            raise ClientException(str(exc)) from exc
        return _tile_response(tile, HOUSES_CACHE_CONTROL)

    @get("/tiles/buildings/{z:int}/{x:int}/{y:int}", name="map:tiles:buildings")
    async def buildings_tile(
        self,
        db_session: NamedDependency[AsyncSession],
        map_scope: NamedDependency[UUID | None],
        z: int,
        x: int,
        y: int,
    ) -> Response[bytes]:
        try:
            tile = await queries.buildings_tile(db_session, z, x, y, scope_root=map_scope)
        except queries.InvalidTileError as exc:
            raise ClientException(str(exc)) from exc
        return _tile_response(tile, BUILDINGS_CACHE_CONTROL)
