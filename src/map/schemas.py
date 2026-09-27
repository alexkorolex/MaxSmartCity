from dataclasses import dataclass


@dataclass(slots=True)
class MapLayerZooms:
    houses_min_zoom: int
    house_footprints_min_zoom: int
    buildings_min_zoom: int
    max_zoom: int


@dataclass(slots=True)
class MapCity:
    city: str
    houses: int
    located: int
    unlocated: int
    with_footprint: int
    buildings: int
    bbox: tuple[float, float, float, float] | None


@dataclass(slots=True)
class MapSummary:
    cities: list[MapCity]
    zooms: MapLayerZooms
    attribution: list[str]
