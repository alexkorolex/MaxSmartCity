from uuid import uuid4

from src.domains.geo.controllers.houses import _HouseMapRowData, _to_house_map_feature


def test_house_map_feature_keeps_unlocated_house() -> None:
    house_id = uuid4()
    feature = _to_house_map_feature(
        _HouseMapRowData(
            id=house_id,
            point_geojson=None,
            formatted="Брянск, улица Примерная, дом 1",
            city="Брянск",
            street="улица Примерная",
            house_number="1",
            active_reports=3,
            active_incidents=1,
        )
    )

    assert feature.id == str(house_id)
    assert feature.geometry is None
    assert feature.properties.active_reports == 3


def test_house_map_feature_uses_geojson_coordinate_order() -> None:
    feature = _to_house_map_feature(
        _HouseMapRowData(
            id=uuid4(),
            point_geojson='{"type":"Point","coordinates":[34.37,53.21]}',
            formatted="Брянск, улица Примерная, дом 2",
            city="Брянск",
            street="улица Примерная",
            house_number="2",
            active_reports=0,
            active_incidents=0,
        )
    )

    assert feature.geometry is not None
    assert feature.geometry.coordinates == (34.37, 53.21)
