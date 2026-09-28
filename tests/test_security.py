from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from litestar.connection import ASGIConnection
from litestar.datastructures import State
from litestar.exceptions import (
    NotAuthorizedException,
    PermissionDeniedException,
    ServiceUnavailableException,
)
from litestar.handlers.base import BaseRouteHandler
from litestar.types import Guard

from src.security.guards import (
    STAFF_BOOTSTRAP_STATE_KEY,
    is_keycloak_token,
    require_admin_or_bootstrap_secret,
    require_bot_secret,
    require_resident,
    require_roles,
)
from src.security.keycloak import TOKEN_VERIFIER_STATE_KEY, KeycloakTokenVerifier
from src.security.resident import decode_resident_token, resident_jwt_auth
from src.security.settings import SecuritySettings

ISSUER = "http://localhost:8080/realms/maxsmartcity"
AUDIENCE = "maxsmartcity-backend"


@pytest.fixture(scope="module")
def rsa_keypair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> SecuritySettings:
    monkeypatch.setenv("KEYCLOAK_ISSUER", ISSUER)
    monkeypatch.setenv("KEYCLOAK_JWKS_URI", f"{ISSUER}/protocol/openid-connect/certs")
    monkeypatch.setenv("KEYCLOAK_INTERNAL_URL", "http://keycloak:8080")
    monkeypatch.setenv("KEYCLOAK_REALM", "maxsmartcity")
    monkeypatch.setenv("KEYCLOAK_AUDIENCE", AUDIENCE)
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", AUDIENCE)
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("KEYCLOAK_ADMIN", "admin")
    monkeypatch.setenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
    monkeypatch.setenv("RESIDENT_JWT_SECRET", "test-resident-secret-at-least-32-bytes-long")
    monkeypatch.setenv("BOT_SHARED_SECRET", "test-bot-secret")
    return SecuritySettings.from_environment()


@dataclass
class _FakeSigningKey:
    key: str


def _patch_jwks(monkeypatch: pytest.MonkeyPatch, public_pem: str) -> None:
    def fake_get_signing_key(_self: object, _token: str) -> _FakeSigningKey:
        return _FakeSigningKey(key=public_pem)

    monkeypatch.setattr(jwt.PyJWKClient, "get_signing_key_from_jwt", fake_get_signing_key)


def _keycloak_token(private_pem: str, *, roles: list[str], iss: str = ISSUER, aud: str = AUDIENCE) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "iss": iss,
        "aud": aud,
        "exp": now + timedelta(minutes=5),
        "iat": now,
        "preferred_username": "staff_test",
        "realm_access": {"roles": roles},
    }
    return jwt.encode(payload, private_pem, algorithm="RS256")


def _run_guard(guard: Guard, headers: dict[str, str], verifier: KeycloakTokenVerifier | None = None) -> State:
    app = type(
        "FakeApp", (), {"state": State({TOKEN_VERIFIER_STATE_KEY: verifier or KeycloakTokenVerifier()})}
    )()
    state = State()
    connection = cast(
        ASGIConnection, type("FakeConnection", (), {"headers": headers, "app": app, "state": state})()
    )
    route_handler = cast(BaseRouteHandler, None)
    guard(connection, route_handler)
    return state


def test_is_keycloak_token_distinguishes_issuer(
    settings: SecuritySettings, rsa_keypair: tuple[str, str]
) -> None:
    private_pem, _ = rsa_keypair
    keycloak_token = _keycloak_token(private_pem, roles=["admin"])
    resident_token = resident_jwt_auth(settings).create_token(identifier="some-resident-id")

    assert is_keycloak_token(keycloak_token, settings) is True
    assert is_keycloak_token(resident_token, settings) is False


def test_require_roles_accepts_matching_role(
    settings: SecuritySettings, rsa_keypair: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    private_pem, public_pem = rsa_keypair
    _patch_jwks(monkeypatch, public_pem)
    token = _keycloak_token(private_pem, roles=["admin", "district_admin"])

    _run_guard(require_roles("admin"), {"Authorization": f"Bearer {token}"})


def test_require_roles_rejects_missing_role(
    settings: SecuritySettings, rsa_keypair: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    private_pem, public_pem = rsa_keypair
    _patch_jwks(monkeypatch, public_pem)
    token = _keycloak_token(private_pem, roles=["housing_worker"])

    with pytest.raises(PermissionDeniedException):
        _run_guard(require_roles("admin"), {"Authorization": f"Bearer {token}"})


def test_require_roles_rejects_resident_token(settings: SecuritySettings) -> None:
    resident_token = resident_jwt_auth(settings).create_token(identifier="some-resident-id")

    with pytest.raises(PermissionDeniedException):
        _run_guard(require_roles("admin"), {"Authorization": f"Bearer {resident_token}"})


def test_require_roles_rejects_missing_header(settings: SecuritySettings) -> None:
    with pytest.raises(NotAuthorizedException):
        _run_guard(require_roles("admin"), {})


def test_require_resident_accepts_resident_token(settings: SecuritySettings) -> None:
    token = resident_jwt_auth(settings).create_token(identifier="some-resident-id")

    _run_guard(require_resident(), {"Authorization": f"Bearer {token}"})


def test_require_resident_rejects_keycloak_token(
    settings: SecuritySettings, rsa_keypair: tuple[str, str]
) -> None:
    private_pem, _ = rsa_keypair
    token = _keycloak_token(private_pem, roles=["admin"])

    with pytest.raises(PermissionDeniedException):
        _run_guard(require_resident(), {"Authorization": f"Bearer {token}"})


def test_resident_token_round_trip(settings: SecuritySettings) -> None:
    encoded = resident_jwt_auth(settings).create_token(identifier="some-resident-id")

    decoded = decode_resident_token(encoded, settings)

    assert decoded.sub == "some-resident-id"


def test_require_bot_secret_accepts_correct_secret(settings: SecuritySettings) -> None:
    _run_guard(require_bot_secret(), {"X-Bot-Secret": "test-bot-secret"})


def test_require_bot_secret_rejects_wrong_secret(settings: SecuritySettings) -> None:
    with pytest.raises(NotAuthorizedException):
        _run_guard(require_bot_secret(), {"X-Bot-Secret": "wrong"})


def test_require_admin_or_bootstrap_secret_accepts_admin_token(
    settings: SecuritySettings, rsa_keypair: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    private_pem, public_pem = rsa_keypair
    _patch_jwks(monkeypatch, public_pem)
    token = _keycloak_token(private_pem, roles=["admin"])

    _run_guard(require_admin_or_bootstrap_secret(), {"Authorization": f"Bearer {token}"})


def test_require_admin_or_bootstrap_secret_rejects_non_admin_token(
    settings: SecuritySettings, rsa_keypair: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    private_pem, public_pem = rsa_keypair
    _patch_jwks(monkeypatch, public_pem)
    token = _keycloak_token(private_pem, roles=["housing_worker"])

    with pytest.raises(PermissionDeniedException):
        _run_guard(require_admin_or_bootstrap_secret(), {"Authorization": f"Bearer {token}"})


def test_require_admin_or_bootstrap_secret_rejects_missing_header_when_unconfigured(
    settings: SecuritySettings,
) -> None:
    with pytest.raises(NotAuthorizedException):
        _run_guard(require_admin_or_bootstrap_secret(), {})


def test_require_admin_or_bootstrap_secret_accepts_correct_bootstrap_secret(
    settings: SecuritySettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STAFF_BOOTSTRAP_SECRET", "test-bootstrap-secret")

    state = _run_guard(require_admin_or_bootstrap_secret(), {"X-Bootstrap-Secret": "test-bootstrap-secret"})

    assert state.get(STAFF_BOOTSTRAP_STATE_KEY) is True


def test_require_admin_or_bootstrap_secret_rejects_wrong_bootstrap_secret(
    settings: SecuritySettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STAFF_BOOTSTRAP_SECRET", "test-bootstrap-secret")

    with pytest.raises(NotAuthorizedException):
        _run_guard(require_admin_or_bootstrap_secret(), {"X-Bootstrap-Secret": "wrong"})


def test_unreachable_keycloak_is_a_503_not_an_invalid_token(
    settings: SecuritySettings,
    rsa_keypair: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    private_pem, _ = rsa_keypair

    def unreachable(_self: object, _token: str) -> None:
        raise jwt.PyJWKClientConnectionError("Fail to fetch data from the url, err: timed out")

    monkeypatch.setattr(jwt.PyJWKClient, "get_signing_key_from_jwt", unreachable)
    token = _keycloak_token(private_pem, roles=["admin"])

    with pytest.raises(ServiceUnavailableException):
        _run_guard(require_roles("admin"), {"Authorization": f"Bearer {token}"})
    [record] = [record for record in caplog.records if record.name == "src.security.guards"]
    assert record.levelname == "ERROR"
    assert record.exc_info is not None


def test_each_verifier_keeps_its_own_jwks_client(settings: SecuritySettings) -> None:
    first, second = KeycloakTokenVerifier(), KeycloakTokenVerifier()

    assert first._jwks_client(settings.keycloak_jwks_uri) is first._jwks_client(settings.keycloak_jwks_uri)
    assert first._jwks_client(settings.keycloak_jwks_uri) is not second._jwks_client(
        settings.keycloak_jwks_uri
    )
