import httpx

from src.security.settings import SecuritySettings


class KeycloakAdminError(RuntimeError):
    """Raised when a Keycloak Admin REST API call fails."""

    def __init__(self, message: str, *, conflict: bool = False, invalid: bool = False) -> None:
        super().__init__(message)
        self.conflict = conflict
        self.invalid = invalid


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
                "requiredActions": ["UPDATE_PASSWORD"],
                "credentials": [{"type": "password", "value": password, "temporary": True}],
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


async def update_staff_user(
    settings: SecuritySettings, *, subject: str, display_name: str, email: str | None
) -> None:
    """Keep the Keycloak account's name/e-mail in step with the local ``OperatorUser``
    after the staff member edits their own profile."""
    first_name, _, last_name = display_name.partition(" ")
    async with httpx.AsyncClient(timeout=10) as client:
        headers = {"Authorization": f"Bearer {await _admin_token(settings, client)}"}
        updated = await client.put(
            f"{settings.keycloak_admin_users_url}/{subject}",
            headers=headers,
            json={"email": email or "", "firstName": first_name, "lastName": last_name or "-"},
        )
        if updated.status_code == httpx.codes.CONFLICT:
            raise KeycloakAdminError("This e-mail is already used by another account", conflict=True)
        if updated.status_code != httpx.codes.NO_CONTENT:
            raise KeycloakAdminError(f"Could not update Keycloak user: {updated.text}")


async def set_staff_password(settings: SecuritySettings, *, subject: str, password: str) -> None:
    """Replace the staff member's Keycloak password (permanent, not a temporary one)."""
    async with httpx.AsyncClient(timeout=10) as client:
        headers = {"Authorization": f"Bearer {await _admin_token(settings, client)}"}
        reset = await client.put(
            f"{settings.keycloak_admin_users_url}/{subject}/reset-password",
            headers=headers,
            json={"type": "password", "value": password, "temporary": False},
        )
        if reset.status_code == httpx.codes.BAD_REQUEST:
            detail = reset.json().get("error_description") or "Password rejected by the password policy"
            raise KeycloakAdminError(detail, invalid=True)
        if reset.status_code != httpx.codes.NO_CONTENT:
            raise KeycloakAdminError(f"Could not set Keycloak password: {reset.text}")


async def complete_initial_password(settings: SecuritySettings, *, username: str, password: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        headers = {"Authorization": f"Bearer {await _admin_token(settings, client)}"}
        found = await client.get(
            settings.keycloak_admin_users_url,
            headers=headers,
            params={"username": username, "exact": "true"},
        )
        if found.status_code != httpx.codes.OK or not found.json():
            raise KeycloakAdminError("Staff account was not found")
        subject = found.json()[0]["id"]
        reset = await client.put(
            f"{settings.keycloak_admin_users_url}/{subject}/reset-password",
            headers=headers,
            json={"type": "password", "value": password, "temporary": False},
        )
        if reset.status_code == httpx.codes.BAD_REQUEST:
            detail = reset.json().get("error_description") or "Password rejected by the password policy"
            raise KeycloakAdminError(detail, invalid=True)
        if reset.status_code != httpx.codes.NO_CONTENT:
            raise KeycloakAdminError(f"Could not set Keycloak password: {reset.text}")
        cleared = await client.put(
            f"{settings.keycloak_admin_users_url}/{subject}", headers=headers, json={"requiredActions": []}
        )
        if cleared.status_code != httpx.codes.NO_CONTENT:
            raise KeycloakAdminError(f"Could not finish the password change: {cleared.text}")


async def realm_role_has_users(settings: SecuritySettings, role: str) -> bool:
    async with httpx.AsyncClient(timeout=10) as client:
        headers = {"Authorization": f"Bearer {await _admin_token(settings, client)}"}
        response = await client.get(
            f"{settings.keycloak_internal_url}/admin/realms/{settings.keycloak_realm}/roles/{role}/users",
            headers=headers,
            params={"first": 0, "max": 1},
        )
        if response.status_code != httpx.codes.OK:
            raise KeycloakAdminError(f"Could not list users of role {role!r}: {response.text}")
        return bool(response.json())
