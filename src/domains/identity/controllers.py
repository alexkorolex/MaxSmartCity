from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.dto import DTOData
from litestar.exceptions import NotFoundException
from litestar.params import FromPath, Parameter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.geo.models import House
from src.domains.identity.models import Department, Organization, Resident
from src.domains.identity.schemas import (
    DepartmentCreateDTO,
    DepartmentReadDTO,
    DepartmentUpdateDTO,
    OrganizationCreateDTO,
    OrganizationReadDTO,
    OrganizationUpdateDTO,
    PrincipalRead,
    ResidentReadDTO,
    ResidentSelfUpdateRequest,
)
from src.domains.identity.services import DepartmentService, OrganizationService, ResidentService
from src.security.dependency import provide_principal
from src.security.guards import require_resident, require_roles
from src.security.principal import Principal


def provide_organization_service(db_session: NamedDependency[AsyncSession]) -> OrganizationService:
    return OrganizationService(session=db_session, auto_commit=True)


def provide_department_service(db_session: NamedDependency[AsyncSession]) -> DepartmentService:
    return DepartmentService(session=db_session, auto_commit=True)


class OrganizationController(Controller):
    path = "/identity/organizations"
    tags = ("identity",)
    return_dto = OrganizationReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"service": Provide(provide_organization_service, sync_to_thread=False)}

    @get("/", name="identity:Organization:list")
    async def list_items(
        self,
        service: NamedDependency[OrganizationService],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Organization]:
        with database_action("list", "identity.Organization"):
            return await service.get_many(LimitOffset(limit=limit, offset=offset), order_by=("id", False))

    @get("/{item_id:uuid}", name="identity:Organization:get")
    async def get_item(
        self, item_id: FromPath[UUID], service: NamedDependency[OrganizationService]
    ) -> Organization:
        with database_action("get", "identity.Organization"):
            return await service.get(item_id)

    @post("/", dto=OrganizationCreateDTO, name="identity:Organization:create")
    async def create_item(
        self, data: DTOData[Organization], service: NamedDependency[OrganizationService]
    ) -> Organization:
        with database_action("create", "identity.Organization"):
            return await service.create(data)

    @patch("/{item_id:uuid}", dto=OrganizationUpdateDTO, name="identity:Organization:update")
    async def update_item(
        self,
        item_id: FromPath[UUID],
        data: DTOData[Organization],
        service: NamedDependency[OrganizationService],
    ) -> Organization:
        with database_action("update", "identity.Organization"):
            return await service.update(data, item_id=item_id)

    @delete("/{item_id:uuid}", return_dto=None, name="identity:Organization:delete")
    async def delete_item(
        self, item_id: FromPath[UUID], service: NamedDependency[OrganizationService]
    ) -> None:
        with database_action("delete", "identity.Organization"):
            await service.delete(item_id)


class DepartmentController(Controller):
    """Departments belong to an organization (housing utility / district administration)
    and are themselves owned by an ``admin``. Workers are linked in via
    ``OrganizationMember.department_id``."""

    path = "/identity/departments"
    tags = ("identity",)
    return_dto = DepartmentReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"service": Provide(provide_department_service, sync_to_thread=False)}

    @get("/", name="identity:Department:list")
    async def list_items(
        self,
        service: NamedDependency[DepartmentService],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Department]:
        with database_action("list", "identity.Department"):
            return await service.get_many(LimitOffset(limit=limit, offset=offset), order_by=("id", False))

    @get("/{item_id:uuid}", name="identity:Department:get")
    async def get_item(
        self, item_id: FromPath[UUID], service: NamedDependency[DepartmentService]
    ) -> Department:
        with database_action("get", "identity.Department"):
            return await service.get(item_id)

    @post(
        "/",
        dto=DepartmentCreateDTO,
        name="identity:Department:create",
        guards=[require_roles("admin")],
    )
    async def create_item(
        self, data: DTOData[Department], service: NamedDependency[DepartmentService]
    ) -> Department:
        with database_action("create", "identity.Department"):
            return await service.create(data)

    @patch(
        "/{item_id:uuid}",
        dto=DepartmentUpdateDTO,
        name="identity:Department:update",
        guards=[require_roles("admin")],
    )
    async def update_item(
        self,
        item_id: FromPath[UUID],
        data: DTOData[Department],
        service: NamedDependency[DepartmentService],
    ) -> Department:
        with database_action("update", "identity.Department"):
            return await service.update(data, item_id=item_id)

    @delete(
        "/{item_id:uuid}",
        return_dto=None,
        name="identity:Department:delete",
        guards=[require_roles("admin")],
    )
    async def delete_item(self, item_id: FromPath[UUID], service: NamedDependency[DepartmentService]) -> None:
        with database_action("delete", "identity.Department"):
            await service.delete(item_id)


def provide_resident_service(db_session: NamedDependency[AsyncSession]) -> ResidentService:
    return ResidentService(session=db_session, auto_commit=True)


class MeController(Controller):
    """Whoever holds a valid token - staff via Keycloak or a resident via the bot - can
    ask who they are."""

    path = "/identity/me"
    tags = ("identity",)

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "principal": Provide(provide_principal),
            "resident_service": Provide(provide_resident_service, sync_to_thread=False),
        }

    @get("/", name="identity:me")
    async def get_me(self, principal: NamedDependency[Principal]) -> PrincipalRead:
        return PrincipalRead(
            actor_type=principal.actor_type.value,
            actor_id=str(principal.actor_id),
            roles=sorted(principal.roles),
            organization_id=str(principal.organization_id) if principal.organization_id else None,
            department_id=str(principal.department_id) if principal.department_id else None,
        )

    @get(
        "/resident",
        name="identity:me:resident:get",
        guards=[require_resident()],
        return_dto=ResidentReadDTO,
    )
    async def get_my_resident_profile(
        self,
        resident_service: NamedDependency[ResidentService],
        principal: NamedDependency[Principal],
    ) -> Resident:
        with database_action("get", "identity.Resident"):
            return await resident_service.get(principal.actor_id)

    @patch(
        "/resident",
        name="identity:me:resident:update",
        guards=[require_resident()],
        return_dto=ResidentReadDTO,
    )
    async def update_my_resident_profile(
        self,
        data: ResidentSelfUpdateRequest,
        resident_service: NamedDependency[ResidentService],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> Resident:
        with database_action("update", "identity.Resident"):
            updates: dict[str, object] = {}
            if data.notifications_enabled is not None:
                updates["notifications_enabled"] = data.notifications_enabled
            if data.display_name is not None:
                updates["display_name"] = data.display_name
            if data.house_id is not None:
                exists = await db_session.scalar(select(House.id).where(House.id == data.house_id))
                if exists is None:
                    raise NotFoundException(f"House {data.house_id} was not found")
                updates["house_id"] = data.house_id
            if not updates:
                return await resident_service.get(principal.actor_id)
            return await resident_service.update(updates, item_id=principal.actor_id)
