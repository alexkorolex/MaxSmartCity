import httpx

from src.security.settings import SecuritySettings


class KeycloakAdminError(RuntimeError):
    """Raised when a Keycloak Admin REST API call fails."""

    def __init__(self, message: str, *, conflict: bool = False) -> None:
        super().__init__(message)
        self.conflict = conflict


async def _admin_token(settings: SecuritySettings, client: httpx.AsyncClient) -> str:
    response = await client.post(
        settings.keycloak_master_token_url,
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": settings.keycloak_admin_username,
            "password": settings.keycloak_admin_password,
        },
    )
    if response.status_code != httpx.codes.OK:
        raise KeycloakAdminError(f"Could not obtain a Keycloak admin token: {response.text}")
    return response.json()["access_token"]


async def create_staff_user(
    settings: SecuritySettings,
    *,
    login: str,
    password: str,
    email: str | None,
    display_name: str,
    role: str,
) -> str:
    """Create a user in the Keycloak realm, assign one realm role, and return its subject id.

    This is the only place in the backend that talks to Keycloak's Admin REST API - staff
    accounts otherwise live entirely inside Keycloak (optionally LDAP-federated).
    """
    first_name, _, last_name = display_name.partition(" ")
    async with httpx.AsyncClient(timeout=10) as client:
        headers = {"Authorization": f"Bearer {await _admin_token(settings, client)}"}

        created = await client.post(
            settings.keycloak_admin_users_url,
            headers=headers,
            json={
                "username": login,
                "email": email,
                "firstName": first_name or login,
                "lastName": last_name or "-",
                "enabled": True,
                "emailVerified": True,
                "requiredActions": [],
                "credentials": [{"type": "password", "value": password, "temporary": False}],
            },
        )
        if created.status_code == httpx.codes.CONFLICT:
            raise KeycloakAdminError(f"Keycloak user {login!r} already exists", conflict=True)
        if created.status_code != httpx.codes.CREATED:
            raise KeycloakAdminError(f"Could not create Keycloak user: {created.text}")
        subject = created.headers["Location"].rsplit("/", 1)[-1]

        role_lookup = await client.get(
            f"{settings.keycloak_internal_url}/admin/realms/{settings.keycloak_realm}/roles/{role}",
            headers=headers,
        )
        if role_lookup.status_code != httpx.codes.OK:
            raise KeycloakAdminError(f"Unknown Keycloak realm role {role!r}: {role_lookup.text}")

        assigned = await client.post(
            f"{settings.keycloak_admin_users_url}/{subject}/role-mappings/realm",
            headers=headers,
            json=[role_lookup.json()],
        )
        if assigned.status_code != httpx.codes.NO_CONTENT:
            raise KeycloakAdminError(f"Could not assign role {role!r}: {assigned.text}")

        return subject
