from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

from litestar import Controller, Router, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ClientException, NotFoundException, PermissionDeniedException
from litestar.params import FromPath, Parameter
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.geo.schemas import (
    TerritoryAssignCommand,
    TerritoryAssignResult,
    TerritoryCreateCommand,
    TerritoryHouse,
    TerritoryNode,
    TerritoryStreet,
    TerritoryUpdateCommand,
)
from src.domains.geo.services.territories import (
    TerritoryConflictError,
    TerritoryForbiddenError,
    TerritoryNotFoundError,
    TerritoryService,
    visible_territory_root,
)
from src.domains.identity.admin_scope import is_platform_admin
from src.security.dependency import provide_principal
from src.security.guards import require_roles
from src.security.principal import Principal

_TERRITORY_ROLES = ("admin", "district_admin")


async def provide_territory_scope(
    db_session: NamedDependency[AsyncSession], principal: NamedDependency[Principal]
) -> UUID | None:
    try:
        return await visible_territory_root(
            db_session, is_admin=is_platform_admin(principal), organization_id=principal.organization_id
        )
    except TerritoryForbiddenError as exc:
        raise PermissionDeniedException(str(exc)) from exc


def provide_territory_service(db_session: NamedDependency[AsyncSession]) -> TerritoryService:
    return TerritoryService(db_session)


@asynccontextmanager
async def _territory_errors() -> AsyncIterator[None]:
    try:
        yield
    except TerritoryNotFoundError as exc:
        raise NotFoundException(str(exc)) from exc
    except TerritoryConflictError as exc:
        raise ClientException(status_code=409, detail=str(exc)) from exc
    except TerritoryForbiddenError as exc:
        raise PermissionDeniedException(str(exc)) from exc


class TerritoryController(Controller):
    path = "/geo/territories"
    tags = ("geo",)
    return_dto = None

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "principal": Provide(provide_principal),
            "service": Provide(provide_territory_service, sync_to_thread=False),
            "territory_scope": Provide(provide_territory_scope),
        }

    @get("/", name="geo:Territory:tree", guards=[require_roles(*_TERRITORY_ROLES)])
    async def tree(
        self, service: NamedDependency[TerritoryService], territory_scope: NamedDependency[UUID | None]
    ) -> Sequence[TerritoryNode]:
        with database_action("list", "geo.AdministrativeArea"):
            return await service.tree(territory_scope)

    @post("/", name="geo:Territory:create", guards=[require_roles(*_TERRITORY_ROLES)])
    async def create(
        self,
        data: TerritoryCreateCommand,
        service: NamedDependency[TerritoryService],
        db_session: NamedDependency[AsyncSession],
        territory_scope: NamedDependency[UUID | None],
    ) -> Sequence[TerritoryNode]:
        async with _territory_errors():
            with database_action("create", "geo.AdministrativeArea"):
                await service.create(
                    name=data.name, type=data.type, parent_id=data.parent_id, scope=territory_scope
                )
                await db_session.commit()
                return await service.tree(territory_scope)

    @patch("/{territory_id:uuid}", name="geo:Territory:update", guards=[require_roles(*_TERRITORY_ROLES)])
    async def update(
        self,
        territory_id: FromPath[UUID],
        data: TerritoryUpdateCommand,
        service: NamedDependency[TerritoryService],
        db_session: NamedDependency[AsyncSession],
        territory_scope: NamedDependency[UUID | None],
    ) -> Sequence[TerritoryNode]:
        async with _territory_errors():
            with database_action("update", "geo.AdministrativeArea"):
                await service.update(
                    territory_id,
                    name=data.name,
                    type=data.type,
                    parent_id=data.parent_id,
                    scope=territory_scope,
                )
                await db_session.commit()
                return await service.tree(territory_scope)

    @delete("/{territory_id:uuid}", name="geo:Territory:delete", guards=[require_roles(*_TERRITORY_ROLES)])
    async def delete_territory(
        self,
        territory_id: FromPath[UUID],
        service: NamedDependency[TerritoryService],
        db_session: NamedDependency[AsyncSession],
        territory_scope: NamedDependency[UUID | None],
    ) -> None:
        async with _territory_errors():
            with database_action("delete", "geo.AdministrativeArea"):
                await service.delete(territory_id, scope=territory_scope)
                await db_session.commit()

    @get(
        "/{territory_id:uuid}/streets",
        name="geo:Territory:streets",
        guards=[require_roles(*_TERRITORY_ROLES)],
    )
    async def streets(
        self,
        territory_id: FromPath[UUID],
        service: NamedDependency[TerritoryService],
        territory_scope: NamedDependency[UUID | None],
        q: Annotated[str, Parameter()] = "",
        limit: Annotated[int, Parameter(ge=1, le=1000)] = 300,
    ) -> Sequence[TerritoryStreet]:
        async with _territory_errors():
            with database_action("list", "geo.House"):
                return await service.streets(territory_id, query=q, limit=limit, scope=territory_scope)

    @get(
        "/{territory_id:uuid}/houses", name="geo:Territory:houses", guards=[require_roles(*_TERRITORY_ROLES)]
    )
    async def street_houses(
        self,
        territory_id: FromPath[UUID],
        service: NamedDependency[TerritoryService],
        territory_scope: NamedDependency[UUID | None],
        street: Annotated[str, Parameter()],
    ) -> Sequence[TerritoryHouse]:
        async with _territory_errors():
            with database_action("list", "geo.House"):
                return await service.street_houses(territory_id, street, scope=territory_scope)

    @post(
        "/{territory_id:uuid}/assign", name="geo:Territory:assign", guards=[require_roles(*_TERRITORY_ROLES)]
    )
    async def assign(
        self,
        territory_id: FromPath[UUID],
        data: TerritoryAssignCommand,
        service: NamedDependency[TerritoryService],
        db_session: NamedDependency[AsyncSession],
        territory_scope: NamedDependency[UUID | None],
    ) -> TerritoryAssignResult:
        async with _territory_errors():
            with database_action("update", "geo.House"):
                moved = await service.assign(
                    territory_id, streets=data.streets, house_ids=data.house_ids, scope=territory_scope
                )
                await db_session.commit()
                return TerritoryAssignResult(moved=moved)
