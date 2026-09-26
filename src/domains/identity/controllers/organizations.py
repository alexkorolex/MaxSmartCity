"""Organizations directory, and an admin registering a УК/ТСЖ with its first employee."""

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.dto import DTOData
from litestar.exceptions import ClientException, HTTPException, NotFoundException
from litestar.params import FromPath, Parameter
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.identity.admin_scope import STAFF_ROLES
from src.domains.identity.controllers.members import OrganizationMemberController
from src.domains.identity.credentials import send_credentials_email
from src.domains.identity.enums import OrganizationRegistrationStatus
from src.domains.identity.models import (
    Organization,
)
from src.domains.identity.schemas import (
    AuthorityRegistrationRequest,
    OrganizationCreateDTO,
    OrganizationReadDTO,
    OrganizationRegistrationRequest,
    OrganizationRegistrationResult,
    OrganizationUpdateDTO,
)
from src.domains.identity.services import (
    IdentityConflictError,
    IdentityNotFoundError,
    OrganizationService,
    StaffAccountError,
)
from src.domains.identity.validation import OrganizationRequisitesError
from src.security.dependency import provide_principal
from src.security.guards import require_roles
from src.security.keycloak_admin import KeycloakAdminError
from src.security.principal import Principal


def provide_organization_service(db_session: NamedDependency[AsyncSession]) -> OrganizationService:
    return OrganizationService(session=db_session, auto_commit=True)


@asynccontextmanager
async def _registration_errors() -> AsyncIterator[None]:
    try:
        yield
    except (OrganizationRequisitesError, StaffAccountError) as exc:
        raise ClientException(status_code=400, detail=str(exc)) from exc
    except IdentityNotFoundError as exc:
        raise NotFoundException(str(exc)) from exc
    except IdentityConflictError as exc:
        raise ClientException(status_code=409, detail=str(exc)) from exc
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=409 if exc.conflict else 502, detail=str(exc)) from exc


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

    @get("/", name="identity:Organization:list", guards=[require_roles(*STAFF_ROLES)])
    async def list_items(
        self,
        service: NamedDependency[OrganizationService],
        principal: NamedDependency[Principal],
        registration_status: Annotated[OrganizationRegistrationStatus | None, Parameter()] = None,
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Organization]:
        with database_action("list", "identity.Organization"):
            criteria = service.directory_criteria(principal)
            if criteria is None:
                return []
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
            async with _registration_errors():
                organization, member = await OrganizationService(session=db_session).register_with_employee(
                    data, registered_by=principal.actor_id
                )
            await db_session.commit()
            employee = await OrganizationMemberController.load_summary(db_session, member.id)
        credentials_email = await send_credentials_email(
            email=data.employee.email,
            display_name=employee.display_name,
            login=employee.login,
            password=data.employee.password,
            organization_name=organization.name,
        )
        return OrganizationRegistrationResult(
            organization_id=organization.id, employee=employee, credentials_email=credentials_email
        )

    @post(
        "/authorities",
        return_dto=None,
        name="identity:Organization:register-authority",
        guards=[require_roles("admin")],
    )
    async def register_authority(
        self,
        data: AuthorityRegistrationRequest,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> OrganizationRegistrationResult:
        with database_action("create", "identity.Organization"):
            async with _registration_errors():
                organization, member = await OrganizationService(session=db_session).register_authority(
                    data, registered_by=principal.actor_id
                )
            await db_session.commit()
            employee = await OrganizationMemberController.load_summary(db_session, member.id)
        credentials_email = await send_credentials_email(
            email=data.employee.email,
            display_name=employee.display_name,
            login=employee.login,
            password=data.employee.password,
            organization_name=organization.name,
        )
        return OrganizationRegistrationResult(
            organization_id=organization.id, employee=employee, credentials_email=credentials_email
        )

    @get("/{item_id:uuid}", name="identity:Organization:get", guards=[require_roles(*STAFF_ROLES)])
    async def get_item(
        self,
        item_id: FromPath[UUID],
        service: NamedDependency[OrganizationService],
        principal: NamedDependency[Principal],
    ) -> Organization:
        with database_action("get", "identity.Organization"):
            if not await service.is_visible_to(item_id, principal):
                raise NotFoundException(f"Organization {item_id} was not found")
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
