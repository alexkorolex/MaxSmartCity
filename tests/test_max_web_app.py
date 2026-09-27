import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from src.max_bot.web_app import InvalidInitDataError, verify_init_data

BOT_TOKEN = "test-bot-token"
NOW = 1_790_000_000


def sign(fields: dict[str, str], bot_token: str = BOT_TOKEN) -> str:
    launch_params = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret_key, launch_params.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": signature})


def fields(**overrides: str) -> dict[str, str]:
    user = {"id": 4242, "first_name": "Иван", "last_name": "Петров", "username": "ivan"}
    return {
        "auth_date": str(NOW - 60),
        "query_id": "q-1",
        "user": json.dumps(user, ensure_ascii=False),
        "start_param": "abc",
        **overrides,
    }


def test_valid_init_data_returns_user() -> None:
    user = verify_init_data(sign(fields()), BOT_TOKEN, now=NOW)

    assert user.max_user_id == 4242
    assert user.username == "ivan"
    assert user.display_name == "Иван Петров"


def test_tampered_value_is_rejected() -> None:
    init_data = sign(fields()).replace("start_param=abc", "start_param=abd")

    with pytest.raises(InvalidInitDataError, match="signature"):
        verify_init_data(init_data, BOT_TOKEN, now=NOW)


def test_other_bot_token_is_rejected() -> None:
    with pytest.raises(InvalidInitDataError, match="signature"):
        verify_init_data(sign(fields(), bot_token="another-bot"), BOT_TOKEN, now=NOW)


def test_missing_hash_is_rejected() -> None:
    with pytest.raises(InvalidInitDataError, match="signature"):
        verify_init_data(urlencode(fields()), BOT_TOKEN, now=NOW)


def test_duplicate_parameter_is_rejected() -> None:
    init_data = sign(fields()) + "&start_param=other"

    with pytest.raises(InvalidInitDataError, match="duplicate"):
        verify_init_data(init_data, BOT_TOKEN, now=NOW)


@pytest.mark.parametrize("auth_date", [NOW - 24 * 3600 - 1, NOW + 3600])
def test_stale_or_future_auth_date_is_rejected(auth_date: int) -> None:
    with pytest.raises(InvalidInitDataError, match="expired"):
        verify_init_data(sign(fields(auth_date=str(auth_date))), BOT_TOKEN, now=NOW)


def test_signed_data_without_user_is_rejected() -> None:
    data = fields()
    del data["user"]

    with pytest.raises(InvalidInitDataError, match="user"):
        verify_init_data(sign(data), BOT_TOKEN, now=NOW)


def test_malformed_init_data_is_rejected() -> None:
    with pytest.raises(InvalidInitDataError, match="malformed"):
        verify_init_data("not a query string", BOT_TOKEN, now=NOW)
