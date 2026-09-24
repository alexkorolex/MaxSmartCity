import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SmtpSettings:
    """Outgoing mail for the ``EMAIL`` organization channel. Optional: without
    ``SMTP_HOST`` the channel simply fails delivery (and is retried) instead of the whole
    app refusing to start."""

    host: str
    port: int
    username: str | None
    password: str | None
    sender: str
    starttls: bool

    @classmethod
    def from_environment(cls) -> "SmtpSettings":
        host = os.environ.get("SMTP_HOST")
        if not host:
            raise ValueError("SMTP_HOST is required for e-mail notifications; see .env.example")
        sender = os.environ.get("SMTP_FROM")
        if not sender:
            raise ValueError("SMTP_FROM is required for e-mail notifications; see .env.example")
        return cls(
            host=host,
            port=int(os.environ.get("SMTP_PORT") or 587),
            username=os.environ.get("SMTP_USERNAME") or None,
            password=os.environ.get("SMTP_PASSWORD") or None,
            sender=sender,
            starttls=(os.environ.get("SMTP_STARTTLS") or "true").lower() != "false",
        )
