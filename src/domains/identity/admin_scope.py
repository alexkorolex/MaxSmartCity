"""Shared organization-scoping rules for the admin-panel endpoints (identity, reports,
incidents, collaboration): a platform ``admin`` sees everything, while a
``district_admin``/``housing_worker`` is confined to their own ``organization_id`` - and a
staff member with no active organization membership sees nothing, rather than erroring."""

from dataclasses import dataclass
from uuid import UUID

from litestar.exceptions import PermissionDeniedException

from src.security.principal import Principal

ADMIN_ROLE = "admin"
STAFF_ROLES = ("admin", "district_admin", "housing_worker")
"""Every staff role - who may use the admin panel at all (then scoped by organization)."""


def is_platform_admin(principal: Principal) -> bool:
    """A platform ``admin`` is not confined to any single organization."""
    return ADMIN_ROLE in principal.roles


@dataclass(frozen=True, slots=True)
class OrganizationScope:
    """Resolved organization-level visibility for one request.

    - ``is_admin=True``: unrestricted, unless ``organization_id`` narrows it (an admin
      explicitly filtering the listing down to one org).
    - ``is_admin=False``: always confined to ``organization_id`` - which is ``None`` only
      when the caller has no active membership, meaning they must see *nothing* (check
      ``sees_nothing`` and short-circuit before querying, rather than filtering on a NULL
      ``organization_id`` which could accidentally match other unrelated rows).
    """

    is_admin: bool
    organization_id: UUID | None

    @property
    def sees_nothing(self) -> bool:
        return not self.is_admin and self.organization_id is None


def resolve_organization_scope(
    principal: Principal, requested_organization_id: UUID | None = None
) -> OrganizationScope:
    """Combine the caller's role/org with an optional ``organization_id`` query filter.

    Admin: any requested org is honored as a filter (or none, to see everyone). Non-admin:
    the caller's own ``organization_id`` always applies; if they explicitly request a
    *different* org, that's a 403 (probing another organization's data by id), never a
    silent downgrade to their own org.
    """
    if is_platform_admin(principal):
        return OrganizationScope(is_admin=True, organization_id=requested_organization_id)
    if requested_organization_id is not None and requested_organization_id != principal.organization_id:
        raise PermissionDeniedException("Cannot access another organization's data")
    return OrganizationScope(is_admin=False, organization_id=principal.organization_id)
