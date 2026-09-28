import socket

import pytest

from src.domains.notifications import webhook_targets
from src.domains.notifications.webhook_targets import (
    UnsafeWebhookTargetError,
    ensure_webhook_url_resolves_publicly,
    validate_webhook_url,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.parametrize(
    "url",
    [
        "http://hooks.example.com/x",
        "https://user:pass@hooks.example.com/x",
        "https://localhost/x",
        "https://backend:8000/x",
        "https://minio.internal/x",
        "https://127.0.0.1/x",
        "https://10.0.0.5/x",
        "https://172.18.0.4/x",
        "https://192.168.1.1/x",
        "https://169.254.169.254/latest/meta-data",
        "https://[::1]/x",
        "https://[::ffff:127.0.0.1]/x",
        "https://0.0.0.0/x",
    ],
)
def test_private_or_malformed_targets_are_rejected(url: str) -> None:
    with pytest.raises(UnsafeWebhookTargetError):
        validate_webhook_url(url)


@pytest.mark.parametrize(
    "url", ["https://hooks.example.com/x", "https://8.8.8.8/x", "https://[2606:4700::1111]/x"]
)
def test_public_targets_are_accepted(url: str) -> None:
    validate_webhook_url(url)


def _resolving_to(*addresses: str) -> object:
    async def fake_getaddrinfo(_self: object, host: str, port: int, **_kwargs: object) -> list[tuple]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port)) for address in addresses]

    return fake_getaddrinfo


async def test_a_public_name_that_resolves_to_a_private_address_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loop_type = type(webhook_targets.asyncio.get_running_loop())
    monkeypatch.setattr(loop_type, "getaddrinfo", _resolving_to("93.184.216.34", "10.0.0.7"))

    with pytest.raises(UnsafeWebhookTargetError):
        await ensure_webhook_url_resolves_publicly("https://rebind.example.com/hook")


async def test_a_public_name_resolving_publicly_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    loop_type = type(webhook_targets.asyncio.get_running_loop())
    monkeypatch.setattr(loop_type, "getaddrinfo", _resolving_to("93.184.216.34"))

    await ensure_webhook_url_resolves_publicly("https://hooks.example.com/hook")
