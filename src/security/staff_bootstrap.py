from src.security.keycloak_admin import realm_role_has_users
from src.security.settings import SecuritySettings

BOOTSTRAP_ROLE = "admin"


class StaffBootstrapClosedError(RuntimeError):
    pass


async def ensure_bootstrap_allowed(settings: SecuritySettings, role: str) -> None:
    if role != BOOTSTRAP_ROLE:
        raise StaffBootstrapClosedError("The bootstrap secret can only create the first administrator")
    if await realm_role_has_users(settings, BOOTSTRAP_ROLE):
        raise StaffBootstrapClosedError("An administrator already exists; the bootstrap secret is closed")
