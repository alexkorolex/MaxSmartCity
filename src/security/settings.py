import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SecuritySettings:
    keycloak_issuer: str
    """Must match the token's ``iss`` claim exactly - the URL Keycloak was reached at when
    issuing it (its ``KC_HOSTNAME``), not necessarily how the backend itself reaches Keycloak."""
    keycloak_jwks_uri: str
    """Where the backend fetches Keycloak's signing keys from - typically an in-network
    address (e.g. ``http://keycloak:8080/...``), which may differ from ``keycloak_issuer``."""
    keycloak_internal_url: str
    """Base URL the backend itself uses to call Keycloak (token endpoint, Admin REST API) -
    typically the in-network address, e.g. ``http://keycloak:8080``."""
    keycloak_realm: str
    keycloak_audience: str
    keycloak_client_id: str
    keycloak_client_secret: str
    """Used only for the ``/auth/staff/login`` password-grant proxy and to build service
    tokens; never given to staff directly."""
    keycloak_admin_username: str
    keycloak_admin_password: str
    """Credentials for Keycloak's own bootstrap admin (master realm), used solely to call
    the Admin REST API when registering new staff accounts."""
    resident_jwt_secret: str
    bot_shared_secret: str

    @classmethod
    def from_environment(cls) -> "SecuritySettings":
        keycloak_issuer = os.environ.get("KEYCLOAK_ISSUER")
        if not keycloak_issuer:
            raise ValueError("KEYCLOAK_ISSUER is required; see .env.example")
        keycloak_jwks_uri = os.environ.get("KEYCLOAK_JWKS_URI")
        if not keycloak_jwks_uri:
            raise ValueError("KEYCLOAK_JWKS_URI is required; see .env.example")
        keycloak_internal_url = os.environ.get("KEYCLOAK_INTERNAL_URL")
        if not keycloak_internal_url:
            raise ValueError("KEYCLOAK_INTERNAL_URL is required; see .env.example")
        keycloak_realm = os.environ.get("KEYCLOAK_REALM")
        if not keycloak_realm:
            raise ValueError("KEYCLOAK_REALM is required; see .env.example")
        keycloak_audience = os.environ.get("KEYCLOAK_AUDIENCE")
        if not keycloak_audience:
            raise ValueError("KEYCLOAK_AUDIENCE is required; see .env.example")
        keycloak_client_id = os.environ.get("KEYCLOAK_CLIENT_ID")
        if not keycloak_client_id:
            raise ValueError("KEYCLOAK_CLIENT_ID is required; see .env.example")
        keycloak_client_secret = os.environ.get("KEYCLOAK_CLIENT_SECRET")
        if not keycloak_client_secret:
            raise ValueError("KEYCLOAK_CLIENT_SECRET is required; see .env.example")
        keycloak_admin_username = os.environ.get("KEYCLOAK_ADMIN")
        if not keycloak_admin_username:
            raise ValueError("KEYCLOAK_ADMIN is required; see .env.example")
        keycloak_admin_password = os.environ.get("KEYCLOAK_ADMIN_PASSWORD")
        if not keycloak_admin_password:
            raise ValueError("KEYCLOAK_ADMIN_PASSWORD is required; see .env.example")
        resident_jwt_secret = os.environ.get("RESIDENT_JWT_SECRET")
        if not resident_jwt_secret:
            raise ValueError("RESIDENT_JWT_SECRET is required; see .env.example")
        bot_shared_secret = os.environ.get("BOT_SHARED_SECRET")
        if not bot_shared_secret:
            raise ValueError("BOT_SHARED_SECRET is required; see .env.example")
        return cls(
            keycloak_issuer=keycloak_issuer,
            keycloak_jwks_uri=keycloak_jwks_uri,
            keycloak_internal_url=keycloak_internal_url,
            keycloak_realm=keycloak_realm,
            keycloak_audience=keycloak_audience,
            keycloak_client_id=keycloak_client_id,
            keycloak_client_secret=keycloak_client_secret,
            keycloak_admin_username=keycloak_admin_username,
            keycloak_admin_password=keycloak_admin_password,
            resident_jwt_secret=resident_jwt_secret,
            bot_shared_secret=bot_shared_secret,
        )

    @property
    def keycloak_token_url(self) -> str:
        return f"{self.keycloak_internal_url}/realms/{self.keycloak_realm}/protocol/openid-connect/token"

    @property
    def keycloak_master_token_url(self) -> str:
        return f"{self.keycloak_internal_url}/realms/master/protocol/openid-connect/token"

    @property
    def keycloak_admin_users_url(self) -> str:
        return f"{self.keycloak_internal_url}/admin/realms/{self.keycloak_realm}/users"
