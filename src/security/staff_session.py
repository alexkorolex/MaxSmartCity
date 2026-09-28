import os

from litestar.datastructures import Cookie

STAFF_REFRESH_COOKIE = "sc_staff_refresh"
DEFAULT_STAFF_REFRESH_COOKIE_PATH = "/api/auth/staff"


def _cookie_path() -> str:
    return os.environ.get("STAFF_REFRESH_COOKIE_PATH") or DEFAULT_STAFF_REFRESH_COOKIE_PATH


def refresh_cookie(refresh_token: str, max_age: int | None) -> Cookie:
    return Cookie(
        key=STAFF_REFRESH_COOKIE,
        value=refresh_token,
        max_age=max_age,
        path=_cookie_path(),
        httponly=True,
        secure=True,
        samesite="strict",
    )


def expired_refresh_cookie() -> Cookie:
    return Cookie(
        key=STAFF_REFRESH_COOKIE,
        value="",
        max_age=0,
        path=_cookie_path(),
        httponly=True,
        secure=True,
        samesite="strict",
    )
