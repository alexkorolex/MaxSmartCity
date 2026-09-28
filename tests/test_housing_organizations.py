import hashlib
import hmac
import json
from uuid import uuid4

import pytest

from src.common.state_machine import InvalidStateTransition
from src.domains.identity.enums import OrganizationType
from src.domains.identity.validation import (
    OrganizationRequisitesError,
    is_valid_inn,
    is_valid_ogrn,
    validate_housing_requisites,
)
from src.domains.notifications.channels import (
    CHANNEL_STRATEGIES,
    ChannelConfigurationError,
    ChannelTarget,
    OrganizationMessage,
    WebhookStrategy,
    strategy_for,
)
from src.domains.notifications.enums import OrganizationChannelType
from src.domains.reports.enums import ReportStatus
from src.domains.reports.state_machine import ensure_report_transition

VALID_INN = "7707083893"
VALID_OGRN = "1027700132195"


@pytest.mark.parametrize(
    ("inn", "expected"),
    [
        ("7707083893", True),
        ("500100732259", True),
        ("7707083894", False),
        ("770708389", False),
        ("77070838930", False),
        ("77070838a3", False),
    ],
)
def test_inn_checksum(inn: str, expected: bool) -> None:
    assert is_valid_inn(inn) is expected


@pytest.mark.parametrize(
    ("ogrn", "expected"),
    [
        ("1027700132195", True),
        ("304500116000157", True),
        ("1027700132196", False),
        ("102770013219", False),
    ],
)
def test_ogrn_checksum(ogrn: str, expected: bool) -> None:
    assert is_valid_ogrn(ogrn) is expected


def test_management_company_requires_license() -> None:
    with pytest.raises(OrganizationRequisitesError, match="license"):
        validate_housing_requisites(
            organization_type=OrganizationType.MANAGEMENT_COMPANY,
            inn=VALID_INN,
            ogrn=VALID_OGRN,
            license_number=None,
            in_reserve_registry=False,
        )
    validate_housing_requisites(
        organization_type=OrganizationType.MANAGEMENT_COMPANY,
        inn=VALID_INN,
        ogrn=VALID_OGRN,
        license_number="077-000123",
        in_reserve_registry=True,
    )


@pytest.mark.parametrize(
    ("license_number", "in_reserve_registry"),
    [("077-000123", False), (None, True)],
)
def test_hoa_is_neither_licensed_nor_in_reserve_registry(
    license_number: str | None, in_reserve_registry: bool
) -> None:
    with pytest.raises(OrganizationRequisitesError):
        validate_housing_requisites(
            organization_type=OrganizationType.HOA,
            inn=VALID_INN,
            ogrn=VALID_OGRN,
            license_number=license_number,
            in_reserve_registry=in_reserve_registry,
        )


def test_only_housing_organizations_self_register() -> None:
    with pytest.raises(OrganizationRequisitesError, match="self-register"):
        validate_housing_requisites(
            organization_type=OrganizationType.WATER_UTILITY,
            inn=VALID_INN,
            ogrn=VALID_OGRN,
            license_number=None,
            in_reserve_registry=False,
        )


def test_resident_request_closes_and_reopens_with_its_incident() -> None:
    ensure_report_transition(ReportStatus.LINKED, ReportStatus.CLOSED)
    ensure_report_transition(ReportStatus.CLOSED, ReportStatus.LINKED)
    ensure_report_transition(ReportStatus.RECEIVED, ReportStatus.CLOSED)
    with pytest.raises(InvalidStateTransition):
        ensure_report_transition(ReportStatus.REJECTED, ReportStatus.CLOSED)


def test_every_channel_type_has_a_strategy() -> None:
    assert set(CHANNEL_STRATEGIES) == set(OrganizationChannelType)
    for channel_type, strategy in CHANNEL_STRATEGIES.items():
        assert strategy.type is channel_type


@pytest.mark.parametrize(
    ("channel_type", "target", "secret", "valid"),
    [
        (OrganizationChannelType.MAX_MEMBERS, None, None, True),
        (OrganizationChannelType.MAX_MEMBERS, "123", None, False),
        (OrganizationChannelType.MAX_CHAT, "-100123", None, True),
        (OrganizationChannelType.MAX_CHAT, "chat", None, False),
        (OrganizationChannelType.EMAIL, "dispatch@uk.example", None, True),
        (OrganizationChannelType.EMAIL, "not-an-email", None, False),
        (OrganizationChannelType.WEBHOOK, "https://crm.uk.example/hook", "s3cret", True),
        (OrganizationChannelType.WEBHOOK, "http://crm.uk.example/hook", None, False),
    ],
)
def test_channel_settings_are_validated_by_their_strategy(
    channel_type: OrganizationChannelType, target: str | None, secret: str | None, valid: bool
) -> None:
    strategy = strategy_for(channel_type)
    if valid:
        strategy.validate(target, secret)
    else:
        with pytest.raises(ChannelConfigurationError):
            strategy.validate(target, secret)


def test_organization_message_round_trips_through_outbox_payload() -> None:
    message = OrganizationMessage(
        organization_id=uuid4(),
        event_type="RESIDENT_REPORT_RECEIVED",
        title="Новая заявка жителя",
        body="ул. Ленина, 1",
        incident_id=uuid4(),
        house_id=uuid4(),
    )
    assert OrganizationMessage.from_payload(json.loads(json.dumps(message.to_payload()))) == message


@pytest.mark.anyio
async def test_webhook_is_signed_with_the_channel_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: dict[str, object] = {}

    async def resolves_publicly(_url: str) -> None:
        return None

    monkeypatch.setattr(
        "src.domains.notifications.channels.ensure_webhook_url_resolves_publicly", resolves_publicly
    )

    class FakeResponse:
        status_code = 204

    class FakeClient:
        def __init__(self, **_kwargs: object) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, url: str, *, content: bytes, headers: dict[str, str]) -> FakeResponse:
            sent.update(url=url, content=content, headers=headers)
            return FakeResponse()

    monkeypatch.setattr("src.domains.notifications.channels.httpx.AsyncClient", FakeClient)
    message = OrganizationMessage(organization_id=uuid4(), event_type="TEST", title="t", body="b")
    channel = ChannelTarget(
        key="1", type=OrganizationChannelType.WEBHOOK, target="https://crm.example/hook", secret="k"
    )
    await WebhookStrategy().send(None, channel, message)  # ty: ignore[invalid-argument-type]

    content = sent["content"]
    assert isinstance(content, bytes)
    headers = sent["headers"]
    assert isinstance(headers, dict)
    expected = hmac.new(b"k", content, hashlib.sha256).hexdigest()
    assert headers["X-SmartCity-Signature"] == f"sha256={expected}"
    assert json.loads(content)["organization_id"] == str(message.organization_id)
