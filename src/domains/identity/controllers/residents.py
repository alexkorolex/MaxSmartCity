"""The caller's own identity and profile, and the admin-panel resident directory."""

from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from litestar import Controller, Router, get, patch
from litestar.di import NamedDependency, Provide
from litestar.exceptions import NotFoundException
from litestar.params import FromPath, Parameter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.geo.models import Address, House
from src.domains.identity.admin_scope import STAFF_ROLES, resolve_organization_scope
from src.domains.identity.models import (
    Resident,
)
from src.domains.identity.schemas import (
    PrincipalRead,
    ResidentReadDTO,
    ResidentSelfUpdateRequest,
    ResidentSummary,
)
from src.domains.identity.services import (
    ResidentService,
)
from src.domains.incidents.scope import organization_resident_ids
from src.domains.reports.models import Report
from src.security.dependency import provide_principal
from src.security.guards import require_resident, require_roles
from src.security.principal import Principal


def provide_resident_service(db_session: NamedDependency[AsyncSession]) -> ResidentService:
    return ResidentService(session=db_session, auto_commit=True)


class MeController(Controller):
    """Whoever holds a valid token - staff via Keycloak or a resident via the bot - can
    ask who they are."""

    path = "/identity/me"
    tags = ("identity",)

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "principal": Provide(provide_principal),
            "resident_service": Provide(provide_resident_service, sync_to_thread=False),
        }

    @get("/", name="identity:me")
    async def get_me(self, principal: NamedDependency[Principal]) -> PrincipalRead:
        return PrincipalRead(
            actor_type=principal.actor_type.value,
            actor_id=str(principal.actor_id),
            roles=sorted(principal.roles),
            organization_id=str(principal.organization_id) if principal.organization_id else None,
            department_id=str(principal.department_id) if principal.department_id else None,
        )

    @get(
        "/resident",
        name="identity:me:resident:get",
        guards=[require_resident()],
        return_dto=ResidentReadDTO,
    )
    async def get_my_resident_profile(
        self,
        resident_service: NamedDependency[ResidentService],
        principal: NamedDependency[Principal],
    ) -> Resident:
        with database_action("get", "identity.Resident"):
            return await resident_service.get(principal.actor_id)

    @patch(
        "/resident",
        name="identity:me:resident:update",
        guards=[require_resident()],
        return_dto=ResidentReadDTO,
    )
    async def update_my_resident_profile(
        self,
        data: ResidentSelfUpdateRequest,
        resident_service: NamedDependency[ResidentService],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> Resident:
        with database_action("update", "identity.Resident"):
            updates: dict[str, object] = {}
            if data.notifications_enabled is not None:
                updates["notifications_enabled"] = data.notifications_enabled
            if data.display_name is not None:
                updates["display_name"] = data.display_name
            if data.house_id is not None:
                exists = await db_session.scalar(select(House.id).where(House.id == data.house_id))
                if exists is None:
                    raise NotFoundException(f"House {data.house_id} was not found")
                updates["house_id"] = data.house_id
            if not updates:
                return await resident_service.get(principal.actor_id)
            return await resident_service.update(updates, item_id=principal.actor_id)


class ResidentController(Controller):
    """Admin-panel resident directory. ``admin`` browses every resident; a
    ``district_admin``/``housing_worker`` only sees residents of their organization's
    houses and those whose reports it works on (``src.domains.incidents.scope``) - never
    another organization's residents."""

    path = "/identity/residents"
    tags = ("identity",)
    return_dto = None

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"principal": Provide(provide_principal)}

    @get("/", name="identity:Resident:list", guards=[require_roles(*STAFF_ROLES)])
    async def list_items(
        self,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        city: Annotated[str | None, Parameter()] = None,
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[ResidentSummary]:
        scope = resolve_organization_scope(principal)
        if scope.sees_nothing:
            return []
        with database_action("list", "identity.Resident"):
            reports_count = (
                select(func.count(Report.id))
                .where(Report.resident_id == Resident.id)
                .correlate(Resident)
                .scalar_subquery()
            )
            statement = (
                select(
                    Resident.id,
                    Resident.display_name,
                    Resident.username,
                    Resident.max_user_id,
                    Resident.house_id,
                    Address.city.label("house_city"),
                    Address.formatted.label("house_formatted"),
                    reports_count.label("reports_count"),
                    Resident.created_at,
                )
                .select_from(Resident)
                .outerjoin(House, House.id == Resident.house_id)
                .outerjoin(Address, Address.id == House.address_id)
            )
            if city:
                statement = statement.where(Address.city == city)
            if not scope.is_admin:
                assert scope.organization_id is not None
                statement = statement.where(Resident.id.in_(organization_resident_ids(scope.organization_id)))
            statement = statement.order_by(Resident.created_at.desc()).limit(limit).offset(offset)
            rows = (await db_session.execute(statement)).all()
            return [
                ResidentSummary(
                    id=row.id,
                    display_name=row.display_name,
                    username=row.username,
                    max_user_id=row.max_user_id,
                    house_id=row.house_id,
                    house_city=row.house_city,
                    house_formatted=row.house_formatted,
                    reports_count=row.reports_count,
                    created_at=row.created_at,
                )
                for row in rows
            ]

    @get(
        "/{item_id:uuid}",
        name="identity:Resident:get",
        guards=[require_roles(*STAFF_ROLES)],
    )
    async def get_item(
        self,
        item_id: FromPath[UUID],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> ResidentSummary:
        scope = resolve_organization_scope(principal)
        if scope.sees_nothing:
            raise NotFoundException(f"Resident {item_id} was not found")
        with database_action("get", "identity.Resident"):
            reports_count = (
                select(func.count(Report.id))
                .where(Report.resident_id == Resident.id)
                .correlate(Resident)
                .scalar_subquery()
            )
            statement = (
                select(
                    Resident.id,
                    Resident.display_name,
                    Resident.username,
                    Resident.max_user_id,
                    Resident.house_id,
                    Address.city.label("house_city"),
                    Address.formatted.label("house_formatted"),
                    reports_count.label("reports_count"),
                    Resident.created_at,
                )
                .select_from(Resident)
                .outerjoin(House, House.id == Resident.house_id)
                .outerjoin(Address, Address.id == House.address_id)
                .where(Resident.id == item_id)
            )
            if not scope.is_admin:
                assert scope.organization_id is not None
                statement = statement.where(Resident.id.in_(organization_resident_ids(scope.organization_id)))
            row = (await db_session.execute(statement)).first()
            if row is None:
                raise NotFoundException(f"Resident {item_id} was not found")
            return ResidentSummary(
                id=row.id,
                display_name=row.display_name,
                username=row.username,
                max_user_id=row.max_user_id,
                house_id=row.house_id,
                house_city=row.house_city,
                house_formatted=row.house_formatted,
                reports_count=row.reports_count,
                created_at=row.created_at,
            )
