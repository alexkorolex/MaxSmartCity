"""E-mail a new staff member their sign-in details right after an admin created the
account. Sent directly after the registration is committed - never through the outbox,
so the temporary password is not stored anywhere in the database."""

import logging
from dataclasses import dataclass

from src.domains.notifications.mailer import MailDeliveryError, send_email
from src.settings import admin_panel_url

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CredentialsEmailResult:
    """Whether the employee got their login by e-mail - if not, the admin has to hand it
    over themselves, so the UI must say so."""

    recipient: str | None
    sent: bool
    error: str | None = None


def build_credentials_email(
    *,
    display_name: str,
    login: str,
    password: str,
    organization_name: str,
    login_url: str | None,
) -> tuple[str, str]:
    subject = f"Доступ к панели Smart City — {organization_name}"
    link_line = (
        f"Ссылка для входа: {login_url}"
        if login_url
        else "Ссылку на панель управления уточните у администратора платформы."
    )
    body = (
        f"Здравствуйте, {display_name}!\n\n"
        f"Вас зарегистрировали сотрудником организации {organization_name} в панели управления "
        "Smart City. В ней вы будете видеть дома организации, их жителей и заявки.\n\n"
        f"{link_line}\n"
        f"Логин: {login}\n"
        f"Временный пароль: {password}\n\n"
        "Никому не сообщайте пароль. Если вы не ожидали этого письма, сообщите администратору "
        "платформы.\n\n"
        "— Smart City"
    )
    return subject, body


async def send_credentials_email(
    *,
    email: str | None,
    display_name: str,
    login: str,
    password: str,
    organization_name: str,
) -> CredentialsEmailResult:
    """Best effort: a failure is reported back, never raised - the account already exists."""
    recipient = (email or "").strip() or None
    if recipient is None:
        return CredentialsEmailResult(recipient=None, sent=False, error="E-mail сотрудника не указан")
    subject, body = build_credentials_email(
        display_name=display_name,
        login=login,
        password=password,
        organization_name=organization_name,
        login_url=admin_panel_url(),
    )
    try:
        await send_email(recipient, subject, body)
    except MailDeliveryError as exc:
        # The error text never contains the password - only SMTP's own diagnostics.
        logger.warning("Staff credentials e-mail was not sent", extra={"login": login, "error": str(exc)})
        return CredentialsEmailResult(recipient=recipient, sent=False, error=str(exc))
    return CredentialsEmailResult(recipient=recipient, sent=True)
