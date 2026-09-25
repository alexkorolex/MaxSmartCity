"""Links into MAX that can be built from what the Bot API tells us about a user."""

import re

_USERNAME = re.compile(r"[A-Za-z0-9_.]{2,64}")


def max_profile_url(username: str | None) -> str | None:
    """Public profile link, only for a user with a public nickname. Most MAX users have
    none - their profile link (``max.ru/u/<code>``) is an opaque code the Bot API doesn't
    expose, so it can't be derived from the numeric user id."""
    if not username:
        return None
    nickname = username.strip().lstrip("@")
    return f"https://max.ru/{nickname}" if _USERNAME.fullmatch(nickname) else None
