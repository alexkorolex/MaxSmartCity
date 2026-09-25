"""Plain-text e-mail over SMTP - the one place the backend talks to a mail server."""

import asyncio
import smtplib
from email.message import EmailMessage

from src.domains.notifications.settings import SmtpSettings


class MailDeliveryError(RuntimeError):
    """The message could not be sent (SMTP not configured, unreachable, rejected)."""


def _send_blocking(settings: SmtpSettings, message: EmailMessage) -> None:
    smtp_class = smtplib.SMTP_SSL if settings.use_ssl else smtplib.SMTP
    with smtp_class(settings.host, settings.port, timeout=15) as smtp:
        if settings.starttls:
            smtp.starttls()
        if settings.username and settings.password:
            smtp.login(settings.username, settings.password)
        smtp.send_message(message)


async def send_email(to: str, subject: str, body: str, *, settings: SmtpSettings | None = None) -> None:
    try:
        settings = settings or SmtpSettings.from_environment()
    except ValueError as exc:
        raise MailDeliveryError(str(exc)) from exc
    message = EmailMessage()
    message["From"] = settings.sender
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    try:
        await asyncio.to_thread(_send_blocking, settings, message)
    except (smtplib.SMTPException, OSError) as exc:
        raise MailDeliveryError(f"SMTP delivery failed: {exc}") from exc
