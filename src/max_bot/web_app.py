import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl

from src.database.logging import database_action
from src.domains.identity.models import Resident
from src.domains.identity.services import ResidentService
from src.max_bot.handlers import _display_name

INIT_DATA_MAX_AGE_SECONDS = 24 * 3600
INIT_DATA_CLOCK_SKEW_SECONDS = 60


class InvalidInitDataError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class WebAppUser:
    max_user_id: int
    username: str | None
    display_name: str | None


def _signature(fields: dict[str, str], bot_token: str) -> str:
    launch_params = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    return hmac.new(secret_key, launch_params.encode(), hashlib.sha256).hexdigest()


def verify_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = INIT_DATA_MAX_AGE_SECONDS,
    now: float | None = None,
) -> WebAppUser:
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise InvalidInitDataError("initData is malformed") from exc
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise InvalidInitDataError("initData has duplicate parameters")

    received_hash = fields.pop("hash", "")
    if not received_hash or not hmac.compare_digest(_signature(fields, bot_token), received_hash.lower()):
        raise InvalidInitDataError("initData signature is invalid")

    try:
        auth_date = int(fields["auth_date"])
    except (KeyError, ValueError) as exc:
        raise InvalidInitDataError("initData has no valid auth_date") from exc
    current = time.time() if now is None else now
    if auth_date > current + INIT_DATA_CLOCK_SKEW_SECONDS or current - auth_date > max_age_seconds:
        raise InvalidInitDataError("initData has expired")

    try:
        user = json.loads(fields["user"])
        max_user_id = int(user["id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidInitDataError("initData has no valid user") from exc
    return WebAppUser(
        max_user_id=max_user_id,
        username=user.get("username") or None,
        display_name=_display_name(user.get("first_name"), user.get("last_name")),
    )


async def authenticate_web_app_resident(
    init_data: str, bot_token: str, resident_service: ResidentService
) -> Resident:
    user = verify_init_data(init_data, bot_token)
    with database_action("upsert", "identity.Resident"):
        return await resident_service.upsert_by_max_user_id(
            max_user_id=user.max_user_id, username=user.username, display_name=user.display_name
        )
