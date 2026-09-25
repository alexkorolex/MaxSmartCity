"""Links into MAX that can be built from what the Bot API tells us about a user."""

import re

_USERNAME = re.compile(r"[A-Za-z0-9_.]{2,64}")


def max_profile_url(username: str | None) -> str | None:
    if not username:
        return None
    nickname = username.strip().lstrip("@")
    return f"https://max.ru/{nickname}" if _USERNAME.fullmatch(nickname) else None
