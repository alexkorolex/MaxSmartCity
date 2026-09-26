from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

_FIND = (
    "SELECT id FROM geo.administrative_area WHERE lower(trim(name)) = lower(trim(:name)) "
    "AND parent_id IS NOT DISTINCT FROM :parent_id"
)
_CREATE = (
    "INSERT INTO geo.administrative_area(id, parent_id, name, type, created_at, updated_at) "
    "VALUES (:id, :parent_id, :name, :type, now(), now())"
)
_IN_SUBTREE = (
    "WITH RECURSIVE subtree AS ("
    "SELECT id FROM geo.administrative_area WHERE id = :root_id "
    "UNION ALL SELECT a.id FROM geo.administrative_area a JOIN subtree s ON a.parent_id = s.id) "
    "SELECT EXISTS(SELECT 1 FROM geo.house h JOIN subtree s ON s.id = h.administrative_area_id "
    "WHERE h.id = :house_id)"
)


async def _find(connection: AsyncConnection, name: str, parent_id: UUID | None) -> UUID | None:
    return (
        await connection.execute(text(_FIND), {"name": name, "parent_id": parent_id})
    ).scalar_one_or_none()


async def _find_or_create(connection: AsyncConnection, name: str, parent_id: UUID | None, type: str) -> UUID:
    existing = await _find(connection, name, parent_id)
    if existing is not None:
        return existing
    territory_id = uuid4()
    await connection.execute(
        text(_CREATE),
        {"id": territory_id, "parent_id": parent_id, "name": " ".join(name.split()), "type": type},
    )
    return territory_id


async def place_house(
    connection: AsyncConnection, house_id: UUID, city: str, okrug: str | None, district: str | None
) -> None:
    if okrug is None and district is None:
        city_id = await _find(connection, city, None)
        if city_id is None:
            return
        already_placed = (
            await connection.execute(text(_IN_SUBTREE), {"root_id": city_id, "house_id": house_id})
        ).scalar_one()
        if already_placed:
            return
        target = city_id
    else:
        target = await _find_or_create(connection, city, None, "CITY")
        if okrug is not None:
            target = await _find_or_create(connection, okrug, target, "ADMINISTRATIVE_OKRUG")
        if district is not None:
            target = await _find_or_create(connection, district, target, "DISTRICT")
    await connection.execute(
        text("UPDATE geo.house SET administrative_area_id = :target WHERE id = :house_id"),
        {"target": target, "house_id": house_id},
    )
