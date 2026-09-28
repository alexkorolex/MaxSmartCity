import re
from typing import Any

import httpx
from litestar import Controller, Request, Response, Router, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import (
    ClientException,
    HTTPException,
    NotAuthorizedException,
    NotFoundException,
    PermissionDeniedException,
    ServiceUnavailableException,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.auth.schemas import (
    ResidentAuthenticateRequest,
    ResidentAuthenticateResponse,
    ResidentLoginRequest,
    ResidentTokenRequest,
    ResidentTokenResponse,
    ResidentWebAppLoginRequest,
    StaffInitialPasswordRequest,
    StaffLinkMaxIdRequest,
    StaffLinkMaxIdResponse,
    StaffLoginRequest,
    StaffLoginResponse,
    StaffLogoutRequest,
    StaffPasswordChangeRequest,
    StaffProfileRead,
    StaffProfileUpdateRequest,
    StaffRefreshRequest,
    StaffRegisterRequest,
    StaffRegisterResponse,
)
from src.domains.identity.models import Department, OperatorUser, Organization, OrganizationMember
from src.domains.identity.services import MIN_PASSWORD_LENGTH, OperatorUserService, ResidentService
from src.max_bot.dedup import consume_login_code
from src.max_bot.settings import MaxBotSettings
from src.max_bot.web_app import InvalidInitDataError, authenticate_web_app_resident
from src.security.dependency import provide_principal
from src.security.guards import (
    RESIDENT_TOKEN_ISSUER,
    STAFF_BOOTSTRAP_STATE_KEY,
    require_admin_or_bootstrap_secret,
    require_bot_secret,
    require_staff,
)
from src.security.keycloak import (
    KeycloakLoginError,
    KeycloakPasswordChangeRequired,
    login_staff_with_password,
    logout_staff,
    refresh_staff_tokens,
)
from src.security.keycloak_admin import (
    KeycloakAdminError,
    create_staff_user,
    set_staff_password,
    update_staff_user,
)
from src.security.principal import Principal
from src.security.resident import resident_jwt_auth
from src.security.settings import SecuritySettings
from src.security.staff_bootstrap import StaffBootstrapClosedError, ensure_bootstrap_allowed
from src.security.staff_password import (
    InitialPasswordError,
    PasswordChangeNotRequiredError,
    change_initial_password,
)
from src.security.staff_session import STAFF_REFRESH_COOKIE, expired_refresh_cookie, refresh_cookie


def _staff_tokens(tokens: dict[str, Any]) -> Response[StaffLoginResponse]:
    body = StaffLoginResponse(
        token=tokens["access_token"],
        refresh_token=None,
        expires_in=tokens.get("expires_in"),
        refresh_expires_in=tokens.get("refresh_expires_in"),
    )
    refresh_token = tokens.get("refresh_token")
    cookies = [refresh_cookie(refresh_token, tokens.get("refresh_expires_in"))] if refresh_token else []
    return Response(content=body, cookies=cookies)


def _refresh_token(request: Request, data: StaffRefreshRequest | StaffLogoutRequest | None) -> str | None:
    return request.cookies.get(STAFF_REFRESH_COOKIE) or (data.refresh_token if data else None)


_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_STAFF_ROLE_PRIORITY = ("admin", "district_admin", "housing_worker")


def _keycloak_admin_failure(exc: KeycloakAdminError) -> HTTPException:
    if exc.invalid:
        return ClientException(str(exc))
    return HTTPException(status_code=409 if exc.conflict else 502, detail=str(exc))


def _password_change_required() -> HTTPException:
    return PermissionDeniedException(
        "The temporary password must be changed", extra={"code": "password_change_required"}
    )


def provide_resident_service(db_session: NamedDependency[AsyncSession]) -> ResidentService:
    return ResidentService(session=db_session, auto_commit=True)


def provide_operator_user_service(db_session: NamedDependency[AsyncSession]) -> OperatorUserService:
    return OperatorUserService(session=db_session, auto_commit=True)


class ResidentAuthController(Controller):
    """Auth endpoints for residents.

    ``authenticate``/``token`` are called by the bot only (shared secret, ``X-Bot-Secret``)
    - residents never provide a login/password themselves. ``login`` is the odd one out:
    it is called by the resident's own browser, redeeming the single-use code the bot
    (or ``POST /webhook/max``, see ``src/max_bot``) handed them in chat, so it carries no
    bot-secret guard.
    """

    path = "/auth/residents"
    tags = ("auth",)

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"service": Provide(provide_resident_service, sync_to_thread=False)}

    @post("/authenticate", name="auth:Resident:authenticate", guards=[require_bot_secret()])
    async def authenticate(
        self, data: ResidentAuthenticateRequest, service: NamedDependency[ResidentService]
    ) -> ResidentAuthenticateResponse:
        with database_action("upsert", "identity.Resident"):
            resident = await service.upsert_by_max_user_id(
                max_user_id=data.max_user_id, username=data.username, display_name=data.display_name
            )
        return ResidentAuthenticateResponse(
            resident_id=str(resident.id),
            max_user_id=resident.max_user_id,
            username=resident.username,
            display_name=resident.display_name,
        )

    @post("/token", name="auth:Resident:token", guards=[require_bot_secret()])
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

    @post("/login", name="auth:Resident:login")
    async def login(
        self, data: ResidentLoginRequest, service: NamedDependency[ResidentService]
    ) -> ResidentTokenResponse:
        resident_id = await consume_login_code(data.code)
        if resident_id is None:
            raise NotAuthorizedException("Invalid or expired code")

        with database_action("get", "identity.Resident"):
            resident = await service.get_one_or_none(id=resident_id)
        if resident is None:
            raise NotFoundException("Resident no longer exists")

        settings = SecuritySettings.from_environment()
        token = resident_jwt_auth(settings).create_token(
            identifier=str(resident.id), token_issuer=RESIDENT_TOKEN_ISSUER
        )
        return ResidentTokenResponse(token=token, resident_id=str(resident.id))

    @post("/max-web-app", name="auth:Resident:max-web-app")
    async def login_via_max_web_app(
        self, data: ResidentWebAppLoginRequest, service: NamedDependency[ResidentService]
    ) -> ResidentTokenResponse:
        try:
            bot_token = MaxBotSettings.from_environment().bot_token
        except ValueError as exc:
            raise ServiceUnavailableException("MAX bot is not configured") from exc
        try:
            resident = await authenticate_web_app_resident(data.init_data, bot_token, service)
        except InvalidInitDataError as exc:
            raise NotAuthorizedException(str(exc)) from exc

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
    async def login(self, data: StaffLoginRequest) -> Response[StaffLoginResponse]:
        settings = SecuritySettings.from_environment()
        try:
            tokens = await login_staff_with_password(settings, username=data.username, password=data.password)
        except KeycloakPasswordChangeRequired as exc:
            raise _password_change_required() from exc
        except KeycloakLoginError as exc:
            raise NotAuthorizedException(str(exc)) from exc
        return _staff_tokens(tokens)

    @post("/initial-password", name="auth:Staff:initial-password")
    async def initial_password(self, data: StaffInitialPasswordRequest) -> Response[StaffLoginResponse]:
        settings = SecuritySettings.from_environment()
        try:
            tokens = await change_initial_password(
                settings, username=data.username, password=data.password, new_password=data.new_password
            )
        except InitialPasswordError as exc:
            raise ClientException(str(exc)) from exc
        except PasswordChangeNotRequiredError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except KeycloakAdminError as exc:
            raise _keycloak_admin_failure(exc) from exc
        except KeycloakLoginError as exc:
            raise NotAuthorizedException(str(exc)) from exc
        return _staff_tokens(tokens)

    @post("/refresh", name="auth:Staff:refresh")
    async def refresh(
        self, request: Request, data: StaffRefreshRequest | None = None
    ) -> Response[StaffLoginResponse]:
        """New access token for a still valid session (up to 24 hours after login) - no
        password. 401 once the session expired or was ended by ``/logout``."""
        refresh_token = _refresh_token(request, data)
        if not refresh_token:
            raise NotAuthorizedException("No staff session")
        settings = SecuritySettings.from_environment()
        try:
            tokens = await refresh_staff_tokens(settings, refresh_token=refresh_token)
        except KeycloakLoginError as exc:
            raise NotAuthorizedException(str(exc)) from exc
        return _staff_tokens(tokens)

    @post("/logout", status_code=204, name="auth:Staff:logout")
    async def logout(self, request: Request, data: StaffLogoutRequest | None = None) -> Response[None]:
        """End the session so the refresh token can't be used any more (e.g. on a shared
        computer) - dropping tokens in the browser alone would leave it valid for 24 hours."""
        refresh_token = _refresh_token(request, data)
        if refresh_token:
            try:
                await logout_staff(SecuritySettings.from_environment(), refresh_token=refresh_token)
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=502, detail="Could not reach the identity provider") from exc
        return Response(content=None, status_code=204, cookies=[expired_refresh_cookie()])

    @post("/register", name="auth:Staff:register", guards=[require_admin_or_bootstrap_secret()])
    async def register(
        self,
        request: Request,
        data: StaffRegisterRequest,
        operator_service: NamedDependency[OperatorUserService],
    ) -> StaffRegisterResponse:
        settings = SecuritySettings.from_environment()
        try:
            if request.state.get(STAFF_BOOTSTRAP_STATE_KEY):
                await ensure_bootstrap_allowed(settings, data.role)
            subject = await create_staff_user(
                settings,
                login=data.login,
                password=data.password,
                email=data.email,
                display_name=data.display_name,
                role=data.role,
            )
        except StaffBootstrapClosedError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except KeycloakAdminError as exc:
            raise _keycloak_admin_failure(exc) from exc

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

    @delete("/max-id", status_code=204, name="auth:Staff:unlink-max-id", guards=[require_staff()])
    async def unlink_max_id(
        self, principal: NamedDependency[Principal], operator_service: NamedDependency[OperatorUserService]
    ) -> None:
        with database_action("update", "identity.OperatorUser"):
            await operator_service.update({"max_user_id": None}, item_id=principal.actor_id)

    @get("/profile", name="auth:Staff:profile", guards=[require_staff()])
    async def get_profile(
        self, principal: NamedDependency[Principal], db_session: NamedDependency[AsyncSession]
    ) -> StaffProfileRead:
        return await _read_profile(db_session, principal)

    @patch("/profile", name="auth:Staff:profile-update", guards=[require_staff()])
    async def update_profile(
        self,
        data: StaffProfileUpdateRequest,
        principal: NamedDependency[Principal],
        db_session: NamedDependency[AsyncSession],
    ) -> StaffProfileRead:
        display_name = data.display_name.strip()
        email = (data.email or "").strip() or None
        if not display_name:
            raise ClientException("Name is required")
        if email is not None and not _EMAIL_PATTERN.match(email):
            raise ClientException("E-mail address is invalid")

        operator = await _own_operator(db_session, principal)
        if operator.keycloak_subject:
            try:
                await update_staff_user(
                    SecuritySettings.from_environment(),
                    subject=operator.keycloak_subject,
                    display_name=display_name,
                    email=email,
                )
            except KeycloakAdminError as exc:
                raise _keycloak_admin_failure(exc) from exc

        with database_action("update", "identity.OperatorUser"):
            operator.display_name = display_name
            operator.email = email
            await db_session.commit()
        return await _read_profile(db_session, principal)

    @post("/password", status_code=204, name="auth:Staff:password", guards=[require_staff()])
    async def change_password(
        self,
        data: StaffPasswordChangeRequest,
        principal: NamedDependency[Principal],
        db_session: NamedDependency[AsyncSession],
    ) -> None:
        if len(data.new_password) < MIN_PASSWORD_LENGTH:
            raise ClientException(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        operator = await _own_operator(db_session, principal)
        if not operator.keycloak_subject:
            raise ClientException("This account has no password to change")

        settings = SecuritySettings.from_environment()
        try:
            await login_staff_with_password(settings, username=operator.login, password=data.current_password)
        except KeycloakLoginError as exc:
            raise ClientException("Current password is incorrect") from exc
        try:
            await set_staff_password(settings, subject=operator.keycloak_subject, password=data.new_password)
        except KeycloakAdminError as exc:
            raise _keycloak_admin_failure(exc) from exc


async def _own_operator(db_session: AsyncSession, principal: Principal) -> OperatorUser:
    operator = await db_session.get(OperatorUser, principal.actor_id)
    if operator is None:
        raise NotFoundException("Staff account was not found")
    return operator


async def _read_profile(db_session: AsyncSession, principal: Principal) -> StaffProfileRead:
    row = (
        await db_session.execute(
            select(
                OperatorUser,
                Organization.name.label("organization_name"),
                Department.name.label("department_name"),
            )
            .select_from(OperatorUser)
            .outerjoin(
                OrganizationMember,
                (OrganizationMember.user_id == OperatorUser.id) & OrganizationMember.is_active.is_(True),
            )
            .outerjoin(Organization, Organization.id == OrganizationMember.organization_id)
            .outerjoin(Department, Department.id == OrganizationMember.department_id)
            .where(OperatorUser.id == principal.actor_id)
        )
    ).first()
    if row is None:
        raise NotFoundException("Staff account was not found")
    operator: OperatorUser = row[0]
    return StaffProfileRead(
        id=str(operator.id),
        login=operator.login,
        display_name=operator.display_name,
        email=operator.email,
        max_user_id=operator.max_user_id,
        organization_name=row.organization_name,
        department_name=row.department_name,
        role_code=next((role for role in _STAFF_ROLE_PRIORITY if role in principal.roles), None),
    )
