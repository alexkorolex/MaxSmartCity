from collections import defaultdict
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, literal, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from src.domains.geo.enums import AdministrativeAreaType
from src.domains.geo.models import Address, AdministrativeArea, House
from src.domains.geo.schemas import (
    TerritoryHouse,
    TerritoryNode,
    TerritoryStreet,
    TerritoryStreetShare,
)
from src.domains.identity.models import Organization

MAX_TERRITORY_NAME_LENGTH = 255


class TerritoryNotFoundError(RuntimeError):
    pass


class TerritoryConflictError(RuntimeError):
    pass


class TerritoryForbiddenError(RuntimeError):
    pass


def normalized(column: InstrumentedAttribute[str | None] | InstrumentedAttribute[str]) -> ColumnElement[str]:
    return func.lower(func.trim(column))


def subtree_ids(territory_id: UUID | ColumnElement[Any]) -> Select[Any]:
    tree = select(AdministrativeArea.id).where(AdministrativeArea.id == territory_id).cte(recursive=True)
    tree = tree.union_all(select(AdministrativeArea.id).where(AdministrativeArea.parent_id == tree.c.id))
    return select(tree.c.id)


def ancestor_ids(territory_id: UUID | ColumnElement[Any]) -> Select[Any]:
    chain = (
        select(AdministrativeArea.id, AdministrativeArea.parent_id)
        .where(AdministrativeArea.id == territory_id)
        .cte(recursive=True)
    )
    chain = chain.union_all(
        select(AdministrativeArea.id, AdministrativeArea.parent_id).where(
            AdministrativeArea.id == chain.c.parent_id
        )
    )
    return select(chain.c.id)


def territory_house_ids(territory_id: UUID) -> Select[Any]:
    return select(House.id).where(House.administrative_area_id.in_(subtree_ids(territory_id)))


def jurisdiction_house_ids(organization_id: UUID) -> Select[Any]:
    territory = select(Organization.territory_id).where(Organization.id == organization_id).scalar_subquery()
    return select(House.id).where(House.administrative_area_id.in_(subtree_ids(territory)))


async def visible_territory_root(
    session: AsyncSession, *, is_admin: bool, organization_id: UUID | None
) -> UUID | None:
    if is_admin:
        return None
    territory_id = (
        await session.scalar(select(Organization.territory_id).where(Organization.id == organization_id))
        if organization_id is not None
        else None
    )
    if territory_id is None:
        raise TerritoryForbiddenError("Only a platform admin or an authority can see territories")
    return territory_id


async def ensure_territory_visible(session: AsyncSession, root_id: UUID | None, territory_id: UUID) -> None:
    if root_id is None:
        return
    if territory_id not in set((await session.scalars(subtree_ids(root_id))).all()):
        raise TerritoryForbiddenError("This territory is outside yours")


def _clean_name(name: str) -> str:
    cleaned = " ".join(name.split())
    if not cleaned:
        raise TerritoryConflictError("Territory name is required")
    if len(cleaned) > MAX_TERRITORY_NAME_LENGTH:
        raise TerritoryConflictError(f"Territory name is longer than {MAX_TERRITORY_NAME_LENGTH} characters")
    return cleaned


class TerritoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, territory_id: UUID) -> AdministrativeArea:
        territory = await self.session.get(AdministrativeArea, territory_id)
        if territory is None:
            raise TerritoryNotFoundError(f"Territory {territory_id} was not found")
        return territory

    async def tree(self, root_id: UUID | None = None) -> list[TerritoryNode]:
        house_counts = (
            select(House.administrative_area_id, func.count().label("houses"))
            .where(House.administrative_area_id.is_not(None))
            .group_by(House.administrative_area_id)
            .subquery()
        )
        authorities = (
            select(Organization.territory_id, func.array_agg(Organization.name).label("names"))
            .where(Organization.territory_id.is_not(None))
            .group_by(Organization.territory_id)
            .subquery()
        )
        statement = (
            select(
                AdministrativeArea,
                func.coalesce(house_counts.c.houses, 0).label("houses"),
                authorities.c.names,
            )
            .outerjoin(house_counts, house_counts.c.administrative_area_id == AdministrativeArea.id)
            .outerjoin(authorities, authorities.c.territory_id == AdministrativeArea.id)
            .order_by(AdministrativeArea.name)
        )
        if root_id is not None:
            statement = statement.where(AdministrativeArea.id.in_(subtree_ids(root_id)))
        rows = (await self.session.execute(statement)).all()
        direct = {row[0].id: row.houses for row in rows}
        children: dict[UUID | None, list[UUID]] = defaultdict(list)
        for row in rows:
            children[row[0].parent_id].append(row[0].id)

        def total(territory_id: UUID) -> int:
            return direct[territory_id] + sum(total(child) for child in children.get(territory_id, []))

        return [
            TerritoryNode(
                id=row[0].id,
                parent_id=row[0].parent_id if row[0].id != root_id else None,
                name=row[0].name,
                type=row[0].type.value,
                direct_house_count=row.houses,
                house_count=total(row[0].id),
                authorities=sorted(row.names or []),
            )
            for row in rows
        ]

    async def create(
        self, *, name: str, type: AdministrativeAreaType, parent_id: UUID | None
    ) -> AdministrativeArea:
        name = _clean_name(name)
        if parent_id is None and type is not AdministrativeAreaType.CITY:
            raise TerritoryConflictError("A top-level territory must be a city")
        if parent_id is not None and type is AdministrativeAreaType.CITY:
            raise TerritoryConflictError("A city can only be a top-level territory")
        if parent_id is not None:
            await self.get(parent_id)
        await self._ensure_name_free(name, parent_id)
        territory = AdministrativeArea(name=name, type=type, parent_id=parent_id)
        self.session.add(territory)
        await self.session.flush()
        if parent_id is None:
            await self._attach_city_houses(territory)
        return territory

    async def update(
        self,
        territory_id: UUID,
        *,
        name: str | None = None,
        type: AdministrativeAreaType | None = None,
        parent_id: UUID | None = None,
    ) -> AdministrativeArea:
        territory = await self.get(territory_id)
        is_city = territory.parent_id is None
        if name is not None:
            name = _clean_name(name)
            if is_city and name.lower() != territory.name.lower():
                raise TerritoryConflictError("A city is matched to houses by name and cannot be renamed")
            if name.lower() != territory.name.lower():
                await self._ensure_name_free(name, territory.parent_id)
            territory.name = name
        if type is not None and type is not territory.type:
            if is_city or type is AdministrativeAreaType.CITY:
                raise TerritoryConflictError("Only a top-level territory is a city")
            territory.type = type
        if parent_id is not None and parent_id != territory.parent_id:
            await self._move(territory, parent_id)
        await self.session.flush()
        return territory

    async def delete(self, territory_id: UUID) -> None:
        territory = await self.get(territory_id)
        if await self.session.scalar(
            select(AdministrativeArea.id).where(AdministrativeArea.parent_id == territory_id).limit(1)
        ):
            raise TerritoryConflictError("Delete or move the nested territories first")
        if await self.session.scalar(
            select(Organization.id).where(Organization.territory_id == territory_id).limit(1)
        ):
            raise TerritoryConflictError("An authority is attached to this territory")
        await self.session.execute(
            update(House)
            .where(House.administrative_area_id == territory_id)
            .values(administrative_area_id=territory.parent_id)
        )
        await self.session.delete(territory)
        await self.session.flush()

    async def city_root(self, territory_id: UUID) -> AdministrativeArea:
        territory = await self.get(territory_id)
        while territory.parent_id is not None:
            territory = await self.get(territory.parent_id)
        return territory

    async def streets(
        self, territory_id: UUID, *, query: str = "", limit: int = 200
    ) -> list[TerritoryStreet]:
        root = await self.city_root(territory_id)
        statement = (
            select(Address.street, House.administrative_area_id, func.count().label("houses"))
            .join(House, House.address_id == Address.id)
            .where(House.administrative_area_id.in_(subtree_ids(root.id)), Address.street.is_not(None))
            .group_by(Address.street, House.administrative_area_id)
        )
        if query.strip():
            statement = statement.where(Address.street.ilike(f"%{query.strip()}%"))
        names = {node.id: node.name for node in await self.tree(root.id)}
        streets: dict[str, list[TerritoryStreetShare]] = defaultdict(list)
        for row in (await self.session.execute(statement)).all():
            streets[row.street].append(
                TerritoryStreetShare(
                    territory_id=row.administrative_area_id,
                    territory_name=names.get(row.administrative_area_id, ""),
                    house_count=row.houses,
                )
            )
        return [
            TerritoryStreet(
                street=street,
                house_count=sum(share.house_count for share in shares),
                territories=sorted(shares, key=lambda share: -share.house_count),
            )
            for street, shares in sorted(streets.items())[:limit]
        ]

    async def street_houses(self, territory_id: UUID, street: str) -> list[TerritoryHouse]:
        root = await self.city_root(territory_id)
        rows = (
            await self.session.execute(
                select(
                    House.id,
                    Address.formatted,
                    Address.house_number,
                    AdministrativeArea.id,
                    AdministrativeArea.name,
                )
                .join(Address, Address.id == House.address_id)
                .join(AdministrativeArea, AdministrativeArea.id == House.administrative_area_id)
                .where(House.administrative_area_id.in_(subtree_ids(root.id)), Address.street == street)
                .order_by(Address.house_number)
            )
        ).all()
        return [
            TerritoryHouse(
                house_id=row[0],
                formatted=row.formatted,
                house_number=row.house_number,
                territory_id=row[3],
                territory_name=row.name,
            )
            for row in rows
        ]

    async def assign(self, territory_id: UUID, *, streets: list[str], house_ids: list[UUID]) -> int:
        root = await self.city_root(territory_id)
        in_city = House.administrative_area_id.in_(subtree_ids(root.id))
        moved = 0
        if streets:
            by_street = (
                select(House.id)
                .join(Address, Address.id == House.address_id)
                .where(in_city, Address.street.in_(streets))
            )
            result = await self.session.execute(
                update(House)
                .where(House.id.in_(by_street))
                .values(administrative_area_id=territory_id)
                .returning(House.id)
                .execution_options(synchronize_session=False)
            )
            moved += len(result.all())
        if house_ids:
            inside = await self.session.scalar(
                select(func.count()).select_from(House).where(House.id.in_(house_ids), in_city)
            )
            if inside != len(set(house_ids)):
                raise TerritoryConflictError("Some houses belong to another city")
            result = await self.session.execute(
                update(House)
                .where(House.id.in_(house_ids))
                .values(administrative_area_id=territory_id)
                .returning(House.id)
                .execution_options(synchronize_session=False)
            )
            moved += len(result.all())
        return moved

    async def _ensure_name_free(self, name: str, parent_id: UUID | None) -> None:
        same_parent = (
            AdministrativeArea.parent_id.is_(None)
            if parent_id is None
            else AdministrativeArea.parent_id == parent_id
        )
        taken = await self.session.scalar(
            select(AdministrativeArea.id).where(
                same_parent, normalized(AdministrativeArea.name) == name.lower()
            )
        )
        if taken is not None:
            raise TerritoryConflictError(f"Territory {name!r} already exists here")

    async def _attach_city_houses(self, city: AdministrativeArea) -> None:
        in_city = (
            select(House.id)
            .join(Address, Address.id == House.address_id)
            .where(
                House.administrative_area_id.is_(None), normalized(Address.city) == literal(city.name.lower())
            )
        )
        await self.session.execute(
            update(House)
            .where(House.id.in_(in_city))
            .values(administrative_area_id=city.id)
            .execution_options(synchronize_session=False)
        )

    async def _move(self, territory: AdministrativeArea, parent_id: UUID) -> None:
        if territory.parent_id is None:
            raise TerritoryConflictError("A city cannot be moved")
        if parent_id in set((await self.session.scalars(subtree_ids(territory.id))).all()):
            raise TerritoryConflictError("A territory cannot be moved into itself")
        if (await self.city_root(parent_id)).id != (await self.city_root(territory.id)).id:
            raise TerritoryConflictError("A territory can only be moved within its city")
        await self._ensure_name_free(territory.name, parent_id)
        territory.parent_id = parent_id
