import os
from dataclasses import dataclass


def _flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() not in ("false", "0", "no", "off")


@dataclass(frozen=True, slots=True)
class SmtpSettings:
    """Outgoing mail (the ``EMAIL`` organization channel, staff credentials). Optional:
    without ``SMTP_HOST`` sending simply fails - and says so - instead of the whole app
    refusing to start."""

    host: str
    port: int
    username: str | None
    password: str | None
    sender: str
    use_ssl: bool
    """Implicit TLS from the first byte (``SMTP_SSL``, port 465) - defaults to on for port
    465, where STARTTLS on a plain connection never works."""
    starttls: bool
    """Upgrade a plain connection (``SMTP_STARTTLS``, port 587); ignored with ``use_ssl``."""

    @classmethod
    def from_environment(cls) -> "SmtpSettings":
        host = os.environ.get("SMTP_HOST")
        if not host:
            raise ValueError("SMTP_HOST is required for e-mail; see .env.example")
        sender = os.environ.get("SMTP_FROM")
        if not sender:
            raise ValueError("SMTP_FROM is required for e-mail; see .env.example")
        port = int(os.environ.get("SMTP_PORT") or 587)
        use_ssl = _flag("SMTP_SSL", default=port == 465)
        return cls(
            host=host,
            port=port,
            username=os.environ.get("SMTP_USERNAME") or None,
            password=os.environ.get("SMTP_PASSWORD") or None,
            sender=sender,
            use_ssl=use_ssl,
            starttls=not use_ssl and _flag("SMTP_STARTTLS", default=True),
        )
