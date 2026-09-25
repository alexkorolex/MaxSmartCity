"""Who works for an organization: its roster, registering colleagues, deactivating."""

from collections.abc import Sequence
from typing import Annotated, Any
from uuid import UUID

from litestar import Controller, Router, get, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ClientException, HTTPException, NotFoundException, PermissionDeniedException
from litestar.params import FromPath, Parameter
from sqlalchemy import Row, Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.identity.admin_scope import STAFF_ROLES, is_platform_admin, resolve_organization_scope
from src.domains.identity.credentials import send_credentials_email
from src.domains.identity.models import (
    Department,
    OperatorUser,
    Organization,
    OrganizationMember,
    Role,
)
from src.domains.identity.schemas import (
    OrganizationMemberCreateRequest,
    OrganizationMemberSummary,
    StaffAccountCreatedResult,
    StaffAccountRequest,
)
from src.domains.identity.services import (
    IdentityConflictError,
    IdentityForbiddenError,
    IdentityNotFoundError,
    OrganizationMemberService,
    StaffAccountError,
)
from src.security.dependency import provide_principal
from src.security.guards import require_roles
from src.security.keycloak_admin import KeycloakAdminError
from src.security.principal import Principal


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

    @get("/", name="identity:OrganizationMember:list", guards=[require_roles(*STAFF_ROLES)])
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

    @post("/", name="identity:OrganizationMember:add", guards=[require_roles(*STAFF_ROLES)])
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
        guards=[require_roles(*STAFF_ROLES)],
    )
    async def create_account(
        self,
        organization_id: FromPath[UUID],
        data: StaffAccountRequest,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> StaffAccountCreatedResult:
        """Create a new employee login directly inside the organization and e-mail them
        their sign-in details - by an ``admin`` for any organization, or by staff for
        their own one (registering a colleague)."""
        if resolve_organization_scope(principal, organization_id).sees_nothing:
            raise PermissionDeniedException("No active organization membership")
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
            summary = await self.load_summary(db_session, member.id)
            organization_name = await db_session.scalar(
                select(Organization.name).where(Organization.id == organization_id)
            )
        credentials_email = await send_credentials_email(
            email=data.email,
            display_name=summary.display_name,
            login=summary.login,
            password=data.password,
            organization_name=organization_name or "",
        )
        return StaffAccountCreatedResult(member=summary, credentials_email=credentials_email)

    @post(
        "/{member_id:uuid}/deactivate",
        status_code=200,
        name="identity:OrganizationMember:deactivate",
        guards=[require_roles(*STAFF_ROLES)],
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
            own_membership = await db_session.scalar(
                select(OrganizationMember.id).where(
                    OrganizationMember.id == member_id, OrganizationMember.user_id == principal.actor_id
                )
            )
            if own_membership is not None:
                raise ClientException(status_code=409, detail="You cannot deactivate your own membership")
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
