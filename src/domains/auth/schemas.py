from dataclasses import dataclass


@dataclass
class ResidentAuthenticateRequest:
    """Sent by the resident bot - never by the resident directly, who has no login/password."""

    max_user_id: int
    username: str | None = None
    display_name: str | None = None


@dataclass
class ResidentAuthenticateResponse:
    resident_id: str
    max_user_id: int | None
    username: str | None
    display_name: str | None


@dataclass
class ResidentTokenRequest:
    max_user_id: int


@dataclass
class ResidentTokenResponse:
    token: str
    resident_id: str


@dataclass
class ResidentLoginRequest:
    """Sent by the resident's own browser - redeems the single-use code the bot gave them
    in chat. Not guarded by the bot shared secret: the code itself is the credential."""

    code: str


@dataclass
class ResidentWebAppLoginRequest:
    init_data: str


@dataclass
class StaffLoginRequest:
    """Staff still authenticate with a login/password - just proxied through our API so
    clients never talk to Keycloak directly. The password is forwarded, never stored."""

    username: str
    password: str


@dataclass
class StaffLoginResponse:
    token: str
    refresh_token: str | None
    expires_in: int | None
    """Seconds until ``token`` (the access token) expires - a few minutes."""
    refresh_expires_in: int | None = None
    """Seconds until ``refresh_token`` expires - the Keycloak session, 24 hours."""


@dataclass
class StaffInitialPasswordRequest:
    username: str
    password: str
    new_password: str


@dataclass
class StaffRefreshRequest:
    """Keeps a staff member signed in: the refresh token from ``/auth/staff/login`` (or
    the previous refresh) buys a new access token without re-entering the password."""

    refresh_token: str | None = None


@dataclass
class StaffLogoutRequest:
    refresh_token: str | None = None


@dataclass
class StaffRegisterRequest:
    """Creates a new staff account (admin/housing_worker/district_admin) - admin only.

    Organization/department membership is not set here; use the existing
    ``/identity/departments`` and ``OrganizationMember`` records for that afterwards.
    """

    login: str
    password: str
    display_name: str
    role: str
    email: str | None = None


@dataclass
class StaffRegisterResponse:
    operator_id: str
    login: str
    display_name: str
    role: str


@dataclass
class StaffLinkMaxIdRequest:
    """Links a staff member's own MAX-bot account, e.g. for notifications - optional,
    self-service, and separate from their Keycloak login."""

    max_user_id: int


@dataclass
class StaffLinkMaxIdResponse:
    operator_id: str
    max_user_id: int


@dataclass
class StaffProfileRead:
    """The signed-in staff member's own account, as shown on their profile page."""

    id: str
    login: str
    display_name: str
    email: str | None
    max_user_id: int | None
    organization_name: str | None
    department_name: str | None
    role_code: str | None


@dataclass
class StaffProfileUpdateRequest:
    display_name: str
    email: str | None = None


@dataclass
class StaffPasswordChangeRequest:
    """The current password is re-checked against Keycloak, so a borrowed open session
    alone can't be used to lock the owner out."""

    current_password: str
    new_password: str
