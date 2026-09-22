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
