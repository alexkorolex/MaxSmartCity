import re
from collections.abc import Sequence
from typing import Annotated, Any
from uuid import UUID

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.dto import DTOData
from litestar.exceptions import ClientException, NotFoundException, PermissionDeniedException
from litestar.params import FromPath, Parameter
from sqlalchemy import Row, Select, case, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.geo.models import Address, House, HouseManagement
from src.domains.geo.schemas import (
    AddressCreateDTO,
    AddressReadDTO,
    AddressUpdateDTO,
    AssignHouseManagementCommand,
    HouseInfo,
    HouseManagementSummary,
    HouseSummary,
    TerminateHouseManagementCommand,
)
from src.domains.geo.services import (
    AddressService,
    HouseManagementConflictError,
    HouseManagementNotFoundError,
    HouseManagementService,
    house_management_summary_statement,
    load_house_reference,
    load_managing_organizations,
    load_platform_manager,
    to_house_management_summary,
)
from src.domains.identity.admin_scope import resolve_organization_scope
from src.domains.identity.models import Organization
from src.security.dependency import provide_principal
from src.security.guards import require_roles
from src.security.principal import Principal

_STAFF_ADMIN_ROLES = ("admin", "district_admin", "housing_worker")
_HOUSE_MANAGEMENT_AUTHORITY_ROLES = ("admin", "district_admin")
"""Who may assign any house to any organization (including moving it away from its
current manager): the platform admin, or the district administration (Управа) acting as
the local authority that appoints a УК from the Перечень. A ``housing_worker`` may only
take a not-yet-managed house for, and release a house from, their own organization."""


def provide_address_service(db_session: NamedDependency[AsyncSession]) -> AddressService:
    return AddressService(session=db_session, auto_commit=True)


class AddressController(Controller):
    path = "/geo/addresses"
    tags = ("geo",)
    return_dto = AddressReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"service": Provide(provide_address_service, sync_to_thread=False)}

    @get("/", name="geo:Address:list")
    async def list_items(
        self,
        service: NamedDependency[AddressService],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Address]:
        with database_action("list", "geo.Address"):
            return await service.get_many(LimitOffset(limit=limit, offset=offset), order_by=("id", False))

    @get("/cities", name="geo:Address:cities", return_dto=None, cache=True)
    async def list_cities(self, db_session: NamedDependency[AsyncSession]) -> Sequence[str]:
        """Every distinct city that has at least one address on record - the complete set
        a filter dropdown should offer, not just whatever happens to already be loaded on
        the page (e.g. the small, unrelated set of organization headquarters cities)."""
        with database_action("list", "geo.Address"):
            result = await db_session.execute(
                select(Address.city).where(Address.city.is_not(None)).distinct().order_by(Address.city)
            )
            return [row[0] for row in result.all()]

    @get("/{item_id:uuid}", name="geo:Address:get")
    async def get_item(self, item_id: FromPath[UUID], service: NamedDependency[AddressService]) -> Address:
        with database_action("get", "geo.Address"):
            return await service.get(item_id)

    @post("/", dto=AddressCreateDTO, name="geo:Address:create")
    async def create_item(self, data: DTOData[Address], service: NamedDependency[AddressService]) -> Address:
        with database_action("create", "geo.Address"):
            return await service.create(data)

    @patch("/{item_id:uuid}", dto=AddressUpdateDTO, name="geo:Address:update")
    async def update_item(
        self,
        item_id: FromPath[UUID],
        data: DTOData[Address],
        service: NamedDependency[AddressService],
    ) -> Address:
        with database_action("update", "geo.Address"):
            return await service.update(data, item_id=item_id)

    @delete("/{item_id:uuid}", return_dto=None, name="geo:Address:delete")
    async def delete_item(self, item_id: FromPath[UUID], service: NamedDependency[AddressService]) -> None:
        with database_action("delete", "geo.Address"):
            await service.delete(item_id)


def _search_words(q: str | None) -> list[str]:
    """Up to 6 words of an address query, LIKE-escaped."""
    words = re.findall(r"[\w-]+", q or "")[:6]
    return [word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") for word in words]


def _house_summary_statement() -> Select[Any]:
    """A house with its address and current manager (if any) flattened in."""
    return (
        select(
            House.id,
            Address.city,
            Address.street,
            Address.house_number,
            Address.formatted,
            HouseManagement.organization_id,
            Organization.name.label("organization_name"),
        )
        .join(Address, Address.id == House.address_id)
        .outerjoin(
            HouseManagement,
            (HouseManagement.house_id == House.id) & HouseManagement.is_active.is_(True),
        )
        .outerjoin(Organization, Organization.id == HouseManagement.organization_id)
    )


def _to_house_summary(row: Row[Any]) -> HouseSummary:
    return HouseSummary(
        house_id=row.id,
        city=row.city,
        street=row.street,
        house_number=row.house_number,
        formatted=row.formatted,
        managed_by_organization_id=row.organization_id,
        managed_by_organization_name=row.organization_name,
    )


class HouseController(Controller):
    """Read-only: what a resident (or the "Сообщить о проблеме" flow) picks a home from.
    Houses are seeded by the ingestion pipeline, not created through this API."""

    path = "/geo/houses"
    tags = ("geo",)
    return_dto = None

    @get("/", name="geo:House:list")
    async def list_items(
        self,
        db_session: NamedDependency[AsyncSession],
        city: Annotated[str | None, Parameter()] = None,
        q: Annotated[str | None, Parameter(max_length=200)] = None,
        limit: Annotated[int, Parameter(ge=1, le=200)] = 200,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[HouseSummary]:
        """``q`` searches word by word, case-insensitively: every word must occur in the
        formatted address, except numbers, which must start the house number - so
        "Мира 9" finds "ул. Мира, д. 9" and "9А", but not a house whose postcode has a 9."""
        with database_action("list", "geo.House"):
            words = _search_words(q)
            numbers = [word.lower() for word in words if word[0].isdigit()]
            # A typed house number first ("Мира 10" -> дом 10, then 10А, 10 корп. 1, ...).
            exact_number_first = (
                case((func.lower(Address.house_number).in_(numbers), 0), else_=1) if numbers else literal(1)
            )
            statement = (
                _house_summary_statement()
                .order_by(exact_number_first, Address.city, Address.street, Address.house_number)
                .limit(limit)
                .offset(offset)
            )
            if city:
                statement = statement.where(Address.city == city)
            for word in words:
                if word[0].isdigit():
                    # Numbers match the house number itself - never a postcode ("241028" holds "10").
                    statement = statement.where(Address.house_number.ilike(f"{word}%"))
                else:
                    statement = statement.where(Address.formatted.ilike(f"%{word}%"))
            rows = (await db_session.execute(statement)).all()
            return [_to_house_summary(row) for row in rows]

    @get("/{item_id:uuid}", name="geo:House:get")
    async def get_item(
        self, item_id: FromPath[UUID], db_session: NamedDependency[AsyncSession]
    ) -> HouseSummary:
        with database_action("get", "geo.House"):
            row = (await db_session.execute(_house_summary_statement().where(House.id == item_id))).first()
            if row is None:
                raise NotFoundException(f"House {item_id} was not found")
            return _to_house_summary(row)

    @get("/{item_id:uuid}/info", name="geo:House:info")
    async def get_info(self, item_id: FromPath[UUID], db_session: NamedDependency[AsyncSession]) -> HouseInfo:
        """Everything a resident wants to know about the house they picked: who manages
        it and how to reach them - from open sources (with provenance) and, when the
        УК/ТСЖ is connected to Smart City, that it receives requests directly."""
        with database_action("get", "geo.House"):
            row = (await db_session.execute(_house_summary_statement().where(House.id == item_id))).first()
            if row is None:
                raise NotFoundException(f"House {item_id} was not found")
            platform_manager = await load_platform_manager(db_session, item_id)
            management_method, official_status = await load_house_reference(db_session, item_id)
            managing_organizations = await load_managing_organizations(
                db_session,
                item_id,
                platform_inn=platform_manager.inn if platform_manager else None,
                platform_ogrn=platform_manager.ogrn if platform_manager else None,
            )
            return HouseInfo(
                house=_to_house_summary(row),
                management_method=management_method,
                official_status=official_status,
                platform_manager=platform_manager,
                managing_organizations=managing_organizations,
            )

    @get("/{item_id:uuid}/management", name="geo:House:management")
    async def get_management(
        self, item_id: FromPath[UUID], db_session: NamedDependency[AsyncSession]
    ) -> HouseManagementSummary:
        """Who currently manages the house (УК/ТСЖ) - lets a resident see where their
        requests go."""
        with database_action("get", "geo.HouseManagement"):
            row = (
                await db_session.execute(
                    house_management_summary_statement().where(
                        HouseManagement.house_id == item_id, HouseManagement.is_active.is_(True)
                    )
                )
            ).first()
            if row is None:
                raise NotFoundException(f"House {item_id} has no active manager")
            return to_house_management_summary(row)


def provide_house_management_service(
    db_session: NamedDependency[AsyncSession],
) -> HouseManagementService:
    return HouseManagementService(session=db_session)


class HouseManagementController(Controller):
    """Which УК/ТСЖ manages which house - the houses define what an organization works
    on (its residents, reports and incidents, see ``src.domains.incidents.scope``).
    ``admin``/``district_admin`` see and change every record; a ``housing_worker`` sees
    and manages only their own organization's houses."""

    path = "/geo/house-management"
    tags = ("geo",)
    return_dto = None

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "service": Provide(provide_house_management_service, sync_to_thread=False),
            "principal": Provide(provide_principal),
        }

    @get("/", name="geo:HouseManagement:list", guards=[require_roles(*_STAFF_ADMIN_ROLES)])
    async def list_items(
        self,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        house_id: Annotated[UUID | None, Parameter()] = None,
        organization_id: Annotated[UUID | None, Parameter()] = None,
        active_only: Annotated[bool, Parameter()] = True,
        limit: Annotated[int, Parameter(ge=1, le=200)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[HouseManagementSummary]:
        if not principal.has_role(*_HOUSE_MANAGEMENT_AUTHORITY_ROLES):
            scope = resolve_organization_scope(principal, organization_id)
            if scope.sees_nothing:
                return []
            organization_id = scope.organization_id
        with database_action("list", "geo.HouseManagement"):
            statement = house_management_summary_statement()
            if house_id is not None:
                statement = statement.where(HouseManagement.house_id == house_id)
            if organization_id is not None:
                statement = statement.where(HouseManagement.organization_id == organization_id)
            if active_only:
                statement = statement.where(HouseManagement.is_active.is_(True))
            statement = (
                statement.order_by(Address.formatted, HouseManagement.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            rows = (await db_session.execute(statement)).all()
            return [to_house_management_summary(row) for row in rows]

    @post(
        "/",
        status_code=201,
        name="geo:HouseManagement:assign",
        guards=[require_roles(*_STAFF_ADMIN_ROLES)],
    )
    async def assign(
        self,
        data: AssignHouseManagementCommand,
        service: NamedDependency[HouseManagementService],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> HouseManagementSummary:
        is_authority = principal.has_role(*_HOUSE_MANAGEMENT_AUTHORITY_ROLES)
        if not is_authority and resolve_organization_scope(principal, data.organization_id).sees_nothing:
            raise PermissionDeniedException("No active organization membership")
        with database_action("create", "geo.HouseManagement"):
            try:
                management = await service.assign(
                    data, changed_by=principal.actor_id, allow_replace=is_authority
                )
            except HouseManagementNotFoundError as exc:
                raise NotFoundException(str(exc)) from exc
            except HouseManagementConflictError as exc:
                raise ClientException(status_code=409, detail=str(exc)) from exc
            await db_session.commit()
            return await self._summary(db_session, management.id)

    @post(
        "/{item_id:uuid}/terminate",
        status_code=200,
        name="geo:HouseManagement:terminate",
        guards=[require_roles(*_STAFF_ADMIN_ROLES)],
    )
    async def terminate(
        self,
        item_id: FromPath[UUID],
        data: TerminateHouseManagementCommand,
        service: NamedDependency[HouseManagementService],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> HouseManagementSummary:
        own_organization: UUID | None = None
        if not principal.has_role(*_HOUSE_MANAGEMENT_AUTHORITY_ROLES):
            if principal.organization_id is None:
                raise PermissionDeniedException("No active organization membership")
            own_organization = principal.organization_id
        with database_action("update", "geo.HouseManagement"):
            try:
                await service.terminate(
                    item_id, data, changed_by=principal.actor_id, organization_id=own_organization
                )
            except HouseManagementNotFoundError as exc:
                raise NotFoundException(str(exc)) from exc
            except HouseManagementConflictError as exc:
                raise ClientException(status_code=409, detail=str(exc)) from exc
            await db_session.commit()
            return await self._summary(db_session, item_id)

    @staticmethod
    async def _summary(db_session: AsyncSession, item_id: UUID) -> HouseManagementSummary:
        statement = house_management_summary_statement().where(HouseManagement.id == item_id)
        row = (await db_session.execute(statement)).first()
        if row is None:
            raise NotFoundException(f"House management {item_id} was not found")
        return to_house_management_summary(row)
