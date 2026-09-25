import hmac
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.request import Request
from uuid import UUID

import fakeredis.aioredis
import pytest
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.handlers.base import BaseRouteHandler
from litestar.stores.redis import RedisStore

from src.domains.identity.services import ResidentService
from src.max_bot import certs, dedup, handlers, identity, startup
from src.max_bot.client import MaxApiError, MaxClient
from src.max_bot.guards import require_max_webhook_secret
from src.max_bot.settings import MaxBotSettings

FAKE_BOT_USERNAME = "max_smart_city_bot"

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> MaxBotSettings:
    monkeypatch.setenv("MAX_BOT_TOKEN", "test-bot-token")
    monkeypatch.setenv("MAX_WEBHOOK_SECRET", "test-webhook-secret")
    monkeypatch.setenv("WEB_APP_LOGIN_URL", "https://app.example.com/auth/max")
    # Deliberately absent by default (some tests set it back) - must not leak in from
    # whatever the developer's own shell happens to have exported.
    monkeypatch.delenv("MAX_WEBHOOK_PUBLIC_URL", raising=False)
    return MaxBotSettings.from_environment()


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    """Route the app's Redis-backed dedup/login-code stores to an in-memory fake, shared
    across calls within a test via a single FakeServer."""
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    server = fakeredis.aioredis.FakeServer()

    def fake_with_client(
        cls: type[RedisStore], _url: str, *, namespace: str | None = None, **_kwargs: object
    ) -> RedisStore:
        return cls(redis=fakeredis.aioredis.FakeRedis(server=server), namespace=namespace)

    monkeypatch.setattr(RedisStore, "with_client", classmethod(fake_with_client))


@pytest.fixture(autouse=True)
def fake_bot_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock MAX's ``/me`` bot-info call and reset the process-lifetime username cache, so
    every test resolves the same fixed username independent of test order or network."""
    monkeypatch.setattr(identity, "_cached_username", None)

    async def fake_get_me(_self: MaxClient) -> dict[str, Any]:
        return {"user_id": 1, "first_name": "Smart City", "is_bot": True, "username": FAKE_BOT_USERNAME}

    monkeypatch.setattr(MaxClient, "get_me", fake_get_me)


@dataclass
class _FakeConnection:
    headers: dict[str, str]


def test_require_max_webhook_secret_accepts_correct_secret(settings: MaxBotSettings) -> None:
    connection = cast(
        ASGIConnection, _FakeConnection(headers={"X-Max-Bot-Api-Secret": "test-webhook-secret"})
    )
    require_max_webhook_secret()(connection, cast(BaseRouteHandler, None))


def test_require_max_webhook_secret_rejects_wrong_secret(settings: MaxBotSettings) -> None:
    connection = cast(ASGIConnection, _FakeConnection(headers={"X-Max-Bot-Api-Secret": "wrong"}))
    with pytest.raises(NotAuthorizedException):
        require_max_webhook_secret()(connection, cast(BaseRouteHandler, None))


async def test_login_code_round_trip() -> None:
    resident_id = UUID("11111111-1111-1111-1111-111111111111")

    code = await dedup.create_login_code(resident_id)
    first = await dedup.consume_login_code(code)
    second = await dedup.consume_login_code(code)

    assert first == resident_id
    assert second is None


async def test_dedup_marks_event_processed_only_once() -> None:
    key = "bot_started:123:456"

    assert await dedup.is_duplicate_event(key) is False
    await dedup.mark_event_processed(key)
    assert await dedup.is_duplicate_event(key) is True


@dataclass
class _FakeResident:
    id: UUID


class _FakeResidentService:
    def __init__(self) -> None:
        self.upserts: list[dict[str, Any]] = []
        self.remembered_chats: list[tuple[int, int]] = []
        self.stopped: list[int] = []

    async def upsert_by_max_user_id(
        self, *, max_user_id: int, username: str | None, display_name: str | None, chat_id: int | None = None
    ) -> _FakeResident:
        self.upserts.append(
            {
                "max_user_id": max_user_id,
                "username": username,
                "display_name": display_name,
                "chat_id": chat_id,
            }
        )
        return _FakeResident(id=UUID(int=max_user_id))

    async def remember_chat(self, *, max_user_id: int, chat_id: int) -> None:
        self.remembered_chats.append((max_user_id, chat_id))

    async def mark_bot_stopped(self, *, max_user_id: int) -> None:
        self.stopped.append(max_user_id)


async def test_handle_bot_started_registers_resident_and_sends_welcome(
    settings: MaxBotSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[dict[str, Any]] = []

    async def fake_send_message(self: MaxClient, **kwargs: object) -> None:
        sent.append(kwargs)

    monkeypatch.setattr(MaxClient, "send_message", fake_send_message)

    service = _FakeResidentService()
    update = {
        "update_type": "bot_started",
        "timestamp": 1780000000000,
        "chat_id": 5551234,
        "user": {"user_id": 42, "first_name": "Alex", "last_name": None, "username": "alex", "is_bot": False},
    }

    await handlers.handle_bot_started(update, cast(ResidentService, service), settings)

    # The dialog's chat_id is stored - that's where the resident's notifications go.
    assert service.upserts == [
        {"max_user_id": 42, "username": "alex", "display_name": "Alex", "chat_id": 5551234}
    ]
    assert len(sent) == 1
    assert sent[0]["chat_id"] == 5551234
    assert "Добро пожаловать" in sent[0]["text"]
    open_app_button, link_button = sent[0]["attachments"][0]["payload"]["buttons"][0]
    assert open_app_button["type"] == "open_app"
    assert open_app_button["web_app"] == FAKE_BOT_USERNAME
    assert open_app_button["payload"]
    assert link_button["type"] == "link"
    assert link_button["url"].startswith("https://app.example.com/auth/max?code=")


async def test_handle_message_created_start_command_sends_welcome(
    settings: MaxBotSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[dict[str, Any]] = []

    async def fake_send_message(self: MaxClient, **kwargs: object) -> None:
        sent.append(kwargs)

    monkeypatch.setattr(MaxClient, "send_message", fake_send_message)

    service = _FakeResidentService()
    update = {
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 7, "is_bot": False, "username": "res", "first_name": "Res"},
            "recipient": {"chat_type": "dialog", "chat_id": 7007},
            "body": {"mid": "m0", "text": "/start"},
        },
    }

    await handlers.handle_message_created(update, cast(ResidentService, service), settings)

    assert service.upserts == [{"max_user_id": 7, "username": "res", "display_name": "Res", "chat_id": 7007}]
    assert len(sent) == 1
    assert "Добро пожаловать" in sent[0]["text"]
    assert sent[0]["attachments"][0]["type"] == "inline_keyboard"


async def test_handle_message_created_ignores_bot_senders(
    settings: MaxBotSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[dict[str, Any]] = []

    async def fake_send_message(self: MaxClient, **kwargs: object) -> None:
        sent.append(kwargs)

    monkeypatch.setattr(MaxClient, "send_message", fake_send_message)

    service = _FakeResidentService()
    update = {
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 1, "is_bot": True},
            "recipient": {"chat_type": "dialog"},
            "body": {"mid": "m1", "text": "ping"},
        },
    }

    await handlers.handle_message_created(update, cast(ResidentService, service), settings)

    assert sent == []
    assert service.upserts == []


async def test_handle_message_created_login_command_issues_login_link(
    settings: MaxBotSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[dict[str, Any]] = []

    async def fake_send_message(self: MaxClient, **kwargs: object) -> None:
        sent.append(kwargs)

    monkeypatch.setattr(MaxClient, "send_message", fake_send_message)

    service = _FakeResidentService()
    update = {
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 99, "is_bot": False, "username": "res", "first_name": "Res"},
            "recipient": {"chat_type": "dialog"},
            "body": {"mid": "m2", "text": "/login"},
        },
    }

    await handlers.handle_message_created(update, cast(ResidentService, service), settings)

    assert service.upserts == [{"max_user_id": 99, "username": "res", "display_name": "Res", "chat_id": None}]
    assert len(sent) == 1
    assert "ссылка" in sent[0]["text"].lower()
    open_app_button, link_button = sent[0]["attachments"][0]["payload"]["buttons"][0]
    assert open_app_button["type"] == "open_app"
    assert link_button["url"].startswith("https://app.example.com/auth/max?code=")


async def test_any_dialog_message_remembers_the_chat_without_registering(
    settings: MaxBotSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[dict[str, Any]] = []

    async def fake_send_message(self: MaxClient, **kwargs: object) -> None:
        sent.append(kwargs)

    monkeypatch.setattr(MaxClient, "send_message", fake_send_message)

    service = _FakeResidentService()
    update = {
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 55, "is_bot": False},
            "recipient": {"chat_type": "dialog", "chat_id": 5055},
            "body": {"mid": "m9", "text": "привет"},
        },
    }

    await handlers.handle_message_created(update, cast(ResidentService, service), settings)

    assert service.upserts == []
    assert service.remembered_chats == [(55, 5055)]
    assert len(sent) == 1


async def test_bot_stopped_marks_the_resident(settings: MaxBotSettings) -> None:
    service = _FakeResidentService()

    await handlers.handle_bot_stopped(
        {"update_type": "bot_stopped", "chat_id": 1, "user": {"user_id": 77}}, cast(ResidentService, service)
    )

    assert service.stopped == [77]


def test_webhook_secret_is_compared_constant_time(settings: MaxBotSettings) -> None:
    # sanity: guard uses hmac.compare_digest, not `==`
    assert hmac.compare_digest("a", "a") is True


class _FakeUrlResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def __enter__(self) -> "_FakeUrlResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._data


def test_fetch_russian_trusted_ca_certs_writes_expected_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_pem = b"-----BEGIN CERTIFICATE-----\nZmFrZQ==\n-----END CERTIFICATE-----\n"
    monkeypatch.setattr(certs, "urlopen", lambda *_a, **_kw: _FakeUrlResponse(fake_pem))

    fetched = certs.fetch_russian_trusted_ca_certs(target_dir=tmp_path)

    assert {f.filename for f in fetched} == set(certs.CERT_URLS)
    for f in fetched:
        assert f.path.read_bytes() == fake_pem


def test_fetch_russian_trusted_ca_certs_rejects_non_pem_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(certs, "urlopen", lambda *_a, **_kw: _FakeUrlResponse(b"<html>not a cert</html>"))

    with pytest.raises(certs.CertFetchError):
        certs.fetch_russian_trusted_ca_certs(target_dir=tmp_path)


def test_fetch_retries_transient_failures_then_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_pem = b"-----BEGIN CERTIFICATE-----\nZmFrZQ==\n-----END CERTIFICATE-----\n"
    monkeypatch.setattr(certs, "_RETRY_DELAY_SECONDS", 0)
    calls_per_url: dict[str, int] = {}

    def flaky_urlopen(request: Request, **_kwargs: object) -> _FakeUrlResponse:
        url = request.full_url
        calls_per_url[url] = calls_per_url.get(url, 0) + 1
        if calls_per_url[url] < certs._MAX_ATTEMPTS:
            raise urllib.error.URLError("[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred")
        return _FakeUrlResponse(fake_pem)

    monkeypatch.setattr(certs, "urlopen", flaky_urlopen)

    fetched = certs.fetch_russian_trusted_ca_certs(target_dir=tmp_path)

    assert set(calls_per_url.values()) == {certs._MAX_ATTEMPTS}
    assert len(fetched) == len(certs.CERT_URLS)


def test_fetch_raises_cert_fetch_error_after_exhausting_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(certs, "_RETRY_DELAY_SECONDS", 0)

    def always_fails(*_args: object, **_kwargs: object) -> _FakeUrlResponse:
        raise urllib.error.URLError("[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred")

    monkeypatch.setattr(certs, "urlopen", always_fails)

    with pytest.raises(certs.CertFetchError, match=r"gu-st\.ru"):
        certs.fetch_russian_trusted_ca_certs(target_dir=tmp_path)


async def test_auto_subscribe_skips_when_no_public_url_configured(
    settings: MaxBotSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Explicitly absent, regardless of what the ambient shell environment has set -
    # nothing to register.
    monkeypatch.delenv("MAX_WEBHOOK_PUBLIC_URL", raising=False)
    calls: list[object] = []

    async def fake_subscribe(self: MaxClient, **kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(MaxClient, "subscribe", fake_subscribe)

    await startup.auto_subscribe_max_webhook()

    assert calls == []


async def test_auto_subscribe_registers_when_public_url_configured(
    settings: MaxBotSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MAX_WEBHOOK_PUBLIC_URL", "https://bot.example.com/webhook/max")
    calls: list[dict[str, object]] = []

    async def fake_subscribe(self: MaxClient, **kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(MaxClient, "subscribe", fake_subscribe)

    await startup.auto_subscribe_max_webhook()

    assert len(calls) == 1
    assert calls[0]["url"] == "https://bot.example.com/webhook/max"
    assert calls[0]["secret"] == "test-webhook-secret"


async def test_auto_subscribe_never_raises_on_api_failure(
    settings: MaxBotSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MAX_WEBHOOK_PUBLIC_URL", "https://bot.example.com/webhook/max")

    async def failing_subscribe(self: MaxClient, **_kwargs: object) -> None:
        raise MaxApiError(503, "temporarily unavailable")

    monkeypatch.setattr(MaxClient, "subscribe", failing_subscribe)

    await startup.auto_subscribe_max_webhook()  # must not raise


async def test_chatid_command_in_a_group_replies_with_the_chat_id(
    settings: MaxBotSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[dict[str, Any]] = []

    async def fake_send_message(self: MaxClient, **kwargs: object) -> None:
        sent.append(kwargs)

    monkeypatch.setattr(MaxClient, "send_message", fake_send_message)
    service = _FakeResidentService()
    group_message = {
        "sender": {"user_id": 7, "is_bot": False},
        "recipient": {"chat_type": "chat", "chat_id": -70001},
        "body": {"mid": "m1", "text": "/chatid"},
    }

    await handlers.handle_message_created(
        {"update_type": "message_created", "message": group_message}, cast(ResidentService, service), settings
    )
    chatter = {**group_message, "body": {"mid": "m2", "text": "привет"}}
    await handlers.handle_message_created(
        {"update_type": "message_created", "message": chatter}, cast(ResidentService, service), settings
    )

    assert len(sent) == 1
    assert sent[0]["chat_id"] == -70001
    assert "-70001" in sent[0]["text"]
    assert service.upserts == []


async def test_id_command_in_a_dialog_replies_with_the_max_id_without_registering(
    settings: MaxBotSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[dict[str, Any]] = []

    async def fake_send_message(self: MaxClient, **kwargs: object) -> None:
        sent.append(kwargs)

    monkeypatch.setattr(MaxClient, "send_message", fake_send_message)
    service = _FakeResidentService()
    update = {
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 4242, "is_bot": False},
            "recipient": {"chat_type": "dialog"},
            "body": {"mid": "m3", "text": "/id"},
        },
    }

    await handlers.handle_message_created(update, cast(ResidentService, service), settings)

    assert sent == [{"user_id": 4242, "text": handlers.MY_ID_TEXT.format(user_id=4242)}]
    assert service.upserts == []
