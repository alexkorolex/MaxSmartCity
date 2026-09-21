from uuid import UUID

import jwt
from litestar import Request
from litestar.di import NamedDependency
from litestar.exceptions import NotAuthorizedException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.enums import ActorType
from src.domains.identity.models import OperatorUser, OrganizationMember
from src.security.guards import extract_bearer_token, is_keycloak_token
from src.security.keycloak import decode_keycloak_token
from src.security.principal import Principal
from src.security.resident import decode_resident_token
from src.security.settings import SecuritySettings


async def _resolve_operator_principal(
    subject: str, roles: frozenset[str], preferred_username: str | None, db_session: AsyncSession
) -> Principal:
    """Map a verified Keycloak subject to (and, if needed, provision) a local OperatorUser.

    Keycloak (federated to LDAP) is the source of truth for *who* the caller is; the local
    ``OperatorUser``/``OrganizationMember`` rows are the source of truth for *which*
    organization/department they act in. A staff member's first successful login creates
    their local shadow record automatically.
    """
    operator = (
        await db_session.execute(select(OperatorUser).where(OperatorUser.keycloak_subject == subject))
    ).scalar_one_or_none()
    if operator is None:
        operator = OperatorUser(
            login=preferred_username or subject,
            display_name=preferred_username or subject,
            keycloak_subject=subject,
        )
        db_session.add(operator)
        await db_session.commit()

    membership = (
        await db_session.execute(
            select(OrganizationMember).where(
                OrganizationMember.user_id == operator.id,
                OrganizationMember.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()

    return Principal(
        actor_type=ActorType.OPERATOR,
        actor_id=operator.id,
        roles=roles,
        organization_id=membership.organization_id if membership else None,
        department_id=membership.department_id if membership else None,
    )


async def provide_principal(request: Request, db_session: NamedDependency[AsyncSession]) -> Principal:
    """Resolve the authenticated caller, regardless of whether they came through
    Keycloak (staff) or a bot-issued resident token."""
    settings = SecuritySettings.from_environment()
    token = extract_bearer_token(request)

    if is_keycloak_token(token, settings):
        try:
            claims = decode_keycloak_token(token, settings)
        except jwt.PyJWTError as exc:
            raise NotAuthorizedException("Invalid or expired token") from exc
        return await _resolve_operator_principal(
            claims.subject, claims.roles, claims.preferred_username, db_session
        )

    resident_token = decode_resident_token(token, settings)
    return Principal(actor_type=ActorType.RESIDENT, actor_id=UUID(resident_token.sub))
