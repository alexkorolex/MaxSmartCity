import hmac
import logging

import jwt
from litestar.connection import ASGIConnection
from litestar.exceptions import (
    NotAuthorizedException,
    PermissionDeniedException,
    ServiceUnavailableException,
)
from litestar.handlers.base import BaseRouteHandler
from litestar.types import Guard

from src.security.keycloak import KeycloakClaims, KeycloakUnavailableError, token_verifier
from src.security.resident import decode_resident_token
from src.security.settings import SecuritySettings

RESIDENT_TOKEN_ISSUER = "maxsmartcity-residents"

logger = logging.getLogger(__name__)


def extract_bearer_token(connection: ASGIConnection) -> str:
    header = connection.headers.get("Authorization")
    if not header or not header.lower().startswith("bearer "):
        raise NotAuthorizedException("Missing bearer token")
    return header.split(" ", 1)[1].strip()


def is_keycloak_token(token: str, settings: SecuritySettings) -> bool:
    try:
        unverified = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
    except jwt.PyJWTError as exc:
        raise NotAuthorizedException("Malformed token") from exc
    return unverified.get("iss") == settings.keycloak_issuer


def verify_staff_token(connection: ASGIConnection, token: str, settings: SecuritySettings) -> KeycloakClaims:
    """The verified claims of a Keycloak token: 401 for a bad or expired token, 503 (and an
    error in the log) when Keycloak itself cannot be reached to check it."""
    try:
        return token_verifier(connection).decode(token, settings)
    except KeycloakUnavailableError as exc:
        logger.exception("Cannot verify a staff token: Keycloak is unavailable")
        raise ServiceUnavailableException("Authentication service is unavailable") from exc
    except jwt.PyJWTError as exc:
        raise NotAuthorizedException("Invalid or expired token") from exc


def require_roles(*roles: str) -> Guard:
    """Guard factory: only Keycloak-authenticated staff carrying one of ``roles`` may pass.

    Role names come straight from the token's ``realm_access.roles`` claim - the roles
    themselves are configured and assigned in Keycloak (and, transitively, LDAP group
    mappings), never hard-coded here. Resident (bot) tokens never satisfy this guard,
    since they carry no staff roles.
    """

    def guard(connection: ASGIConnection, _route_handler: BaseRouteHandler) -> None:
        settings = SecuritySettings.from_environment()
        token = extract_bearer_token(connection)
        if not is_keycloak_token(token, settings):
            raise PermissionDeniedException("Staff authentication required")
        claims = verify_staff_token(connection, token, settings)
        if not claims.roles.intersection(roles):
            raise PermissionDeniedException(f"Requires one of roles: {', '.join(roles)}")

    return guard


def require_admin_or_bootstrap_secret() -> Guard:
    """Guard factory: an authenticated ``admin`` staff member, OR - only when
    ``STAFF_BOOTSTRAP_SECRET`` is configured - a caller presenting that value via the
    ``X-Bootstrap-Secret`` header instead.

    Lets a fresh deployment create its first admin account without already holding an
    admin token. Leave the env var unset (the default) to disable this path entirely and
    require an admin token unconditionally, same as before.
    """

    def guard(connection: ASGIConnection, _route_handler: BaseRouteHandler) -> None:
        settings = SecuritySettings.from_environment()
        if settings.staff_bootstrap_secret:
            provided = connection.headers.get("X-Bootstrap-Secret", "")
            if provided and hmac.compare_digest(provided, settings.staff_bootstrap_secret):
                return
        token = extract_bearer_token(connection)
        if not is_keycloak_token(token, settings):
            raise PermissionDeniedException("Staff authentication required")
        claims = verify_staff_token(connection, token, settings)
        if "admin" not in claims.roles:
            raise PermissionDeniedException("Requires role: admin")

    return guard


def require_staff() -> Guard:
    """Guard factory: any Keycloak-authenticated staff member, regardless of role.

    Use this for self-service actions any admin/жилищник/управа worker may take (e.g.
    linking their own MAX account) - role gating for specific actions belongs to
    ``require_roles`` instead.
    """

    def guard(connection: ASGIConnection, _route_handler: BaseRouteHandler) -> None:
        settings = SecuritySettings.from_environment()
        token = extract_bearer_token(connection)
        if not is_keycloak_token(token, settings):
            raise PermissionDeniedException("Staff authentication required")
        verify_staff_token(connection, token, settings)

    return guard


def require_resident() -> Guard:
    """Guard factory: only a resident token minted by our own backend may pass."""

    def guard(connection: ASGIConnection, _route_handler: BaseRouteHandler) -> None:
        settings = SecuritySettings.from_environment()
        token = extract_bearer_token(connection)
        if is_keycloak_token(token, settings):
            raise PermissionDeniedException("Resident authentication required")
        decode_resident_token(token, settings)

    return guard


def require_bot_secret() -> Guard:
    """Guard factory: only the resident-bot service (holding the shared secret) may pass.

    The bot is the only client allowed to mint resident tokens; residents themselves never
    handle a login/password, so this is a service-to-service check, not a user credential.
    """

    def guard(connection: ASGIConnection, _route_handler: BaseRouteHandler) -> None:
        settings = SecuritySettings.from_environment()
        provided = connection.headers.get("X-Bot-Secret", "")
        if not hmac.compare_digest(provided, settings.bot_shared_secret):
            raise NotAuthorizedException("Invalid bot secret")

    return guard
