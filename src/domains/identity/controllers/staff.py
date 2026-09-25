"""Staff directory (``OperatorUser``) and organization departments."""

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
from src.domains.identity.admin_scope import STAFF_ROLES, resolve_organization_scope
from src.domains.identity.models import (
    Department,
    OperatorUser,
    Organization,
    OrganizationMember,
    Role,
)
from src.domains.identity.schemas import (
    DepartmentCreateDTO,
    DepartmentReadDTO,
    DepartmentUpdateDTO,
    OperatorUserSummary,
)
from src.domains.identity.services import (
    DepartmentService,
)
from src.security.dependency import provide_principal
from src.security.guards import require_roles
from src.security.principal import Principal


def provide_department_service(db_session: NamedDependency[AsyncSession]) -> DepartmentService:
    return DepartmentService(session=db_session, auto_commit=True)


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


_ACTIVE_MEMBERSHIP = OrganizationMember.is_active.is_(True)


class OperatorUserController(Controller):
    """Admin-panel roster of staff (``OperatorUser``) accounts, scoped by organization
    for non-``admin`` callers - a ``district_admin``/``housing_worker`` may only browse
    their own organization's staff, never another organization's internal roster."""

    path = "/identity/operator-users"
    tags = ("identity",)
    return_dto = None

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"principal": Provide(provide_principal)}

    @get("/", name="identity:OperatorUser:list", guards=[require_roles(*STAFF_ROLES)])
    async def list_items(
        self,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        city: Annotated[str | None, Parameter()] = None,
        organization_id: Annotated[UUID | None, Parameter()] = None,
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[OperatorUserSummary]:
        scope = resolve_organization_scope(principal, organization_id)
        if scope.sees_nothing:
            return []
        with database_action("list", "identity.OperatorUser"):
            statement = (
                select(
                    OperatorUser.id,
                    OperatorUser.login,
                    OperatorUser.display_name,
                    OperatorUser.email,
                    OperatorUser.is_active,
                    OrganizationMember.organization_id,
                    Organization.name.label("organization_name"),
                    Organization.city.label("organization_city"),
                    OrganizationMember.department_id,
                    Department.name.label("department_name"),
                    Role.code.label("role_code"),
                )
                .select_from(OperatorUser)
                .outerjoin(
                    OrganizationMember,
                    (OrganizationMember.user_id == OperatorUser.id) & _ACTIVE_MEMBERSHIP,
                )
                .outerjoin(Organization, Organization.id == OrganizationMember.organization_id)
                .outerjoin(Department, Department.id == OrganizationMember.department_id)
                .outerjoin(Role, Role.id == OrganizationMember.role_id)
            )
            if scope.organization_id is not None:
                statement = statement.where(OrganizationMember.organization_id == scope.organization_id)
            if city and scope.is_admin:
                statement = statement.where(Organization.city == city)
            statement = statement.order_by(OperatorUser.login).limit(limit).offset(offset)
            rows = (await db_session.execute(statement)).all()
            return [
                OperatorUserSummary(
                    id=row.id,
                    login=row.login,
                    display_name=row.display_name,
                    email=row.email,
                    is_active=row.is_active,
                    organization_id=row.organization_id,
                    organization_name=row.organization_name,
                    organization_city=row.organization_city,
                    department_id=row.department_id,
                    department_name=row.department_name,
                    role_code=row.role_code,
                )
                for row in rows
            ]

    @get(
        "/{item_id:uuid}",
        name="identity:OperatorUser:get",
        guards=[require_roles(*STAFF_ROLES)],
    )
    async def get_item(
        self,
        item_id: FromPath[UUID],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> OperatorUserSummary:
        scope = resolve_organization_scope(principal)
        if scope.sees_nothing:
            raise NotFoundException(f"Operator user {item_id} was not found")
        with database_action("get", "identity.OperatorUser"):
            statement = (
                select(
                    OperatorUser.id,
                    OperatorUser.login,
                    OperatorUser.display_name,
                    OperatorUser.email,
                    OperatorUser.is_active,
                    OrganizationMember.organization_id,
                    Organization.name.label("organization_name"),
                    Organization.city.label("organization_city"),
                    OrganizationMember.department_id,
                    Department.name.label("department_name"),
                    Role.code.label("role_code"),
                )
                .select_from(OperatorUser)
                .outerjoin(
                    OrganizationMember,
                    (OrganizationMember.user_id == OperatorUser.id) & _ACTIVE_MEMBERSHIP,
                )
                .outerjoin(Organization, Organization.id == OrganizationMember.organization_id)
                .outerjoin(Department, Department.id == OrganizationMember.department_id)
                .outerjoin(Role, Role.id == OrganizationMember.role_id)
                .where(OperatorUser.id == item_id)
            )
            if scope.organization_id is not None:
                statement = statement.where(OrganizationMember.organization_id == scope.organization_id)
            row = (await db_session.execute(statement)).first()
            if row is None:
                raise NotFoundException(f"Operator user {item_id} was not found")
            return OperatorUserSummary(
                id=row.id,
                login=row.login,
                display_name=row.display_name,
                email=row.email,
                is_active=row.is_active,
                organization_id=row.organization_id,
                organization_name=row.organization_name,
                organization_city=row.organization_city,
                department_id=row.department_id,
                department_name=row.department_name,
                role_code=row.role_code,
            )
