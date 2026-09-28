import logging
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient
from litestar.connection import ASGIConnection

from src.security.settings import SecuritySettings

logger = logging.getLogger(__name__)

TOKEN_VERIFIER_STATE_KEY = "keycloak_token_verifier"


@dataclass(frozen=True, slots=True)
class KeycloakClaims:
    """Verified claims from a Keycloak access token, before resolving a local Principal."""

    subject: str
    """Keycloak's own user id (``sub``) - not a local database id."""
    preferred_username: str | None
    roles: frozenset[str]


class KeycloakLoginError(RuntimeError):
    """Raised when the username/password (or refresh token) proxied to Keycloak is rejected."""


class KeycloakPasswordChangeRequired(KeycloakLoginError):
    pass


PASSWORD_CHANGE_REQUIRED_DESCRIPTION = "Account is not fully set up"


async def login_staff_with_password(
    settings: SecuritySettings, *, username: str, password: str
) -> dict[str, Any]:
    """Proxy a Resource Owner Password Credentials grant to Keycloak.

    Staff still authenticate with Keycloak (LDAP-federated) credentials, not ones we
    store - the password passes through this call to Keycloak and is never persisted.

    Raises:
        KeycloakLoginError: if Keycloak rejects the credentials.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            settings.keycloak_token_url,
            data={
                "grant_type": "password",
                "client_id": settings.keycloak_client_id,
                "client_secret": settings.keycloak_client_secret,
                "username": username,
                "password": password,
            },
        )
    if response.status_code != httpx.codes.OK:
        description = response.json().get("error_description", "Invalid credentials")
        if description == PASSWORD_CHANGE_REQUIRED_DESCRIPTION:
            raise KeycloakPasswordChangeRequired(description)
        raise KeycloakLoginError(description)
    return response.json()


async def refresh_staff_tokens(settings: SecuritySettings, *, refresh_token: str) -> dict[str, Any]:
    """Exchange a staff refresh token for a new access token (Keycloak rotates the refresh
    token too). Valid while the Keycloak session lives - 24 hours, see
    ``ssoSessionIdleTimeout``/``ssoSessionMaxLifespan`` in ``keycloak/realm-export.json``.

    Raises:
        KeycloakLoginError: if the refresh token is expired, revoked or malformed.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            settings.keycloak_token_url,
            data={
                "grant_type": "refresh_token",
                "client_id": settings.keycloak_client_id,
                "client_secret": settings.keycloak_client_secret,
                "refresh_token": refresh_token,
            },
        )
    if response.status_code != httpx.codes.OK:
        raise KeycloakLoginError(response.json().get("error_description", "Session expired"))
    return response.json()


async def logout_staff(settings: SecuritySettings, *, refresh_token: str) -> None:
    """End the Keycloak session behind ``refresh_token`` - after this neither it nor any
    token issued from it can be refreshed. Best effort: an already dead session is fine."""
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            settings.keycloak_logout_url,
            data={
                "client_id": settings.keycloak_client_id,
                "client_secret": settings.keycloak_client_secret,
                "refresh_token": refresh_token,
            },
        )


class KeycloakUnavailableError(RuntimeError):
    """The realm's signing keys (JWKS) could not be fetched - Keycloak is down or unreachable.
    Not the caller's fault: it must not be reported as an invalid token."""


class KeycloakTokenVerifier:
    """Verifies staff access tokens against the realm's JWKS.

    Owns the JWKS clients and therefore their signing-key cache - one verifier lives as long
    as the application (``app.state``, see ``token_verifier``), so keys are fetched once an
    hour, not on every request, and never shared between applications (e.g. tests).
    """

    def __init__(self) -> None:
        self._jwks_clients: dict[str, PyJWKClient] = {}

    def _jwks_client(self, jwks_uri: str) -> PyJWKClient:
        client = self._jwks_clients.get(jwks_uri)
        if client is None:
            client = self._jwks_clients[jwks_uri] = PyJWKClient(jwks_uri, cache_keys=True, lifespan=3600)
        return client

    def decode(self, token: str, settings: SecuritySettings) -> KeycloakClaims:
        """Raises:
        jwt.PyJWTError: the token is malformed, expired, or fails signature/claim checks.
        KeycloakUnavailableError: the signing keys could not be fetched.
        """
        try:
            signing_key = self._jwks_client(settings.keycloak_jwks_uri).get_signing_key_from_jwt(token)
        except jwt.PyJWKClientConnectionError as exc:
            raise KeycloakUnavailableError(f"Could not fetch JWKS from {settings.keycloak_jwks_uri}") from exc
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.keycloak_audience,
            issuer=settings.keycloak_issuer,
            options={"require": ["sub", "exp"]},
        )
        realm_roles = frozenset(claims.get("realm_access", {}).get("roles", ()))
        return KeycloakClaims(
            subject=claims["sub"],
            preferred_username=claims.get("preferred_username"),
            roles=realm_roles,
        )


def token_verifier(connection: ASGIConnection) -> KeycloakTokenVerifier:
    """The application's verifier, registered in ``src.main.create_app``."""
    return connection.app.state[TOKEN_VERIFIER_STATE_KEY]
