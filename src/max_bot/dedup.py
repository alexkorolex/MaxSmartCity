import secrets
from uuid import UUID

from src.database.cache import CacheSettings

WEBHOOK_DEDUP_TTL_SECONDS = 24 * 3600
LOGIN_CODE_TTL_SECONDS = 5 * 60


async def is_duplicate_event(delivery_key: str) -> bool:
    """MAX may redeliver the same Update after a timeout; check before processing it twice."""
    store = CacheSettings.from_environment().max_webhook_dedup_store()
    return await store.exists(delivery_key)


async def mark_event_processed(delivery_key: str) -> None:
    store = CacheSettings.from_environment().max_webhook_dedup_store()
    await store.set(delivery_key, b"1", expires_in=WEBHOOK_DEDUP_TTL_SECONDS)


async def create_login_code(resident_id: UUID) -> str:
    """Short-lived, single-use code the bot hands a resident so they can log into the web app."""
    store = CacheSettings.from_environment().max_login_code_store()
    code = secrets.token_urlsafe(24)
    await store.set(code, str(resident_id).encode(), expires_in=LOGIN_CODE_TTL_SECONDS)
    return code


async def consume_login_code(code: str) -> UUID | None:
    store = CacheSettings.from_environment().max_login_code_store()
    value = await store.get(code)
    if value is None:
        return None
    await store.delete(code)
    return UUID(value.decode())
