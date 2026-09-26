"""Which УК/ТСЖ manages which house - assigning, taking and releasing houses."""

from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from litestar import Controller, Router, get, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ClientException, NotFoundException, PermissionDeniedException
from litestar.params import FromPath, Parameter
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.geo.models import Address, HouseManagement
from src.domains.geo.schemas import (
    AssignHouseManagementCommand,
    HouseManagementSummary,
    TerminateHouseManagementCommand,
)
from src.domains.geo.services import (
    HouseManagementConflictError,
    HouseManagementNotFoundError,
    HouseManagementService,
    house_management_summary_statement,
    to_house_management_summary,
)
from src.domains.geo.services.territories import jurisdiction_house_ids
from src.domains.identity.admin_scope import AUTHORITY_ROLE, is_platform_admin, resolve_organization_scope
from src.security.dependency import provide_principal
from src.security.guards import require_roles
from src.security.principal import Principal

_STAFF_ADMIN_ROLES = ("admin", "district_admin", "housing_worker")


_HOUSE_MANAGEMENT_AUTHORITY_ROLES = ("admin", "district_admin")
"""Who may assign any house to any organization (including moving it away from its
current manager): the platform admin, or the district administration (Управа) acting as
the local authority that appoints a УК from the Перечень. A ``housing_worker`` may only
take a not-yet-managed house for, and release a house from, their own organization."""


def _jurisdiction_of(principal: Principal) -> UUID | None:
    if is_platform_admin(principal) or not principal.has_role(AUTHORITY_ROLE):
        return None
    return principal.organization_id or UUID(int=0)


def provide_house_management_service(
    db_session: NamedDependency[AsyncSession],
) -> HouseManagementService:
    return HouseManagementService(session=db_session)


class HouseManagementController(Controller):
    """Which УК/ТСЖ manages which house - the houses define what an organization works
    on (its residents, reports and incidents, see ``src.domains.incidents.scope``).
    ``admin``/``district_admin`` see and change every record; a ``housing_worker`` sees
    and manages only their own organization's houses."""

    path = "/geo/house-management"
    tags = ("geo",)
    return_dto = None

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "service": Provide(provide_house_management_service, sync_to_thread=False),
            "principal": Provide(provide_principal),
        }

    @get("/", name="geo:HouseManagement:list", guards=[require_roles(*_STAFF_ADMIN_ROLES)])
    async def list_items(
        self,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        house_id: Annotated[UUID | None, Parameter()] = None,
        organization_id: Annotated[UUID | None, Parameter()] = None,
        active_only: Annotated[bool, Parameter()] = True,
        limit: Annotated[int, Parameter(ge=1, le=200)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[HouseManagementSummary]:
        jurisdiction = _jurisdiction_of(principal)
        if not principal.has_role(*_HOUSE_MANAGEMENT_AUTHORITY_ROLES):
            scope = resolve_organization_scope(principal, organization_id)
            if scope.sees_nothing:
                return []
            organization_id = scope.organization_id
        with database_action("list", "geo.HouseManagement"):
            statement = house_management_summary_statement()
            if jurisdiction is not None:
                statement = statement.where(
                    HouseManagement.house_id.in_(jurisdiction_house_ids(jurisdiction))
                )
            if house_id is not None:
                statement = statement.where(HouseManagement.house_id == house_id)
            if organization_id is not None:
                statement = statement.where(HouseManagement.organization_id == organization_id)
            if active_only:
                statement = statement.where(HouseManagement.is_active.is_(True))
            statement = (
                statement.order_by(Address.formatted, HouseManagement.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            rows = (await db_session.execute(statement)).all()
            return [to_house_management_summary(row) for row in rows]

    @post(
        "/",
        status_code=201,
        name="geo:HouseManagement:assign",
        guards=[require_roles(*_STAFF_ADMIN_ROLES)],
    )
    async def assign(
        self,
        data: AssignHouseManagementCommand,
        service: NamedDependency[HouseManagementService],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> HouseManagementSummary:
        is_authority = principal.has_role(*_HOUSE_MANAGEMENT_AUTHORITY_ROLES)
        if not is_authority and resolve_organization_scope(principal, data.organization_id).sees_nothing:
            raise PermissionDeniedException("No active organization membership")
        with database_action("create", "geo.HouseManagement"):
            try:
                management = await service.assign(
                    data,
                    changed_by=principal.actor_id,
                    allow_replace=is_authority,
                    jurisdiction_of=_jurisdiction_of(principal),
                )
            except HouseManagementNotFoundError as exc:
                raise NotFoundException(str(exc)) from exc
            except HouseManagementConflictError as exc:
                raise ClientException(status_code=409, detail=str(exc)) from exc
            await db_session.commit()
            return await self._summary(db_session, management.id)

    @post(
        "/{item_id:uuid}/terminate",
        status_code=200,
        name="geo:HouseManagement:terminate",
        guards=[require_roles(*_STAFF_ADMIN_ROLES)],
    )
    async def terminate(
        self,
        item_id: FromPath[UUID],
        data: TerminateHouseManagementCommand,
        service: NamedDependency[HouseManagementService],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> HouseManagementSummary:
        own_organization: UUID | None = None
        if not principal.has_role(*_HOUSE_MANAGEMENT_AUTHORITY_ROLES):
            if principal.organization_id is None:
                raise PermissionDeniedException("No active organization membership")
            own_organization = principal.organization_id
        with database_action("update", "geo.HouseManagement"):
            try:
                await service.terminate(
                    item_id,
                    data,
                    changed_by=principal.actor_id,
                    organization_id=own_organization,
                    jurisdiction_of=_jurisdiction_of(principal),
                )
            except HouseManagementNotFoundError as exc:
                raise NotFoundException(str(exc)) from exc
            except HouseManagementConflictError as exc:
                raise ClientException(status_code=409, detail=str(exc)) from exc
            await db_session.commit()
            return await self._summary(db_session, item_id)

    @staticmethod
    async def _summary(db_session: AsyncSession, item_id: UUID) -> HouseManagementSummary:
        statement = house_management_summary_statement().where(HouseManagement.id == item_id)
        row = (await db_session.execute(statement)).first()
        if row is None:
            raise NotFoundException(f"House management {item_id} was not found")
        return to_house_management_summary(row)
