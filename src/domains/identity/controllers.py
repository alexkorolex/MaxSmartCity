from collections.abc import Sequence
from typing import Annotated, Any
from uuid import UUID

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.dto import DTOData
from litestar.exceptions import ClientException, HTTPException, NotFoundException, PermissionDeniedException
from litestar.params import FromPath, Parameter
from sqlalchemy import Row, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.geo.models import Address, House
from src.domains.identity.admin_scope import is_platform_admin, resolve_organization_scope
from src.domains.identity.enums import OrganizationRegistrationStatus
from src.domains.identity.models import (
    Department,
    OperatorUser,
    Organization,
    OrganizationMember,
    Resident,
    Role,
)
from src.domains.identity.schemas import (
    DepartmentCreateDTO,
    DepartmentReadDTO,
    DepartmentUpdateDTO,
    OperatorUserSummary,
    OrganizationCreateDTO,
    OrganizationMemberCreateRequest,
    OrganizationMemberSummary,
    OrganizationReadDTO,
    OrganizationRegistrationRequest,
    OrganizationRegistrationResult,
    OrganizationUpdateDTO,
    PrincipalRead,
    ResidentReadDTO,
    ResidentSelfUpdateRequest,
    ResidentSummary,
    StaffAccountRequest,
)
from src.domains.identity.services import (
    DepartmentService,
    IdentityConflictError,
    IdentityForbiddenError,
    IdentityNotFoundError,
    OrganizationMemberService,
    OrganizationService,
    ResidentService,
    StaffAccountError,
)
from src.domains.identity.validation import OrganizationRequisitesError
from src.domains.incidents.scope import organization_resident_ids
from src.domains.reports.models import Report
from src.security.dependency import provide_principal
from src.security.guards import require_resident, require_roles
from src.security.keycloak_admin import KeycloakAdminError
from src.security.principal import Principal


def provide_organization_service(db_session: NamedDependency[AsyncSession]) -> OrganizationService:
    return OrganizationService(session=db_session, auto_commit=True)


def provide_department_service(db_session: NamedDependency[AsyncSession]) -> DepartmentService:
    return DepartmentService(session=db_session, auto_commit=True)


_STAFF_ADMIN_ROLES = ("admin", "district_admin", "housing_worker")


_ORGANIZATION_DIRECTORY_ROLES = ("admin", "district_admin")
"""May browse every organization: the platform admin, and the district administration
(Управа) that appoints managers for houses. A ``housing_worker`` only ever sees their own
organization - never other УК/ТСЖ."""


class OrganizationController(Controller):
    """Organizations directory. Reads are staff-only and scoped (see
    ``_ORGANIZATION_DIRECTORY_ROLES``); every mutation is ``admin``-only."""

    path = "/identity/organizations"
    tags = ("identity",)
    return_dto = OrganizationReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "service": Provide(provide_organization_service, sync_to_thread=False),
            "principal": Provide(provide_principal),
        }

    @get("/", name="identity:Organization:list", guards=[require_roles(*_STAFF_ADMIN_ROLES)])
    async def list_items(
        self,
        service: NamedDependency[OrganizationService],
        principal: NamedDependency[Principal],
        registration_status: Annotated[OrganizationRegistrationStatus | None, Parameter()] = None,
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Organization]:
        with database_action("list", "identity.Organization"):
            criteria = []
            if not principal.has_role(*_ORGANIZATION_DIRECTORY_ROLES):
                if principal.organization_id is None:
                    return []
                criteria.append(Organization.id == principal.organization_id)
            if registration_status is not None:
                criteria.append(Organization.registration_status == registration_status)
            return await service.get_many(
                LimitOffset(limit=limit, offset=offset), *criteria, order_by=("id", False)
            )

    @post(
        "/register",
        return_dto=None,
        name="identity:Organization:register",
        guards=[require_roles("admin")],
    )
    async def register(
        self,
        data: OrganizationRegistrationRequest,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> OrganizationRegistrationResult:
        """Register a management company / HOA together with its first employee (a new
        staff login). Admin-only: the organization is active immediately."""
        with database_action("create", "identity.Organization"):
            try:
                organization, member = await OrganizationService(session=db_session).register_with_employee(
                    data, registered_by=principal.actor_id
                )
            except (OrganizationRequisitesError, StaffAccountError) as exc:
                raise ClientException(status_code=400, detail=str(exc)) from exc
            except IdentityNotFoundError as exc:
                raise NotFoundException(str(exc)) from exc
            except IdentityConflictError as exc:
                raise ClientException(status_code=409, detail=str(exc)) from exc
            except KeycloakAdminError as exc:
                raise HTTPException(status_code=409 if exc.conflict else 502, detail=str(exc)) from exc
            await db_session.commit()
            return OrganizationRegistrationResult(
                organization_id=organization.id,
                employee=await OrganizationMemberController.load_summary(db_session, member.id),
            )

    @get("/{item_id:uuid}", name="identity:Organization:get", guards=[require_roles(*_STAFF_ADMIN_ROLES)])
    async def get_item(
        self,
        item_id: FromPath[UUID],
        service: NamedDependency[OrganizationService],
        principal: NamedDependency[Principal],
    ) -> Organization:
        if not principal.has_role(*_ORGANIZATION_DIRECTORY_ROLES) and item_id != principal.organization_id:
            raise NotFoundException(f"Organization {item_id} was not found")
        with database_action("get", "identity.Organization"):
            return await service.get(item_id)

    @post(
        "/",
        dto=OrganizationCreateDTO,
        name="identity:Organization:create",
        guards=[require_roles("admin")],
    )
    async def create_item(
        self, data: DTOData[Organization], service: NamedDependency[OrganizationService]
    ) -> Organization:
        with database_action("create", "identity.Organization"):
            return await service.create(data)

    @patch(
        "/{item_id:uuid}",
        dto=OrganizationUpdateDTO,
        name="identity:Organization:update",
        guards=[require_roles("admin")],
    )
    async def update_item(
        self,
        item_id: FromPath[UUID],
        data: DTOData[Organization],
        service: NamedDependency[OrganizationService],
    ) -> Organization:
        with database_action("update", "identity.Organization"):
            return await service.update(data, item_id=item_id)

    @delete(
        "/{item_id:uuid}",
        return_dto=None,
        name="identity:Organization:delete",
        guards=[require_roles("admin")],
    )
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


def _member_summary_statement() -> Select[Any]:
    return (
        select(
            OrganizationMember.id,
            OrganizationMember.organization_id,
            OrganizationMember.user_id,
            OperatorUser.login,
            OperatorUser.display_name,
            OperatorUser.email,
            OperatorUser.max_user_id.is_not(None).label("has_max_account"),
            OrganizationMember.department_id,
            Department.name.label("department_name"),
            Role.code.label("role_code"),
            OrganizationMember.is_active,
            OrganizationMember.created_at,
        )
        .select_from(OrganizationMember)
        .join(OperatorUser, OperatorUser.id == OrganizationMember.user_id)
        .join(Role, Role.id == OrganizationMember.role_id)
        .outerjoin(Department, Department.id == OrganizationMember.department_id)
    )


def _to_member_summary(row: Row[Any]) -> OrganizationMemberSummary:
    return OrganizationMemberSummary(
        id=row.id,
        organization_id=row.organization_id,
        user_id=row.user_id,
        login=row.login,
        display_name=row.display_name,
        email=row.email,
        has_max_account=row.has_max_account,
        department_id=row.department_id,
        department_name=row.department_name,
        role_code=row.role_code,
        is_active=row.is_active,
        created_at=row.created_at,
    )


class OrganizationMemberController(Controller):
    """Staff attached to an organization - who acts for a УК/ТСЖ and receives its
    ``MAX_MEMBERS`` notifications. ``admin`` manages any organization's roster; a
    ``district_admin``/``housing_worker`` only their own, and can only grant the
    ``housing_worker`` role."""

    path = "/identity/organizations/{organization_id:uuid}/members"
    tags = ("identity",)
    return_dto = None

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"principal": Provide(provide_principal)}

    @get("/", name="identity:OrganizationMember:list", guards=[require_roles(*_STAFF_ADMIN_ROLES)])
    async def list_items(
        self,
        organization_id: FromPath[UUID],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        include_inactive: Annotated[bool, Parameter()] = False,
    ) -> Sequence[OrganizationMemberSummary]:
        resolve_organization_scope(principal, organization_id)
        with database_action("list", "identity.OrganizationMember"):
            statement = _member_summary_statement().where(
                OrganizationMember.organization_id == organization_id
            )
            if not include_inactive:
                statement = statement.where(OrganizationMember.is_active.is_(True))
            rows = (await db_session.execute(statement.order_by(OperatorUser.login))).all()
            return [_to_member_summary(row) for row in rows]

    @post("/", name="identity:OrganizationMember:add", guards=[require_roles(*_STAFF_ADMIN_ROLES)])
    async def add_member(
        self,
        organization_id: FromPath[UUID],
        data: OrganizationMemberCreateRequest,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> OrganizationMemberSummary:
        resolve_organization_scope(principal, organization_id)
        with database_action("create", "identity.OrganizationMember"):
            try:
                member = await OrganizationMemberService(session=db_session).add(
                    organization_id, data, allow_any_role=is_platform_admin(principal)
                )
            except IdentityNotFoundError as exc:
                raise NotFoundException(str(exc)) from exc
            except IdentityForbiddenError as exc:
                raise PermissionDeniedException(str(exc)) from exc
            except IdentityConflictError as exc:
                raise ClientException(status_code=409, detail=str(exc)) from exc
            await db_session.commit()
            return await self.load_summary(db_session, member.id)

    @post(
        "/accounts",
        name="identity:OrganizationMember:create-account",
        guards=[require_roles("admin")],
    )
    async def create_account(
        self,
        organization_id: FromPath[UUID],
        data: StaffAccountRequest,
        db_session: NamedDependency[AsyncSession],
    ) -> OrganizationMemberSummary:
        """Admin-only: create a new employee login directly inside the organization."""
        with database_action("create", "identity.OrganizationMember"):
            try:
                member = await OrganizationMemberService(session=db_session).create_account(
                    organization_id, data
                )
            except StaffAccountError as exc:
                raise ClientException(status_code=400, detail=str(exc)) from exc
            except IdentityNotFoundError as exc:
                raise NotFoundException(str(exc)) from exc
            except IdentityConflictError as exc:
                raise ClientException(status_code=409, detail=str(exc)) from exc
            except KeycloakAdminError as exc:
                raise HTTPException(status_code=409 if exc.conflict else 502, detail=str(exc)) from exc
            await db_session.commit()
            return await self.load_summary(db_session, member.id)

    @post(
        "/{member_id:uuid}/deactivate",
        status_code=200,
        name="identity:OrganizationMember:deactivate",
        guards=[require_roles(*_STAFF_ADMIN_ROLES)],
    )
    async def deactivate_member(
        self,
        organization_id: FromPath[UUID],
        member_id: FromPath[UUID],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> OrganizationMemberSummary:
        resolve_organization_scope(principal, organization_id)
        with database_action("update", "identity.OrganizationMember"):
            try:
                await OrganizationMemberService(session=db_session).deactivate(organization_id, member_id)
            except IdentityNotFoundError as exc:
                raise NotFoundException(str(exc)) from exc
            await db_session.commit()
            return await self.load_summary(db_session, member_id)

    @staticmethod
    async def load_summary(db_session: AsyncSession, member_id: UUID) -> OrganizationMemberSummary:
        row = (
            await db_session.execute(_member_summary_statement().where(OrganizationMember.id == member_id))
        ).first()
        if row is None:
            raise NotFoundException(f"Member {member_id} was not found")
        return _to_member_summary(row)


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


# Outer join to the operator's *active* membership/organization/department/role - a staff
# member with no active membership still comes back (with those fields `None`) rather than
# being dropped, since this is a LEFT join, not INNER.
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

    @get("/", name="identity:OperatorUser:list", guards=[require_roles(*_STAFF_ADMIN_ROLES)])
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
        guards=[require_roles(*_STAFF_ADMIN_ROLES)],
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


class ResidentController(Controller):
    """Admin-panel resident directory. ``admin`` browses every resident; a
    ``district_admin``/``housing_worker`` only sees residents of their organization's
    houses and those whose reports it works on (``src.domains.incidents.scope``) - never
    another organization's residents."""

    path = "/identity/residents"
    tags = ("identity",)
    return_dto = None

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"principal": Provide(provide_principal)}

    @get("/", name="identity:Resident:list", guards=[require_roles(*_STAFF_ADMIN_ROLES)])
    async def list_items(
        self,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        city: Annotated[str | None, Parameter()] = None,
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[ResidentSummary]:
        scope = resolve_organization_scope(principal)
        if scope.sees_nothing:
            return []
        with database_action("list", "identity.Resident"):
            reports_count = (
                select(func.count(Report.id))
                .where(Report.resident_id == Resident.id)
                .correlate(Resident)
                .scalar_subquery()
            )
            statement = (
                select(
                    Resident.id,
                    Resident.display_name,
                    Resident.username,
                    Resident.max_user_id,
                    Resident.house_id,
                    Address.city.label("house_city"),
                    Address.formatted.label("house_formatted"),
                    reports_count.label("reports_count"),
                    Resident.created_at,
                )
                .select_from(Resident)
                .outerjoin(House, House.id == Resident.house_id)
                .outerjoin(Address, Address.id == House.address_id)
            )
            if city:
                statement = statement.where(Address.city == city)
            if not scope.is_admin:
                assert scope.organization_id is not None
                statement = statement.where(Resident.id.in_(organization_resident_ids(scope.organization_id)))
            statement = statement.order_by(Resident.created_at.desc()).limit(limit).offset(offset)
            rows = (await db_session.execute(statement)).all()
            return [
                ResidentSummary(
                    id=row.id,
                    display_name=row.display_name,
                    username=row.username,
                    max_user_id=row.max_user_id,
                    house_id=row.house_id,
                    house_city=row.house_city,
                    house_formatted=row.house_formatted,
                    reports_count=row.reports_count,
                    created_at=row.created_at,
                )
                for row in rows
            ]

    @get(
        "/{item_id:uuid}",
        name="identity:Resident:get",
        guards=[require_roles(*_STAFF_ADMIN_ROLES)],
    )
    async def get_item(
        self,
        item_id: FromPath[UUID],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> ResidentSummary:
        scope = resolve_organization_scope(principal)
        if scope.sees_nothing:
            raise NotFoundException(f"Resident {item_id} was not found")
        with database_action("get", "identity.Resident"):
            reports_count = (
                select(func.count(Report.id))
                .where(Report.resident_id == Resident.id)
                .correlate(Resident)
                .scalar_subquery()
            )
            statement = (
                select(
                    Resident.id,
                    Resident.display_name,
                    Resident.username,
                    Resident.max_user_id,
                    Resident.house_id,
                    Address.city.label("house_city"),
                    Address.formatted.label("house_formatted"),
                    reports_count.label("reports_count"),
                    Resident.created_at,
                )
                .select_from(Resident)
                .outerjoin(House, House.id == Resident.house_id)
                .outerjoin(Address, Address.id == House.address_id)
                .where(Resident.id == item_id)
            )
            if not scope.is_admin:
                assert scope.organization_id is not None
                statement = statement.where(Resident.id.in_(organization_resident_ids(scope.organization_id)))
            row = (await db_session.execute(statement)).first()
            if row is None:
                raise NotFoundException(f"Resident {item_id} was not found")
            return ResidentSummary(
                id=row.id,
                display_name=row.display_name,
                username=row.username,
                max_user_id=row.max_user_id,
                house_id=row.house_id,
                house_city=row.house_city,
                house_formatted=row.house_formatted,
                reports_count=row.reports_count,
                created_at=row.created_at,
            )
