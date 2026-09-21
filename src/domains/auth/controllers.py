from litestar import Controller, Router, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import HTTPException, NotAuthorizedException, NotFoundException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.auth.schemas import (
    ResidentAuthenticateRequest,
    ResidentAuthenticateResponse,
    ResidentTokenRequest,
    ResidentTokenResponse,
    StaffLinkMaxIdRequest,
    StaffLinkMaxIdResponse,
    StaffLoginRequest,
    StaffLoginResponse,
    StaffRegisterRequest,
    StaffRegisterResponse,
)
from src.domains.identity.models import OperatorUser, Resident
from src.domains.identity.services import OperatorUserService, ResidentService
from src.security.dependency import provide_principal
from src.security.guards import RESIDENT_TOKEN_ISSUER, require_bot_secret, require_roles, require_staff
from src.security.keycloak import KeycloakLoginError, login_staff_with_password
from src.security.keycloak_admin import KeycloakAdminError, create_staff_user
from src.security.principal import Principal
from src.security.resident import resident_jwt_auth
from src.security.settings import SecuritySettings


def provide_resident_service(db_session: NamedDependency[AsyncSession]) -> ResidentService:
    return ResidentService(session=db_session, auto_commit=True)


def provide_operator_user_service(db_session: NamedDependency[AsyncSession]) -> OperatorUserService:
    return OperatorUserService(session=db_session, auto_commit=True)


class ResidentAuthController(Controller):
    """Auth endpoints for the resident-facing bot only.

    Residents never provide a login/password themselves; the bot is the only client
    here, authenticating itself with a shared secret (``X-Bot-Secret``). The flow is
    two steps on purpose: ``authenticate`` registers/updates the resident, ``token``
    mints a fresh JWT for an already-known one - so the bot can refresh a token
    without repeating registration every time.
    """

    path = "/auth/residents"
    tags = ("auth",)
    guards = (require_bot_secret(),)

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"service": Provide(provide_resident_service, sync_to_thread=False)}

    @post("/authenticate", name="auth:Resident:authenticate")
    async def authenticate(
        self, data: ResidentAuthenticateRequest, service: NamedDependency[ResidentService]
    ) -> ResidentAuthenticateResponse:
        with database_action("upsert", "identity.Resident"):
            resident = await service.get_one_or_none(max_user_id=data.max_user_id)
            if resident is None:
                resident = await service.create(
                    Resident(
                        max_user_id=data.max_user_id,
                        username=data.username,
                        display_name=data.display_name,
                    )
                )
            elif data.username != resident.username or data.display_name != resident.display_name:
                resident = await service.update(
                    {"username": data.username, "display_name": data.display_name}, item_id=resident.id
                )
        return ResidentAuthenticateResponse(
            resident_id=str(resident.id),
            max_user_id=resident.max_user_id,
            username=resident.username,
            display_name=resident.display_name,
        )

    @post("/token", name="auth:Resident:token")
    async def issue_token(
        self, data: ResidentTokenRequest, service: NamedDependency[ResidentService]
    ) -> ResidentTokenResponse:
        with database_action("get", "identity.Resident"):
            resident = await service.get_one_or_none(max_user_id=data.max_user_id)
        if resident is None:
            raise NotFoundException("Resident is not registered; call /auth/residents/authenticate first")

        settings = SecuritySettings.from_environment()
        token = resident_jwt_auth(settings).create_token(
            identifier=str(resident.id), token_issuer=RESIDENT_TOKEN_ISSUER
        )
        return ResidentTokenResponse(token=token, resident_id=str(resident.id))


class StaffAuthController(Controller):
    """Auth endpoints for staff (admin / жилищник / управа).

    Staff identity and credentials live in Keycloak (optionally LDAP-federated) - this
    controller only proxies a password grant and, for registration, the Admin REST API,
    so that every client (including a future staff frontend) only ever talks to our API.
    """

    path = "/auth/staff"
    tags = ("auth",)

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "operator_service": Provide(provide_operator_user_service, sync_to_thread=False),
            "principal": Provide(provide_principal),
        }

    @post("/login", name="auth:Staff:login")
    async def login(self, data: StaffLoginRequest) -> StaffLoginResponse:
        settings = SecuritySettings.from_environment()
        try:
            tokens = await login_staff_with_password(settings, username=data.username, password=data.password)
        except KeycloakLoginError as exc:
            raise NotAuthorizedException(str(exc)) from exc
        return StaffLoginResponse(
            token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            expires_in=tokens.get("expires_in"),
        )

    @post("/register", name="auth:Staff:register", guards=[require_roles("admin")])
    async def register(
        self, data: StaffRegisterRequest, operator_service: NamedDependency[OperatorUserService]
    ) -> StaffRegisterResponse:
        settings = SecuritySettings.from_environment()
        try:
            subject = await create_staff_user(
                settings,
                login=data.login,
                password=data.password,
                email=data.email,
                display_name=data.display_name,
                role=data.role,
            )
        except KeycloakAdminError as exc:
            raise HTTPException(status_code=409 if exc.conflict else 502, detail=str(exc)) from exc

        with database_action("create", "identity.OperatorUser"):
            operator = await operator_service.create(
                OperatorUser(
                    login=data.login,
                    display_name=data.display_name,
                    email=data.email,
                    keycloak_subject=subject,
                )
            )
        return StaffRegisterResponse(
            operator_id=str(operator.id),
            login=operator.login,
            display_name=operator.display_name,
            role=data.role,
        )

    @post("/max-id", name="auth:Staff:link-max-id", guards=[require_staff()])
    async def link_max_id(
        self,
        data: StaffLinkMaxIdRequest,
        principal: NamedDependency[Principal],
        operator_service: NamedDependency[OperatorUserService],
    ) -> StaffLinkMaxIdResponse:
        with database_action("update", "identity.OperatorUser"):
            operator = await operator_service.update(
                {"max_user_id": data.max_user_id}, item_id=principal.actor_id
            )
        return StaffLinkMaxIdResponse(operator_id=str(operator.id), max_user_id=data.max_user_id)
