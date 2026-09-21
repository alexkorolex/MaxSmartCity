from dataclasses import dataclass, field
from uuid import UUID

from src.common.enums import ActorType


@dataclass(frozen=True, slots=True)
class Principal:
    """Authenticated caller, unified across the Keycloak (staff) and resident-bot auth paths."""

    actor_type: ActorType
    actor_id: UUID
    roles: frozenset[str] = field(default_factory=frozenset)
    organization_id: UUID | None = None
    department_id: UUID | None = None

    def has_role(self, *roles: str) -> bool:
        return not self.roles.isdisjoint(roles)
