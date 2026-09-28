from typing import Any

from src.security.keycloak import (
    KeycloakLoginError,
    KeycloakPasswordChangeRequired,
    login_staff_with_password,
)
from src.security.keycloak_admin import complete_initial_password
from src.security.settings import SecuritySettings

MIN_STAFF_PASSWORD_LENGTH = 8


class InitialPasswordError(ValueError):
    pass


class PasswordChangeNotRequiredError(RuntimeError):
    pass


async def change_initial_password(
    settings: SecuritySettings, *, username: str, password: str, new_password: str
) -> dict[str, Any]:
    if len(new_password) < MIN_STAFF_PASSWORD_LENGTH:
        raise InitialPasswordError(f"Password must be at least {MIN_STAFF_PASSWORD_LENGTH} characters long")
    if new_password == password:
        raise InitialPasswordError("The new password must differ from the temporary one")
    try:
        await login_staff_with_password(settings, username=username, password=password)
    except KeycloakPasswordChangeRequired:
        await complete_initial_password(settings, username=username, password=new_password)
        return await login_staff_with_password(settings, username=username, password=new_password)
    except KeycloakLoginError:
        raise
    raise PasswordChangeNotRequiredError("This account has no temporary password")
