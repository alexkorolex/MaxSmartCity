from advanced_alchemy.extensions.litestar import SQLAlchemyDTO

from src.domains.infrastructure.models import IdempotencyRecord, InboundWebhookEvent, OutboxEvent


class IdempotencyRecordReadDTO(SQLAlchemyDTO[IdempotencyRecord]):
    """Internal diagnostic contract."""


class InboundWebhookEventReadDTO(SQLAlchemyDTO[InboundWebhookEvent]):
    """Internal diagnostic contract."""


class OutboxEventReadDTO(SQLAlchemyDTO[OutboxEvent]):
    """Internal diagnostic contract."""
