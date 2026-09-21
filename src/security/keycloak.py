from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient

from src.security.settings import SecuritySettings


@dataclass(frozen=True, slots=True)
class KeycloakClaims:
    """Verified claims from a Keycloak access token, before resolving a local Principal."""

    subject: str
    """Keycloak's own user id (``sub``) - not a local database id."""
    preferred_username: str | None
    roles: frozenset[str]


class KeycloakLoginError(RuntimeError):
    """Raised when the username/password proxied to Keycloak is rejected."""


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
        raise KeycloakLoginError(response.json().get("error_description", "Invalid credentials"))
    return response.json()


@lru_cache(maxsize=1)
def _jwks_client(jwks_uri: str) -> PyJWKClient:
    return PyJWKClient(jwks_uri, cache_keys=True, lifespan=3600)


def decode_keycloak_token(token: str, settings: SecuritySettings) -> KeycloakClaims:
    """Verify a Keycloak-issued access token against the realm's JWKS.

    Raises:
        jwt.PyJWTError: if the token is missing, expired, or fails signature/claim verification.
    """
    signing_key = _jwks_client(settings.keycloak_jwks_uri).get_signing_key_from_jwt(token)
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
