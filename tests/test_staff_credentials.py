import smtplib
from email.message import EmailMessage
from typing import Any

import pytest

from src.domains.identity.credentials import build_credentials_email, send_credentials_email
from src.domains.notifications import mailer
from src.domains.notifications.settings import SmtpSettings


def test_credentials_email_names_the_organization_and_carries_the_sign_in_details() -> None:
    subject, body = build_credentials_email(
        display_name="Иван Диспетчер",
        login="uk-dispatcher",
        password="Temp-pass-123",
        organization_name="ООО «ДОМ-ПЛЮС»",
        login_url="https://admin.example/login",
    )
    assert "ООО «ДОМ-ПЛЮС»" in subject
    assert "Вас зарегистрировали сотрудником организации ООО «ДОМ-ПЛЮС»" in body
    assert "Ссылка для входа: https://admin.example/login" in body
    assert "Логин: uk-dispatcher" in body
    assert "Временный пароль: Temp-pass-123" in body


def test_credentials_email_without_a_configured_link_says_where_to_ask() -> None:
    _subject, body = build_credentials_email(
        display_name="Иван", login="a", password="b", organization_name="ТСЖ", login_url=None
    )
    assert "уточните у администратора" in body


@pytest.mark.anyio
async def test_no_email_address_means_nothing_is_sent() -> None:
    result = await send_credentials_email(
        email="  ", display_name="Иван", login="a", password="b", organization_name="ТСЖ"
    )
    assert result.sent is False
    assert result.recipient is None


@pytest.mark.parametrize(
    ("port", "ssl_flag", "use_ssl", "starttls"),
    [("465", None, True, False), ("587", None, False, True), ("2525", "true", True, False)],
)
def test_implicit_tls_is_chosen_for_port_465(
    monkeypatch: pytest.MonkeyPatch, port: str, ssl_flag: str | None, use_ssl: bool, starttls: bool
) -> None:
    monkeypatch.setenv("SMTP_HOST", "smtp.example")
    monkeypatch.setenv("SMTP_FROM", "noreply@example")
    monkeypatch.setenv("SMTP_PORT", port)
    monkeypatch.setenv("SMTP_STARTTLS", "true")
    if ssl_flag is None:
        monkeypatch.delenv("SMTP_SSL", raising=False)
    else:
        monkeypatch.setenv("SMTP_SSL", ssl_flag)
    settings = SmtpSettings.from_environment()
    assert (settings.use_ssl, settings.starttls) == (use_ssl, starttls)


@pytest.mark.anyio
async def test_mailer_uses_ssl_connection_on_port_465(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, Any]] = []

    class FakeSmtp:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            calls.append(("connect", (type(self).__name__, host, port)))

        def __enter__(self) -> "FakeSmtp":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def starttls(self) -> None:
            calls.append(("starttls", None))

        def login(self, username: str, password: str) -> None:
            calls.append(("login", username))

        def send_message(self, message: EmailMessage) -> None:
            calls.append(("send", message["To"]))

    class SMTP_SSL(FakeSmtp):
        pass

    monkeypatch.setattr(smtplib, "SMTP_SSL", SMTP_SSL)
    monkeypatch.setattr(smtplib, "SMTP", FakeSmtp)
    settings = SmtpSettings(
        host="smtp.example",
        port=465,
        username="user",
        password="secret",
        sender="noreply@example",
        use_ssl=True,
        starttls=False,
    )
    await mailer.send_email("to@example", "Тема", "Текст", settings=settings)
    assert calls == [
        ("connect", ("SMTP_SSL", "smtp.example", 465)),
        ("login", "user"),
        ("send", "to@example"),
    ]
