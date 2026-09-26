from uuid import UUID, uuid4

from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.geo.models import AdministrativeArea
from src.domains.identity.admin_scope import AUTHORITY_ROLE, is_platform_admin
from src.domains.identity.enums import BotStatus, OrganizationRegistrationStatus, OrganizationType
from src.domains.identity.models import (
    Department,
    OperatorUser,
    Organization,
    OrganizationMember,
    Resident,
    Role,
)
from src.domains.identity.repositories import (
    DepartmentRepository,
    OperatorUserRepository,
    OrganizationMemberRepository,
    OrganizationRepository,
    ResidentRepository,
)
from src.domains.identity.schemas import (
    AuthorityRegistrationRequest,
    OrganizationMemberCreateRequest,
    OrganizationRegistrationRequest,
    StaffAccountRequest,
)
from src.domains.identity.validation import (
    OrganizationRequisitesError,
    is_valid_inn,
    is_valid_ogrn,
    validate_housing_requisites,
)
from src.domains.incidents.scope import visible_organization_ids
from src.domains.infrastructure.models import OutboxEvent
from src.security.keycloak_admin import create_staff_user
from src.security.principal import Principal
from src.security.settings import SecuritySettings

HOUSING_WORKER_ROLE = "housing_worker"
DISTRICT_ADMIN_ROLE = "district_admin"


def staff_role_for(organization_type: OrganizationType) -> str:
    """The staff role a new employee of this organization gets - both the Keycloak realm
    role (what guards check) and the local membership role: the district administration's
    people are ``district_admin`` (Управа), everyone else ``housing_worker``."""
    if organization_type is OrganizationType.ADMINISTRATION:
        return DISTRICT_ADMIN_ROLE
    return HOUSING_WORKER_ROLE


MIN_PASSWORD_LENGTH = 8


class IdentityNotFoundError(RuntimeError):
    pass


class IdentityConflictError(RuntimeError):
    pass


class IdentityForbiddenError(RuntimeError):
    pass


class StaffAccountError(ValueError):
    """The requested employee account is invalid (e.g. the password is too short)."""


def _clean(value: str | None) -> str | None:
    return value.strip() or None if value is not None else None


class OrganizationService(SQLAlchemyAsyncRepositoryService[Organization]):
    repository_type = OrganizationRepository

    def directory_criteria(self, principal: Principal) -> list[ColumnElement[bool]] | None:
        if is_platform_admin(principal):
            return []
        if principal.organization_id is None:
            return None
        if principal.has_role(AUTHORITY_ROLE):
            return [Organization.id.in_(visible_organization_ids(principal.organization_id))]
        return [Organization.id == principal.organization_id]

    async def is_visible_to(self, organization_id: UUID, principal: Principal) -> bool:
        criteria = self.directory_criteria(principal)
        if criteria is None:
            return False
        found = await self.repository.session.scalar(
            select(Organization.id).where(Organization.id == organization_id, *criteria)
        )
        return found is not None

    async def register_authority(
        self, data: AuthorityRegistrationRequest, *, registered_by: UUID
    ) -> tuple[Organization, OrganizationMember]:
        session = self.repository.session
        name = " ".join(data.name.split())
        if not name:
            raise StaffAccountError("Authority name is required")
        inn, ogrn = _clean(data.inn), _clean(data.ogrn)
        if inn is not None and not is_valid_inn(inn):
            raise OrganizationRequisitesError("INN is invalid")
        if ogrn is not None and not is_valid_ogrn(ogrn):
            raise OrganizationRequisitesError("OGRN is invalid")
        territory = await session.get(AdministrativeArea, data.territory_id)
        if territory is None:
            raise IdentityNotFoundError(f"Territory {data.territory_id} was not found")
        duplicate = await session.scalar(
            select(Organization.id).where(
                Organization.territory_id == territory.id, Organization.authority_kind == data.authority_kind
            )
        )
        if duplicate is not None:
            raise IdentityConflictError("This territory already has an authority of this kind")
        if inn is not None and await session.scalar(select(Organization.id).where(Organization.inn == inn)):
            raise IdentityConflictError(f"An organization with INN {inn} is already registered")
        await _ensure_account_available(session, data.employee)
        city = territory
        while city.parent_id is not None:
            parent = await session.get(AdministrativeArea, city.parent_id)
            if parent is None:
                break
            city = parent
        organization = Organization(
            code=f"authority-{uuid4().hex[:12]}",
            name=name,
            type=OrganizationType.ADMINISTRATION,
            authority_kind=data.authority_kind,
            territory_id=territory.id,
            city=city.name,
            inn=inn,
            ogrn=ogrn,
            registration_status=OrganizationRegistrationStatus.APPROVED,
            enabled=True,
        )
        session.add(organization)
        await session.flush()
        role_id = await _role_id(session, DISTRICT_ADMIN_ROLE)
        member = await _create_member_account(
            session, organization.id, role_id, DISTRICT_ADMIN_ROLE, data.employee
        )
        session.add(
            OutboxEvent(
                aggregate_type="ORGANIZATION",
                aggregate_id=organization.id,
                event_type="ORGANIZATION_REGISTERED",
                payload={
                    "organization_id": str(organization.id),
                    "type": organization.type.value,
                    "authority_kind": data.authority_kind.value,
                    "territory_id": str(territory.id),
                    "employee_id": str(member.user_id),
                    "registered_by": str(registered_by),
                },
            )
        )
        await session.flush()
        return organization, member

    async def register_with_employee(
        self, data: OrganizationRegistrationRequest, *, registered_by: UUID
    ) -> tuple[Organization, OrganizationMember]:
        """Admin-only: create an active housing organization and its first employee (a new
        Keycloak login attached as ``housing_worker``). Everything that can be checked
        locally is checked before the Keycloak account is created, so a rejected request
        leaves no orphaned login behind."""
        session = self.repository.session
        inn, ogrn = data.inn.strip(), data.ogrn.strip()
        license_number = _clean(data.license_number)
        validate_housing_requisites(
            organization_type=data.type,
            inn=inn,
            ogrn=ogrn,
            license_number=license_number,
            in_reserve_registry=data.in_reserve_registry,
        )
        code = data.code.strip()
        if await session.scalar(select(Organization.id).where(Organization.code == code)) is not None:
            raise IdentityConflictError(f"Organization code {code!r} is already taken")
        if await session.scalar(select(Organization.id).where(Organization.inn == inn)) is not None:
            raise IdentityConflictError(f"An organization with INN {inn} is already registered")
        await _ensure_account_available(session, data.employee)
        role_id = await _role_id(session, HOUSING_WORKER_ROLE)

        organization = Organization(
            code=code,
            name=data.name.strip(),
            type=data.type,
            city=_clean(data.city),
            inn=inn,
            ogrn=ogrn,
            license_number=license_number,
            in_reserve_registry=data.in_reserve_registry,
            registration_status=OrganizationRegistrationStatus.APPROVED,
            enabled=True,
        )
        session.add(organization)
        await session.flush()
        member = await _create_member_account(
            session, organization.id, role_id, HOUSING_WORKER_ROLE, data.employee
        )
        session.add(
            OutboxEvent(
                aggregate_type="ORGANIZATION",
                aggregate_id=organization.id,
                event_type="ORGANIZATION_REGISTERED",
                payload={
                    "organization_id": str(organization.id),
                    "type": organization.type.value,
                    "inn": inn,
                    "employee_id": str(member.user_id),
                    "registered_by": str(registered_by),
                },
            )
        )
        await session.flush()
        return organization, member


async def _role_id(session: AsyncSession, code: str) -> UUID:
    role_id = await session.scalar(select(Role.id).where(Role.code == code))
    if role_id is None:
        raise IdentityNotFoundError(f"Role {code!r} is not seeded")
    return role_id


async def _ensure_account_available(session: AsyncSession, account: StaffAccountRequest) -> None:
    if not account.login.strip() or not account.display_name.strip():
        raise StaffAccountError("Employee login and name are required")
    if len(account.password) < MIN_PASSWORD_LENGTH:
        raise StaffAccountError(f"Employee password must be at least {MIN_PASSWORD_LENGTH} characters")
    login = account.login.strip()
    if await session.scalar(select(OperatorUser.id).where(OperatorUser.login == login)) is not None:
        raise IdentityConflictError(f"Login {login!r} is already taken")


async def _create_member_account(
    session: AsyncSession,
    organization_id: UUID,
    role_id: UUID,
    role_code: str,
    account: StaffAccountRequest,
) -> OrganizationMember:
    """Create the Keycloak login (last, after every local check) and attach it to the
    organization as an active member."""
    login = account.login.strip()
    display_name = account.display_name.strip()
    email = _clean(account.email)
    subject = await create_staff_user(
        SecuritySettings.from_environment(),
        login=login,
        password=account.password,
        email=email,
        display_name=display_name,
        role=role_code,
    )
    operator = OperatorUser(login=login, display_name=display_name, email=email, keycloak_subject=subject)
    session.add(operator)
    await session.flush()
    member = OrganizationMember(organization_id=organization_id, user_id=operator.id, role_id=role_id)
    session.add(member)
    await session.flush()
    return member


class OrganizationMemberService(SQLAlchemyAsyncRepositoryService[OrganizationMember]):
    repository_type = OrganizationMemberRepository

    async def add(
        self,
        organization_id: UUID,
        data: OrganizationMemberCreateRequest,
        *,
        allow_any_role: bool,
    ) -> OrganizationMember:
        """Attach an existing staff account to an approved organization (or re-activate a
        previous membership). Only a platform ``admin`` may grant a role other than
        ``housing_worker``."""
        session = self.repository.session
        organization = await session.get(Organization, organization_id)
        if organization is None:
            raise IdentityNotFoundError(f"Organization {organization_id} was not found")
        if organization.registration_status is not OrganizationRegistrationStatus.APPROVED:
            raise IdentityConflictError("Members can only be added to an approved organization")
        if await session.get(OperatorUser, data.user_id) is None:
            raise IdentityNotFoundError(f"Operator user {data.user_id} was not found")
        role = await session.scalar(select(Role).where(Role.code == data.role_code))
        if role is None:
            raise IdentityNotFoundError(f"Role {data.role_code!r} was not found")
        if not allow_any_role and role.code != HOUSING_WORKER_ROLE:
            raise IdentityForbiddenError(f"Only an admin can grant role {role.code!r}")
        if data.department_id is not None:
            department = await session.get(Department, data.department_id)
            if department is None or department.organization_id != organization.id:
                raise IdentityNotFoundError(
                    f"Department {data.department_id} was not found in this organization"
                )
        elsewhere = await session.scalar(
            select(OrganizationMember.id).where(
                OrganizationMember.user_id == data.user_id,
                OrganizationMember.organization_id != organization.id,
                OrganizationMember.is_active.is_(True),
            )
        )
        if elsewhere is not None:
            raise IdentityConflictError("The user is already an active member of another organization")

        member = await session.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization.id,
                OrganizationMember.user_id == data.user_id,
            )
        )
        if member is None:
            member = OrganizationMember(
                organization_id=organization.id, user_id=data.user_id, role_id=role.id
            )
            session.add(member)
        member.role_id = role.id
        member.department_id = data.department_id
        member.is_active = True
        await session.flush()
        return member

    async def create_account(self, organization_id: UUID, account: StaffAccountRequest) -> OrganizationMember:
        """A brand-new employee login attached straight to the organization - by an admin,
        or by a colleague registering them (the caller's scope is checked by the
        controller). The role follows the organization, see ``staff_role_for``."""
        session = self.repository.session
        organization = await session.get(Organization, organization_id)
        if organization is None:
            raise IdentityNotFoundError(f"Organization {organization_id} was not found")
        if not organization.enabled:
            raise IdentityConflictError("The organization is disabled")
        await _ensure_account_available(session, account)
        role_code = staff_role_for(organization.type)
        role_id = await _role_id(session, role_code)
        return await _create_member_account(session, organization.id, role_id, role_code, account)

    async def deactivate(self, organization_id: UUID, member_id: UUID) -> OrganizationMember:
        member = await self.repository.session.scalar(
            select(OrganizationMember).where(
                OrganizationMember.id == member_id,
                OrganizationMember.organization_id == organization_id,
            )
        )
        if member is None:
            raise IdentityNotFoundError(f"Member {member_id} was not found in this organization")
        member.is_active = False
        await self.repository.session.flush()
        return member


class DepartmentService(SQLAlchemyAsyncRepositoryService[Department]):
    repository_type = DepartmentRepository


class ResidentService(SQLAlchemyAsyncRepositoryService[Resident]):
    repository_type = ResidentRepository

    async def upsert_by_max_user_id(
        self,
        *,
        max_user_id: int,
        username: str | None,
        display_name: str | None,
        chat_id: int | None = None,
    ) -> Resident:
        """Shared by the bot-token auth endpoint and the MAX webhook handler - both
        identify a resident purely by their MAX ``max_user_id``, no login/password.
        ``chat_id`` is the resident's dialog with the bot (from ``/start``): stored, and
        the bot counts as started again."""
        resident = await self.get_one_or_none(max_user_id=max_user_id)
        if resident is None:
            return await self.create(
                Resident(
                    max_user_id=max_user_id, username=username, display_name=display_name, max_chat_id=chat_id
                )
            )
        updates: dict[str, object] = {}
        if username != resident.username or display_name != resident.display_name:
            updates |= {"username": username, "display_name": display_name}
        if chat_id is not None:
            if chat_id != resident.max_chat_id:
                updates["max_chat_id"] = chat_id
            if resident.bot_status is not BotStatus.STARTED:
                updates["bot_status"] = BotStatus.STARTED
        if updates:
            return await self.update(updates, item_id=resident.id)
        return resident

    async def remember_chat(self, *, max_user_id: int, chat_id: int) -> None:
        """Any message in the dialog with the bot: a known resident without a stored chat
        gets it saved. Never registers anyone (``/id`` is asked by staff too)."""
        resident = await self.get_one_or_none(max_user_id=max_user_id)
        if resident is not None and resident.max_chat_id is None:
            await self.update({"max_chat_id": chat_id}, item_id=resident.id)

    async def mark_bot_stopped(self, *, max_user_id: int) -> None:
        """The resident blocked/stopped the bot - MAX would reject messages to them."""
        resident = await self.get_one_or_none(max_user_id=max_user_id)
        if resident is not None and resident.bot_status is not BotStatus.STOPPED:
            await self.update({"bot_status": BotStatus.STOPPED}, item_id=resident.id)


class OperatorUserService(SQLAlchemyAsyncRepositoryService[OperatorUser]):
    repository_type = OperatorUserRepository
