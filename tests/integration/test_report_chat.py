"""The chat between a resident and the organization working on their report."""

import asyncio
import os
from collections.abc import Awaitable, Callable
from uuid import uuid4

import pytest
from litestar.testing import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src.domains.identity.models import Resident
from src.domains.notifications.resident_push import push_resident_notifications
from src.domains.reports.chat import (
    ChatSubscription,
    notify_unread_chat_messages,
    publish_chat_event,
)
from tests.integration.test_housing_api import _headers, _register_housing_organization
from tests.integration.test_ingestion import rows
from tests.integration.test_resident_api import (  # noqa: F401
    _insert_category,
    _insert_house,
    _resident_token,
    _staff_token,
    rsa_keypair,
    run_sql,
    security_env,
)


def _run_notifier(
    database_url: str, job: Callable[[AsyncSession], Awaitable[int]] = notify_unread_chat_messages
) -> int:
    async def run() -> int:
        engine = create_async_engine(database_url, poolclass=NullPool)
        try:
            async with AsyncSession(engine) as session:
                processed = await job(session)
                await session.commit()
                return processed
        finally:
            await engine.dispose()

    return asyncio.run(run())


def test_resident_and_organization_chat_and_are_told_when_away(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_pem, _ = rsa_keypair
    admin = _headers(_staff_token(private_pem, subject=str(uuid4()), roles=["admin"]))

    def register(name: str) -> tuple[str, dict[str, str]]:
        return _register_housing_organization(api_client, monkeypatch, private_pem, admin, name)

    organization_id, worker = register("УК Чат")
    _other_org, outsider = register("УК Чужая")
    house = _insert_house(database_url, formatted=f"ул. Переписки, {uuid4().hex[:6]}")
    body = {"house_id": house, "organization_id": organization_id, "basis": "Договор управления"}
    assert api_client.post("/geo/house-management/", json=body, headers=worker).status_code == 201
    resident_id, token = _resident_token(api_client, display_name="Ольга Житель")
    resident = _headers(token)
    # The resident pressed /start in the bot: their dialog's chat_id is known.
    run_sql(database_url, "UPDATE identity.resident SET max_chat_id = 90210 WHERE id = :id", id=resident_id)
    report = api_client.post(
        "/reports/",
        json={
            "source_type": "MAX",
            "text": "Не горит свет в подъезде",
            "category_id": _insert_category(database_url),
            "house_id": house,
        },
        headers=resident,
    ).json()["id"]
    chat = f"/reports/{report}/messages"

    thread = api_client.get(chat, headers=resident).json()
    assert thread["counterparts"] == ["УК Чат"]
    assert thread["can_write"] is True
    sent = api_client.post(chat, json={"text": "Когда почините?"}, headers=resident)
    assert sent.status_code == 201, sent.text
    assert sent.json()["is_mine"] is True
    assert api_client.post(chat, json={"text": "   "}, headers=resident).status_code == 409

    assert api_client.get(chat, headers=outsider).status_code == 404
    inbox = api_client.get("/chat/conversations", headers=worker).json()
    assert [(item["report_id"], item["unread_count"]) for item in inbox] == [(report, 1)]

    staff_view = api_client.get(chat, headers=worker).json()
    assert staff_view["counterparts"] == ["Ольга Житель"]
    assert [(m["text"], m["is_mine"], m["read_at"] is not None) for m in staff_view["messages"]] == [
        ("Когда почините?", False, True)
    ]
    assert api_client.get("/chat/conversations", headers=worker).json()[0]["unread_count"] == 0
    reply = api_client.post(chat, json={"text": "Электрик приедет сегодня до 18:00"}, headers=worker)
    assert reply.status_code == 201, reply.text
    assert reply.json()["organization_name"] == "УК Чат"

    # The resident is away: after a minute unread, they're told in MAX and in the app.
    delivered: list[tuple[int | None, str]] = []

    async def fake_send(resident: Resident, text: str) -> bool:
        delivered.append((resident.max_chat_id, text))
        return True

    monkeypatch.setattr("src.domains.notifications.resident_push.send_to_resident", fake_send)
    _run_notifier(database_url, push_resident_notifications)  # whatever the report itself caused
    delivered.clear()
    run_sql(
        database_url,
        "UPDATE reports.report_message SET created_at = created_at - interval '2 minutes' "
        "WHERE report_id = :report",
        report=report,
    )
    # ...and the organization is away too, for the resident's follow-up.
    assert api_client.post(chat, json={"text": "Спасибо!"}, headers=resident).status_code == 201
    run_sql(
        database_url,
        "UPDATE reports.report_message SET created_at = created_at - interval '2 minutes' "
        "WHERE report_id = :report AND text = 'Спасибо!'",
        report=report,
    )

    assert _run_notifier(database_url) == 2
    assert _run_notifier(database_url, push_resident_notifications) == 1
    ((chat_id, text),) = delivered
    assert chat_id == 90210
    assert "Электрик приедет сегодня до 18:00" in text
    in_app = api_client.get("/notifications/", headers=resident).json()
    assert [item["type"] for item in in_app] == ["CHAT_MESSAGE"]
    queued = asyncio.run(
        rows(
            database_url,
            "SELECT payload->>'body' AS body FROM infrastructure.outbox_event "
            "WHERE event_type = 'ORGANIZATION_NOTIFICATION' AND payload->>'event_type' = 'CHAT_MESSAGE' "
            "AND aggregate_id = :organization",
            organization=organization_id,
        )
    )
    assert len(queued) == 1
    assert "Спасибо!" in queued[0].body
    assert "Ольга Житель" in queued[0].body

    # Each message is announced once.
    assert _run_notifier(database_url) == 0
    assert _run_notifier(database_url, push_resident_notifications) == 0

    # The resident turned MAX notifications off in the web app: in-app only from now on.
    toggled = api_client.patch(
        "/identity/me/resident", json={"notifications_enabled": False}, headers=resident
    )
    assert toggled.status_code == 200, toggled.text
    assert toggled.json()["max_chat_id"] == 90210
    assert api_client.post(chat, json={"text": "Уже едем"}, headers=worker).status_code == 201
    run_sql(
        database_url,
        "UPDATE reports.report_message SET created_at = created_at - interval '2 minutes' "
        "WHERE report_id = :report AND text = 'Уже едем'",
        report=report,
    )
    assert _run_notifier(database_url) == 1
    assert _run_notifier(database_url, push_resident_notifications) == 1
    assert len(delivered) == 1
    assert len(api_client.get("/notifications/", headers=resident).json()) == 2


def test_long_poll_answers_at_once_when_the_chat_changed_and_times_out_otherwise(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_pem, _ = rsa_keypair
    admin = _headers(_staff_token(private_pem, subject=str(uuid4()), roles=["admin"]))
    organization_id, worker = _register_housing_organization(
        api_client, monkeypatch, private_pem, admin, "УК Поток"
    )
    house = _insert_house(database_url, formatted=f"ул. Ожидания, {uuid4().hex[:6]}")
    body = {"house_id": house, "organization_id": organization_id, "basis": "Договор управления"}
    assert api_client.post("/geo/house-management/", json=body, headers=worker).status_code == 201
    _resident_id, token = _resident_token(api_client)
    resident = _headers(token)
    category = _insert_category(database_url)
    report = api_client.post(
        "/reports/",
        json={"source_type": "MAX", "text": "Шумит лифт", "category_id": category, "house_id": house},
        headers=resident,
    ).json()["id"]
    monkeypatch.setattr("src.domains.reports.controllers.chat.MAX_WAIT_SECONDS", 0.3)

    def poll(headers: dict[str, str], since: str | None = None) -> bool:
        params = {"since": since} if since else {}
        response = api_client.get(f"/reports/{report}/messages/updates", params=params, headers=headers)
        assert response.status_code == 200, response.text
        return response.json()["changed"]

    assert poll(resident) is False
    chat = f"/reports/{report}/messages"
    sent = api_client.post(chat, json={"text": "Когда починят?"}, headers=resident).json()
    assert poll(worker) is True
    assert poll(worker, since=sent["created_at"]) is False

    # The organization reading the message is a change for the resident ("прочитано").
    api_client.get(chat, headers=worker)
    assert poll(resident, since=sent["created_at"]) is True
    assert api_client.get(f"/reports/{uuid4()}/messages/updates", headers=resident).status_code == 404


@pytest.mark.anyio
async def test_a_published_chat_event_wakes_the_waiting_subscriber(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    report_id = uuid4()
    loop = asyncio.get_running_loop()
    async with ChatSubscription(report_id) as subscription:
        started = loop.time()
        publisher = asyncio.create_task(asyncio.sleep(0.2))
        publisher.add_done_callback(lambda _task: asyncio.ensure_future(publish_chat_event(report_id)))
        assert await subscription.wait(5) is True
        assert loop.time() - started < 2
    async with ChatSubscription(uuid4()) as idle:
        assert await idle.wait(0.3) is False
