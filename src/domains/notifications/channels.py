"""Delivery strategies for organization notifications (Strategy pattern).

Each УК/ТСЖ chooses how it hears about residents' requests - ``OrganizationChannel``
rows - and every ``OrganizationChannelType`` has exactly one ``ChannelStrategy`` that
knows how to validate that channel's settings and deliver a message through it. The
dispatcher never branches on the channel type itself; adding a new channel means adding
an enum value and a strategy to ``CHANNEL_STRATEGIES``, nothing else.
"""

import hashlib
import hmac
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.models import utc_now
from src.domains.identity.models import OperatorUser, OrganizationMember
from src.domains.notifications.enums import OrganizationChannelType
from src.domains.notifications.mailer import MailDeliveryError, send_email
from src.domains.notifications.webhook_targets import (
    UnsafeWebhookTargetError,
    ensure_webhook_url_resolves_publicly,
    validate_webhook_url,
)
from src.max_bot.client import MaxApiError, MaxClient
from src.max_bot.settings import MaxBotSettings

logger = logging.getLogger(__name__)


class ChannelConfigurationError(ValueError):
    """The channel's ``target``/``secret`` don't fit its type."""


class ChannelDeliveryError(RuntimeError):
    """Delivery through one channel failed; the dispatcher retries it later."""


@dataclass(frozen=True, slots=True)
class OrganizationMessage:
    organization_id: UUID
    event_type: str
    title: str
    body: str
    incident_id: UUID | None = None
    report_id: UUID | None = None
    house_id: UUID | None = None
    requester: dict[str, Any] | None = None
    """Who filed the request - ``name``, ``max_user_id``, ``max_username``,
    ``max_profile_url`` - also sent to webhooks as structured data."""

    def to_payload(self) -> dict[str, Any]:
        return {
            "organization_id": str(self.organization_id),
            "event_type": self.event_type,
            "title": self.title,
            "body": self.body,
            "incident_id": str(self.incident_id) if self.incident_id else None,
            "report_id": str(self.report_id) if self.report_id else None,
            "house_id": str(self.house_id) if self.house_id else None,
            "requester": self.requester,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "OrganizationMessage":
        def optional(key: str) -> UUID | None:
            return UUID(payload[key]) if payload.get(key) else None

        return cls(
            organization_id=UUID(payload["organization_id"]),
            event_type=payload["event_type"],
            title=payload["title"],
            body=payload["body"],
            incident_id=optional("incident_id"),
            report_id=optional("report_id"),
            house_id=optional("house_id"),
            requester=payload.get("requester"),
        )

    @property
    def text(self) -> str:
        return f"{self.title}\n\n{self.body}"


@dataclass(frozen=True, slots=True)
class ChannelTarget:
    """What a strategy needs from a channel - decoupled from the ORM row so the implicit
    fallback channel (no ``OrganizationChannel`` configured at all) works the same way."""

    key: str
    """Stable id used to remember which channels already got a message across retries."""
    type: OrganizationChannelType
    target: str | None = None
    secret: str | None = None


class ChannelStrategy(ABC):
    type: ClassVar[OrganizationChannelType]

    @abstractmethod
    def validate(self, target: str | None, secret: str | None) -> None:
        """Raise ``ChannelConfigurationError`` if the channel settings are unusable."""

    @abstractmethod
    async def send(self, session: AsyncSession, channel: ChannelTarget, message: OrganizationMessage) -> None:
        """Deliver ``message``; raise ``ChannelDeliveryError`` on a (retryable) failure."""


def _max_client() -> MaxClient:
    try:
        return MaxClient(MaxBotSettings.from_environment())
    except ValueError as exc:
        raise ChannelDeliveryError(f"MAX bot is not configured: {exc}") from exc


class MaxMembersStrategy(ChannelStrategy):
    type = OrganizationChannelType.MAX_MEMBERS

    def validate(self, target: str | None, secret: str | None) -> None:
        if target or secret:
            raise ChannelConfigurationError("MAX_MEMBERS takes neither target nor secret")

    async def send(self, session: AsyncSession, channel: ChannelTarget, message: OrganizationMessage) -> None:
        recipients = (
            await session.scalars(
                select(OperatorUser.max_user_id)
                .join(OrganizationMember, OrganizationMember.user_id == OperatorUser.id)
                .where(
                    OrganizationMember.organization_id == message.organization_id,
                    OrganizationMember.is_active.is_(True),
                    OperatorUser.is_active.is_(True),
                    OperatorUser.max_user_id.is_not(None),
                )
            )
        ).all()
        if not recipients:
            return
        client = _max_client()
        failed = 0
        for max_user_id in recipients:
            try:
                await client.send_message(text=message.text, user_id=max_user_id)
            except (MaxApiError, OSError):
                failed += 1
                logger.warning(
                    "Could not message an organization member in MAX",
                    extra={"organization_id": str(message.organization_id), "max_user_id": max_user_id},
                    exc_info=True,
                )
        if failed == len(recipients):
            raise ChannelDeliveryError(f"MAX delivery failed for all {failed} members")


class MaxChatStrategy(ChannelStrategy):
    type = OrganizationChannelType.MAX_CHAT

    def validate(self, target: str | None, secret: str | None) -> None:
        if not target or not target.lstrip("-").isdigit():
            raise ChannelConfigurationError("MAX_CHAT target must be a numeric chat_id")
        if secret:
            raise ChannelConfigurationError("MAX_CHAT takes no secret")

    async def send(self, session: AsyncSession, channel: ChannelTarget, message: OrganizationMessage) -> None:
        assert channel.target is not None
        try:
            await _max_client().send_message(text=message.text, chat_id=int(channel.target))
        except (MaxApiError, OSError) as exc:
            raise ChannelDeliveryError(f"MAX chat delivery failed: {exc}") from exc


class EmailStrategy(ChannelStrategy):
    type = OrganizationChannelType.EMAIL

    def validate(self, target: str | None, secret: str | None) -> None:
        if not target or "@" not in target or any(char.isspace() for char in target):
            raise ChannelConfigurationError("EMAIL target must be an e-mail address")
        if secret:
            raise ChannelConfigurationError("EMAIL takes no secret")

    async def send(self, session: AsyncSession, channel: ChannelTarget, message: OrganizationMessage) -> None:
        assert channel.target is not None
        try:
            await send_email(channel.target, message.title, message.body)
        except MailDeliveryError as exc:
            raise ChannelDeliveryError(str(exc)) from exc


class WebhookStrategy(ChannelStrategy):
    type = OrganizationChannelType.WEBHOOK

    def validate(self, target: str | None, secret: str | None) -> None:
        if not target:
            raise ChannelConfigurationError("WEBHOOK target must be an https:// URL")
        try:
            validate_webhook_url(target)
        except UnsafeWebhookTargetError as exc:
            raise ChannelConfigurationError(str(exc)) from exc

    async def send(self, session: AsyncSession, channel: ChannelTarget, message: OrganizationMessage) -> None:
        assert channel.target is not None
        body = json.dumps(
            {**message.to_payload(), "sent_at": utc_now().isoformat()}, ensure_ascii=False
        ).encode()
        headers = {"Content-Type": "application/json", "X-SmartCity-Event": message.event_type}
        if channel.secret:
            signature = hmac.new(channel.secret.encode(), body, hashlib.sha256).hexdigest()
            headers["X-SmartCity-Signature"] = f"sha256={signature}"
        try:
            await ensure_webhook_url_resolves_publicly(channel.target)
        except UnsafeWebhookTargetError as exc:
            raise ChannelDeliveryError(str(exc)) from exc
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=False, trust_env=False) as client:
                response = await client.post(channel.target, content=body, headers=headers)
        except httpx.HTTPError as exc:
            raise ChannelDeliveryError(f"Webhook request failed: {exc}") from exc
        if response.status_code >= 300:
            raise ChannelDeliveryError(f"Webhook answered {response.status_code}")


CHANNEL_STRATEGIES: dict[OrganizationChannelType, ChannelStrategy] = {
    strategy.type: strategy
    for strategy in (MaxMembersStrategy(), MaxChatStrategy(), EmailStrategy(), WebhookStrategy())
}


def strategy_for(channel_type: OrganizationChannelType) -> ChannelStrategy:
    return CHANNEL_STRATEGIES[channel_type]
