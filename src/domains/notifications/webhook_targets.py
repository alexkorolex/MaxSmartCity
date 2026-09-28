import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

BLOCKED_HOSTNAMES = frozenset({"localhost", "localhost.localdomain"})
BLOCKED_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home.arpa")


class UnsafeWebhookTargetError(ValueError):
    pass


def _host_and_port(url: str) -> tuple[str, int]:
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise UnsafeWebhookTargetError("WEBHOOK target must be an https:// URL")
    if parts.username or parts.password:
        raise UnsafeWebhookTargetError("WEBHOOK target must not contain credentials")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host:
        raise UnsafeWebhookTargetError("WEBHOOK target has no host")
    try:
        port = parts.port or 443
    except ValueError as exc:
        raise UnsafeWebhookTargetError("WEBHOOK target has an invalid port") from exc
    return host, port


def _ensure_public_address(address: str) -> None:
    ip = ipaddress.ip_address(address)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if not ip.is_global or ip.is_multicast:
        raise UnsafeWebhookTargetError("WEBHOOK target must be a public internet address")


def validate_webhook_url(url: str) -> None:
    host, _ = _host_and_port(url)
    literal = host.strip("[]")
    try:
        ipaddress.ip_address(literal)
    except ValueError:
        if host in BLOCKED_HOSTNAMES or host.endswith(BLOCKED_SUFFIXES) or "." not in host:
            raise UnsafeWebhookTargetError("WEBHOOK target must be a public internet address") from None
        return
    _ensure_public_address(literal)


async def ensure_webhook_url_resolves_publicly(url: str) -> None:
    validate_webhook_url(url)
    host, port = _host_and_port(url)
    try:
        resolved = await asyncio.get_running_loop().getaddrinfo(
            host.strip("[]"), port, type=socket.SOCK_STREAM
        )
    except OSError as exc:
        raise UnsafeWebhookTargetError(f"WEBHOOK host {host!r} does not resolve") from exc
    if not resolved:
        raise UnsafeWebhookTargetError(f"WEBHOOK host {host!r} does not resolve")
    for *_, sockaddr in resolved:
        _ensure_public_address(str(sockaddr[0]))
