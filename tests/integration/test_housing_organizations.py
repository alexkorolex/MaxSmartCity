"""Housing organizations (УК/ТСЖ, Постановление №1616): self-registration and moderation,
house management, routing residents' requests to the managing organization, notification
delivery strategies, and closing a resident's request once the problem is solved."""

import random
from datetime import timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.models import utc_now
from src.domains.geo.models import HouseManagement
from src.domains.geo.schemas import AssignHouseManagementCommand, TerminateHouseManagementCommand
from src.domains.geo.services import (
    HouseManagementConflictError,
    HouseManagementService,
    active_house_manager_id,
)
from src.domains.identity.enums import OrganizationRegistrationStatus, OrganizationType
from src.domains.identity.models import OperatorUser, Organization, Resident
from src.domains.identity.schemas import OrganizationRegistrationRequest, StaffAccountRequest
from src.domains.identity.services import (
    IdentityConflictError,
    OrganizationMemberService,
    OrganizationService,
    StaffAccountError,
)
from src.domains.identity.validation import OrganizationRequisitesError
from src.domains.incidents.enums import IncidentStatus, ResolutionDisputeStatus, ResolutionFeedback
from src.domains.incidents.models import Incident, ResolutionDispute
from src.domains.incidents.schemas import ResolutionFeedbackCommand, TransitionIncidentCommand
from src.domains.incidents.services import IncidentCoreService
from src.domains.infrastructure.enums import OutboxStatus
from src.domains.infrastructure.models import OutboxEvent
from src.domains.notifications.channels import (
    ChannelDeliveryError,
    ChannelStrategy,
    ChannelTarget,
    OrganizationMessage,
)
from src.domains.notifications.dispatcher import (
    ORGANIZATION_NOTIFICATION_EVENT,
    OrganizationNotificationDispatcher,
    enqueue_organization_notification,
)
from src.domains.notifications.enums import NotificationType, OrganizationChannelType
from src.domains.notifications.models import Notification, OrganizationChannel
from src.domains.reports.enums import ReportStatus
from src.domains.reports.models import Report
from src.domains.reports.schemas import CreateReportCommand
from src.domains.reports.services import ReportIntakeService
from tests.integration.test_incident_core import _catalog

_INN10_WEIGHTS = (2, 4, 10, 3, 5, 9, 4, 6, 8)


def random_inn() -> str:
    body = "".join(random.choices("0123456789", k=9))
    check = sum(int(digit) * weight for digit, weight in zip(body, _INN10_WEIGHTS, strict=True)) % 11 % 10
    return f"{body}{check}"


def random_ogrn() -> str:
    body = "1" + "".join(random.choices("0123456789", k=11))
    return f"{body}{int(body) % 11 % 10}"


def _registration(**overrides: object) -> OrganizationRegistrationRequest:
    values: dict[str, object] = {
        "code": f"uk-{uuid4().hex}",
        "name": "УК Тестовая",
        "type": OrganizationType.MANAGEMENT_COMPANY,
        "inn": random_inn(),
        "ogrn": random_ogrn(),
        "license_number": "077-000123",
        "employee": StaffAccountRequest(
            login=f"dispatcher-{uuid4().hex[:8]}", password="password-123", display_name="Диспетчер УК"
        ),
    }
    values.update(overrides)
    return OrganizationRegistrationRequest(**values)  # ty: ignore[invalid-argument-type]


@pytest.fixture
def keycloak_accounts(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Stands in for the Keycloak Admin API: records created logins, returns a subject."""
    created: list[str] = []

    async def fake_create_staff_user(_settings: object, *, login: str, role: str, **_kwargs: object) -> str:
        assert role == "housing_worker"
        created.append(login)
        return str(uuid4())

    monkeypatch.setattr("src.domains.identity.services.create_staff_user", fake_create_staff_user)
    monkeypatch.setattr("src.domains.identity.services.SecuritySettings.from_environment", lambda: None)
    return created


async def _approved_organization(
    db_session: AsyncSession,
    *,
    organization_type: OrganizationType = OrganizationType.MANAGEMENT_COMPANY,
    in_reserve_registry: bool = False,
    registration_status: OrganizationRegistrationStatus = OrganizationRegistrationStatus.APPROVED,
) -> Organization:
    organization = Organization(
        code=f"org-{uuid4().hex}",
        name="УК Дом",
        type=organization_type,
        inn=random_inn(),
        ogrn=random_ogrn(),
        license_number="077-000123" if organization_type is OrganizationType.MANAGEMENT_COMPANY else None,
        in_reserve_registry=in_reserve_registry,
        registration_status=registration_status,
        enabled=registration_status is OrganizationRegistrationStatus.APPROVED,
    )
    db_session.add(organization)
    await db_session.flush()
    return organization


async def _organization_notifications(db_session: AsyncSession, organization_id: UUID) -> list[OutboxEvent]:
    return list(
        (
            await db_session.scalars(
                select(OutboxEvent)
                .where(
                    OutboxEvent.event_type == ORGANIZATION_NOTIFICATION_EVENT,
                    OutboxEvent.aggregate_id == organization_id,
                )
                .order_by(OutboxEvent.created_at)
            )
        ).all()
    )


@pytest.mark.anyio
async def test_admin_registers_organization_with_its_first_employee(
    db_session: AsyncSession, keycloak_accounts: list[str]
) -> None:
    service = OrganizationService(session=db_session)
    request = _registration()

    organization, member = await service.register_with_employee(request, registered_by=uuid4())
    assert organization.registration_status is OrganizationRegistrationStatus.APPROVED
    assert organization.enabled is True
    assert member.is_active is True
    employee = await db_session.get(OperatorUser, member.user_id)
    assert employee is not None
    assert employee.login == request.employee.login
    assert employee.keycloak_subject is not None
    assert keycloak_accounts == [request.employee.login]

    extra = await OrganizationMemberService(session=db_session).create_account(
        organization.id,
        StaffAccountRequest(
            login=f"worker-{uuid4().hex[:8]}", password="password-123", display_name="Мастер"
        ),
    )
    assert extra.organization_id == organization.id
    assert len(keycloak_accounts) == 2

    # Every local check runs before Keycloak is called - rejected requests create no login.
    with pytest.raises(IdentityConflictError, match="INN"):
        await service.register_with_employee(_registration(inn=request.inn), registered_by=uuid4())
    with pytest.raises(IdentityConflictError, match="Login"):
        await service.register_with_employee(_registration(employee=request.employee), registered_by=uuid4())
    with pytest.raises(StaffAccountError, match="password"):
        await service.register_with_employee(
            _registration(employee=StaffAccountRequest(login="short", password="123", display_name="X")),
            registered_by=uuid4(),
        )
    with pytest.raises(OrganizationRequisitesError, match="license"):
        await service.register_with_employee(_registration(license_number=None), registered_by=uuid4())
    assert len(keycloak_accounts) == 2


@pytest.mark.anyio
async def test_house_manager_is_replaced_and_reserve_registry_is_enforced(db_session: AsyncSession) -> None:
    house, _category = await _catalog(db_session)
    chosen = await _approved_organization(db_session, organization_type=OrganizationType.HOA)
    reserve = await _approved_organization(db_session, in_reserve_registry=True)
    not_in_registry = await _approved_organization(db_session)
    pending = await _approved_organization(
        db_session, registration_status=OrganizationRegistrationStatus.PENDING
    )
    service = HouseManagementService(session=db_session)

    first = await service.assign(
        AssignHouseManagementCommand(
            house_id=house.id, organization_id=chosen.id, basis="Протокол общего собрания №1"
        ),
        changed_by=uuid4(),
    )
    assert await active_house_manager_id(db_session, house.id) == chosen.id

    with pytest.raises(HouseManagementConflictError, match="Перечень"):
        await service.assign(
            AssignHouseManagementCommand(
                house_id=house.id,
                organization_id=not_in_registry.id,
                basis="Решение администрации",
                assigned_via_reserve_registry=True,
            ),
            changed_by=uuid4(),
        )
    with pytest.raises(HouseManagementConflictError, match="not approved"):
        await service.assign(
            AssignHouseManagementCommand(house_id=house.id, organization_id=pending.id, basis="x"),
            changed_by=uuid4(),
        )

    second = await service.assign(
        AssignHouseManagementCommand(
            house_id=house.id,
            organization_id=reserve.id,
            basis="Решение администрации об определении УК из Перечня",
            assigned_via_reserve_registry=True,
        ),
        changed_by=uuid4(),
    )
    assert first.is_active is False
    assert first.effective_to == second.effective_from
    assert await active_house_manager_id(db_session, house.id) == reserve.id

    await service.terminate(
        second.id, TerminateHouseManagementCommand(reason="Договор расторгнут"), changed_by=uuid4()
    )
    assert await active_house_manager_id(db_session, house.id) is None
    rows = (
        await db_session.scalars(select(HouseManagement).where(HouseManagement.house_id == house.id))
    ).all()
    assert len(rows) == 2


async def _resident_request(db_session: AsyncSession) -> tuple[Organization, Resident, Report, Incident]:
    house, category = await _catalog(db_session)
    manager = await _approved_organization(db_session)
    await HouseManagementService(session=db_session).assign(
        AssignHouseManagementCommand(house_id=house.id, organization_id=manager.id, basis="Протокол №1"),
        changed_by=uuid4(),
    )
    resident = Resident(max_user_id=30_000 + int(uuid4().hex[:6], 16))
    db_session.add(resident)
    await db_session.flush()
    created = await ReportIntakeService(db_session).create(
        CreateReportCommand(
            source_external_id=f"max-{uuid4()}",
            house_id=house.id,
            category_code=category.code,
            text="Течёт крыша над подъездом",
        ),
        resident_id=resident.id,
    )
    report = await db_session.get(Report, created.report_id)
    incident = await db_session.get(Incident, created.grouping.incident_id)
    assert report is not None
    assert incident is not None
    return manager, resident, report, incident


async def _resolve(db_session: AsyncSession, incident: Incident) -> None:
    service = IncidentCoreService(db_session)
    for target in (IncidentStatus.TRIAGE, IncidentStatus.CONFIRMED, IncidentStatus.RESOLVED):
        await service.transition_incident(
            incident.id,
            TransitionIncidentCommand(target_status=target, expected_version=incident.version),
            changed_by_id=uuid4(),
        )


async def _resident_notifications(db_session: AsyncSession, resident: Resident) -> list[NotificationType]:
    rows = await db_session.scalars(
        select(Notification.type)
        .where(Notification.resident_id == resident.id)
        .order_by(Notification.created_at)
    )
    return list(rows.all())


@pytest.mark.anyio
async def test_resident_request_reaches_house_manager_and_closes_after_confirmation(
    db_session: AsyncSession,
) -> None:
    manager, resident, report, incident = await _resident_request(db_session)
    routed = [
        event
        for event in await _organization_notifications(db_session, manager.id)
        if event.payload["event_type"] == "RESIDENT_REPORT_RECEIVED"
    ]
    assert len(routed) == 1
    assert routed[0].payload["report_id"] == str(report.id)
    assert routed[0].payload["incident_id"] == str(incident.id)

    await _resolve(db_session, incident)
    assert await _resident_notifications(db_session, resident) == [NotificationType.RESOLUTION_REQUESTED]
    assert report.status is ReportStatus.LINKED

    service = IncidentCoreService(db_session)
    await service.record_resolution_feedback(
        incident.id,
        ResolutionFeedbackCommand(report_id=report.id, feedback=ResolutionFeedback.CONFIRMED),
        resident_id=resident.id,
    )
    assert incident.status is IncidentStatus.CLOSED
    assert report.status is ReportStatus.CLOSED
    assert (await _resident_notifications(db_session, resident))[-1] is NotificationType.REPORT_STATUS_CHANGED

    await service.transition_incident(
        incident.id,
        TransitionIncidentCommand(
            target_status=IncidentStatus.REOPENED, expected_version=incident.version, reason="Снова течёт"
        ),
        changed_by_id=uuid4(),
    )
    assert report.status is ReportStatus.LINKED
    assert incident.closed_at is None


@pytest.mark.anyio
async def test_unanswered_resolution_is_closed_automatically_unless_disputed(
    db_session: AsyncSession,
) -> None:
    _manager, resident, report, incident = await _resident_request(db_session)
    _other_manager, other_resident, other_report, disputed = await _resident_request(db_session)
    for item in (incident, disputed):
        await _resolve(db_session, item)
        item.resolved_at = utc_now() - timedelta(days=4)
    db_session.add(
        ResolutionDispute(
            incident_id=disputed.id,
            resident_id=other_resident.id,
            report_id=other_report.id,
            status=ResolutionDisputeStatus.OPEN,
        )
    )
    await db_session.flush()

    closed = await IncidentCoreService(db_session).close_unconfirmed_resolutions()
    assert closed >= 1
    assert incident.status is IncidentStatus.CLOSED
    assert report.status is ReportStatus.CLOSED
    assert disputed.status is IncidentStatus.RESOLVED
    assert other_report.status is ReportStatus.LINKED
    assert NotificationType.REPORT_STATUS_CHANGED in await _resident_notifications(db_session, resident)


class RecordingStrategy(ChannelStrategy):
    def __init__(self, channel_type: OrganizationChannelType, failures: int = 0) -> None:
        self.type = channel_type  # ty: ignore[invalid-attribute-access]
        self.failures = failures
        self.sent: list[tuple[str, str]] = []

    def validate(self, target: str | None, secret: str | None) -> None:
        return None

    async def send(self, session: AsyncSession, channel: ChannelTarget, message: OrganizationMessage) -> None:
        if self.failures:
            self.failures -= 1
            raise ChannelDeliveryError("temporarily down")
        self.sent.append((channel.key, message.title))


@pytest.mark.anyio
async def test_dispatcher_fans_out_by_strategy_and_retries_only_failed_channels(
    db_session: AsyncSession,
) -> None:
    organization = await _approved_organization(db_session)
    chat = OrganizationChannel(
        organization_id=organization.id, type=OrganizationChannelType.MAX_CHAT, target="-1"
    )
    mail = OrganizationChannel(
        organization_id=organization.id, type=OrganizationChannelType.EMAIL, target="a@b.c"
    )
    disabled = OrganizationChannel(
        organization_id=organization.id, type=OrganizationChannelType.MAX_CHAT, target="-2", is_active=False
    )
    db_session.add_all([chat, mail, disabled])
    await db_session.flush()
    enqueue_organization_notification(
        db_session,
        OrganizationMessage(organization_id=organization.id, event_type="TEST", title="Заявка", body="Текст"),
    )
    await db_session.flush()
    (event,) = await _organization_notifications(db_session, organization.id)

    max_chat = RecordingStrategy(OrganizationChannelType.MAX_CHAT)
    email = RecordingStrategy(OrganizationChannelType.EMAIL, failures=1)
    dispatcher = OrganizationNotificationDispatcher(
        db_session, {OrganizationChannelType.MAX_CHAT: max_chat, OrganizationChannelType.EMAIL: email}
    )

    await dispatcher.deliver(event)
    assert max_chat.sent == [(str(chat.id), "Заявка")]
    assert email.sent == []
    assert event.status is OutboxStatus.PENDING
    assert event.attempts == 1
    assert event.next_retry_at is not None
    assert "EMAIL" in str(event.payload["last_error"])

    await dispatcher.deliver(event)
    assert max_chat.sent == [(str(chat.id), "Заявка")]
    assert email.sent == [(str(mail.id), "Заявка")]
    assert event.status is OutboxStatus.PUBLISHED
    assert event.published_at is not None


@pytest.mark.anyio
async def test_organization_without_channels_falls_back_to_members_in_max(db_session: AsyncSession) -> None:
    organization = await _approved_organization(db_session)
    enqueue_organization_notification(
        db_session,
        OrganizationMessage(organization_id=organization.id, event_type="TEST", title="Заявка", body="Текст"),
    )
    await db_session.flush()
    (event,) = await _organization_notifications(db_session, organization.id)
    members = RecordingStrategy(OrganizationChannelType.MAX_MEMBERS)

    await OrganizationNotificationDispatcher(
        db_session, {OrganizationChannelType.MAX_MEMBERS: members}
    ).deliver(event)
    assert members.sent == [("fallback:MAX_MEMBERS", "Заявка")]
    assert event.status is OutboxStatus.PUBLISHED


@pytest.mark.anyio
async def test_new_request_notification_says_who_filed_it(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ADMIN_PANEL_URL", "https://admin.example/")
    house, category = await _catalog(db_session)
    manager = await _approved_organization(db_session)
    await HouseManagementService(session=db_session).assign(
        AssignHouseManagementCommand(house_id=house.id, organization_id=manager.id, basis="Протокол №1"),
        changed_by=uuid4(),
    )
    named = Resident(
        max_user_id=50_000 + int(uuid4().hex[:5], 16), display_name="Иван Петров", username="ivan_p"
    )
    anonymous = Resident(max_user_id=60_000 + int(uuid4().hex[:5], 16))
    db_session.add_all([named, anonymous])
    await db_session.flush()
    intake = ReportIntakeService(db_session)
    for resident, text in ((named, "Нет горячей воды"), (anonymous, "Нет горячей воды во всём подъезде")):
        await intake.create(
            CreateReportCommand(
                source_external_id=f"max-{uuid4()}", house_id=house.id, category_code=category.code, text=text
            ),
            resident_id=resident.id,
        )

    received: list[dict[str, Any]] = [
        cast(dict[str, Any], event.payload)
        for event in await _organization_notifications(db_session, manager.id)
        if event.payload["event_type"] == "RESIDENT_REPORT_RECEIVED"
    ]
    assert len(received) == 2
    first, second = received
    assert "Заявитель: Иван Петров" in first["body"]
    assert "Профиль MAX: https://max.ru/ivan_p" in first["body"]
    assert f"Открыть в панели: https://admin.example/incidents/{first['incident_id']}" in first["body"]
    assert first["requester"] == {
        "name": "Иван Петров",
        "max_user_id": named.max_user_id,
        "max_username": "ivan_p",
        "max_profile_url": "https://max.ru/ivan_p",
    }
    assert "Заявитель: имя не указано" in second["body"]
    assert f"MAX ID: {anonymous.max_user_id} (публичного профиля нет)" in second["body"]
    assert second["requester"]["max_profile_url"] is None
