from uuid import UUID

from litestar import Controller, Router, get
from litestar.di import NamedDependency, Provide
from litestar.exceptions import NotFoundException, PermissionDeniedException
from litestar.params import FromPath
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.analytics.schemas import TerritorySummary
from src.domains.analytics.services import AnalyticsService
from src.domains.geo.services.territories import (
    TerritoryForbiddenError,
    TerritoryNotFoundError,
    ensure_territory_visible,
    visible_territory_root,
)
from src.domains.identity.admin_scope import is_platform_admin
from src.security.dependency import provide_principal
from src.security.guards import require_roles
from src.security.principal import Principal


class AnalyticsController(Controller):
    path = "/analytics"
    tags = ("analytics",)
    return_dto = None

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"principal": Provide(provide_principal)}

    @get(
        "/territories/{territory_id:uuid}/summary",
        name="analytics:territory-summary",
        guards=[require_roles("admin", "district_admin")],
    )
    async def territory_summary(
        self,
        territory_id: FromPath[UUID],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> TerritorySummary:
        try:
            with database_action("get", "analytics.TerritorySummary"):
                root = await visible_territory_root(
                    db_session,
                    is_admin=is_platform_admin(principal),
                    organization_id=principal.organization_id,
                )
                await ensure_territory_visible(db_session, root, territory_id)
                return await AnalyticsService(db_session).territory_summary(territory_id, visible_root=root)
        except TerritoryNotFoundError as exc:
            raise NotFoundException(str(exc)) from exc
        except TerritoryForbiddenError as exc:
            raise PermissionDeniedException(str(exc)) from exc
