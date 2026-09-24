from typing import Any
from uuid import UUID

from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy import Row, Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.models import utc_now
from src.domains.geo.models import Address, AdministrativeArea, AffectedObject, House, HouseManagement
from src.domains.geo.repositories import (
    AddressRepository,
    AdministrativeAreaRepository,
    AffectedObjectRepository,
    HouseManagementRepository,
    HouseRepository,
)
from src.domains.geo.schemas import (
    AssignHouseManagementCommand,
    HouseDataSource,
    HouseManagementSummary,
    HouseManagingOrganization,
    HousePlatformManager,
    TerminateHouseManagementCommand,
)
from src.domains.identity.enums import OrganizationRegistrationStatus, OrganizationType
from src.domains.identity.models import Organization
from src.domains.identity.validation import HOUSING_ORGANIZATION_TYPES
from src.domains.infrastructure.models import OutboxEvent
from src.domains.ingestion import models as ingestion
from src.domains.notifications.dispatcher import OrganizationMessage, enqueue_organization_notification


class AddressService(SQLAlchemyAsyncRepositoryService[Address]):
    repository_type = AddressRepository


class AdministrativeAreaService(SQLAlchemyAsyncRepositoryService[AdministrativeArea]):
    repository_type = AdministrativeAreaRepository


class HouseService(SQLAlchemyAsyncRepositoryService[House]):
    repository_type = HouseRepository


class AffectedObjectService(SQLAlchemyAsyncRepositoryService[AffectedObject]):
    repository_type = AffectedObjectRepository


class HouseManagementNotFoundError(RuntimeError):
    pass


class HouseManagementConflictError(RuntimeError):
    pass


async def active_house_manager_id(session: AsyncSession, house_id: UUID) -> UUID | None:
    """The organization currently managing ``house_id`` - who gets residents' requests."""
    return await session.scalar(
        select(HouseManagement.organization_id).where(
            HouseManagement.house_id == house_id,
            HouseManagement.is_active.is_(True),
        )
    )


def house_management_summary_statement() -> Select[Any]:
    return (
        select(
            HouseManagement.id,
            HouseManagement.house_id,
            Address.formatted.label("house_formatted"),
            HouseManagement.organization_id,
            Organization.name.label("organization_name"),
            Organization.type.label("organization_type"),
            Organization.inn.label("organization_inn"),
            HouseManagement.is_active,
            HouseManagement.basis,
            HouseManagement.assigned_via_reserve_registry,
            HouseManagement.effective_from,
            HouseManagement.effective_to,
        )
        .select_from(HouseManagement)
        .join(House, House.id == HouseManagement.house_id)
        .join(Address, Address.id == House.address_id)
        .join(Organization, Organization.id == HouseManagement.organization_id)
    )


def to_house_management_summary(row: Row[Any]) -> HouseManagementSummary:
    return HouseManagementSummary(
        id=row.id,
        house_id=row.house_id,
        house_formatted=row.house_formatted,
        organization_id=row.organization_id,
        organization_name=row.organization_name,
        organization_type=row.organization_type.value,
        organization_inn=row.organization_inn,
        is_active=row.is_active,
        basis=row.basis,
        assigned_via_reserve_registry=row.assigned_via_reserve_registry,
        effective_from=row.effective_from,
        effective_to=row.effective_to,
    )


class HouseManagementService(SQLAlchemyAsyncRepositoryService[HouseManagement]):
    repository_type = HouseManagementRepository

    async def assign(
        self, command: AssignHouseManagementCommand, *, changed_by: UUID, allow_replace: bool = True
    ) -> HouseManagement:
        """``allow_replace=False`` (an organization taking a house itself) only accepts a
        house nobody manages yet - moving a house away from another УК/ТСЖ is up to the
        admin or the district administration."""
        session = self.repository.session
        house = await session.scalar(select(House).where(House.id == command.house_id).with_for_update())
        if house is None:
            raise HouseManagementNotFoundError(f"House {command.house_id} was not found")
        organization = await session.get(Organization, command.organization_id)
        if organization is None:
            raise HouseManagementNotFoundError(f"Organization {command.organization_id} was not found")
        if organization.type not in HOUSING_ORGANIZATION_TYPES:
            raise HouseManagementConflictError("Only a management company or an HOA can manage a house")
        if (
            organization.registration_status is not OrganizationRegistrationStatus.APPROVED
            or not organization.enabled
        ):
            raise HouseManagementConflictError("The organization is not approved or is disabled")
        if organization.type is OrganizationType.MANAGEMENT_COMPANY and not organization.license_number:
            raise HouseManagementConflictError("A management company without a license cannot manage houses")
        if command.assigned_via_reserve_registry and not organization.in_reserve_registry:
            raise HouseManagementConflictError(
                "Only a management company included in the Перечень can be appointed from it"
            )
        basis = command.basis.strip()
        if not basis:
            raise HouseManagementConflictError("basis is required")
        effective_from = command.effective_from or utc_now().date()

        current = await session.scalar(
            select(HouseManagement)
            .where(HouseManagement.house_id == house.id, HouseManagement.is_active.is_(True))
            .with_for_update()
        )
        if current is not None:
            if current.organization_id == organization.id:
                raise HouseManagementConflictError("The organization already manages this house")
            if not allow_replace:
                raise HouseManagementConflictError(
                    "The house is managed by another organization; contact the district administration"
                )
            if current.effective_from is not None and effective_from < current.effective_from:
                raise HouseManagementConflictError(
                    "effective_from is earlier than the current manager's effective_from"
                )
            current.is_active = False
            current.effective_to = effective_from
            # Flush before inserting: the partial unique index allows one active row per house.
            await session.flush()

        management = HouseManagement(
            house_id=house.id,
            organization_id=organization.id,
            basis=basis,
            assigned_via_reserve_registry=command.assigned_via_reserve_registry,
            effective_from=effective_from,
        )
        session.add(management)
        await session.flush()
        address = await session.scalar(select(Address.formatted).where(Address.id == house.address_id))
        session.add(
            OutboxEvent(
                aggregate_type="HOUSE",
                aggregate_id=house.id,
                event_type="HOUSE_MANAGEMENT_ASSIGNED",
                payload={
                    "house_management_id": str(management.id),
                    "house_id": str(house.id),
                    "organization_id": str(organization.id),
                    "previous_organization_id": str(current.organization_id) if current else None,
                    "assigned_via_reserve_registry": command.assigned_via_reserve_registry,
                    "changed_by": str(changed_by),
                },
            )
        )
        enqueue_organization_notification(
            session,
            OrganizationMessage(
                organization_id=organization.id,
                event_type="HOUSE_MANAGEMENT_ASSIGNED",
                title="Вам передан дом в управление",
                body=f"{address} - с {effective_from:%d.%m.%Y}. Основание: {basis}",
                house_id=house.id,
            ),
        )
        await session.flush()
        return management

    async def terminate(
        self,
        item_id: UUID,
        command: TerminateHouseManagementCommand,
        *,
        changed_by: UUID,
        organization_id: UUID | None = None,
    ) -> HouseManagement:
        """``organization_id`` confines the call to that organization's own houses."""
        session = self.repository.session
        management = await session.scalar(
            select(HouseManagement).where(HouseManagement.id == item_id).with_for_update()
        )
        if management is None or (
            organization_id is not None and management.organization_id != organization_id
        ):
            raise HouseManagementNotFoundError(f"House management {item_id} was not found")
        if not management.is_active:
            raise HouseManagementConflictError("House management is already terminated")
        effective_to = command.effective_to or utc_now().date()
        if management.effective_from is not None and effective_to < management.effective_from:
            raise HouseManagementConflictError("effective_to is earlier than effective_from")
        management.is_active = False
        management.effective_to = effective_to
        session.add(
            OutboxEvent(
                aggregate_type="HOUSE",
                aggregate_id=management.house_id,
                event_type="HOUSE_MANAGEMENT_TERMINATED",
                payload={
                    "house_management_id": str(management.id),
                    "house_id": str(management.house_id),
                    "organization_id": str(management.organization_id),
                    "reason": command.reason,
                    "changed_by": str(changed_by),
                },
            )
        )
        await session.flush()
        return management


MANAGES_RELATIONSHIP = "MANAGES"


async def load_platform_manager(session: AsyncSession, house_id: UUID) -> HousePlatformManager | None:
    row = (
        await session.execute(
            select(
                Organization.id,
                Organization.name,
                Organization.type,
                Organization.inn,
                HouseManagement.effective_from,
            )
            .join(HouseManagement, HouseManagement.organization_id == Organization.id)
            .where(HouseManagement.house_id == house_id, HouseManagement.is_active.is_(True))
        )
    ).first()
    if row is None:
        return None
    return HousePlatformManager(
        organization_id=row.id,
        name=row.name,
        type=row.type.value,
        inn=row.inn,
        effective_from=row.effective_from,
    )


async def load_house_reference(session: AsyncSession, house_id: UUID) -> tuple[str | None, str | None]:
    """``(management_method, official_status)`` from the freshest ingested source."""
    rows = (
        await session.execute(
            select(ingestion.house_source.c.management_method, ingestion.house_source.c.official_status)
            .where(ingestion.house_source.c.house_id == house_id)
            .order_by(ingestion.house_source.c.retrieved_at.desc())
        )
    ).all()
    method = next((row.management_method for row in rows if row.management_method), None)
    status = next((row.official_status for row in rows if row.official_status), None)
    return method, status


async def load_managing_organizations(
    session: AsyncSession, house_id: UUID, *, platform_inn: str | None
) -> list[HouseManagingOrganization]:
    """Management companies of the house from open sources, one entry per organization
    with contacts merged across sources (freshest source first)."""
    today = utc_now().date()
    rows = (
        await session.execute(
            select(
                ingestion.organization.c.id.label("organization_id"),
                ingestion.organization.c.name,
                ingestion.organization.c.type,
                ingestion.organization_source.c.inn,
                ingestion.organization_source.c.ogrn,
                ingestion.organization_source.c.phones,
                ingestion.organization_source.c.email,
                ingestion.organization_source.c.website,
                ingestion.organization_source.c.provenance,
                ingestion.house_organization.c.basis,
                ingestion.house_organization.c.period_from,
                ingestion.house_organization.c.retrieved_at,
                ingestion.source.c.code.label("source_code"),
                ingestion.source.c.url.label("source_url"),
                ingestion.source.c.data_kind,
            )
            .select_from(ingestion.house_organization)
            .join(
                ingestion.organization,
                ingestion.organization.c.id == ingestion.house_organization.c.organization_id,
            )
            .join(ingestion.source, ingestion.source.c.id == ingestion.house_organization.c.source_id)
            .outerjoin(
                ingestion.organization_source,
                and_(
                    ingestion.organization_source.c.source_id == ingestion.house_organization.c.source_id,
                    ingestion.organization_source.c.organization_id
                    == ingestion.house_organization.c.organization_id,
                ),
            )
            .where(
                ingestion.house_organization.c.house_id == house_id,
                ingestion.house_organization.c.relationship == MANAGES_RELATIONSHIP,
                or_(
                    ingestion.house_organization.c.period_to.is_(None),
                    ingestion.house_organization.c.period_to >= today,
                ),
            )
            .order_by(ingestion.house_organization.c.retrieved_at.desc())
        )
    ).all()

    merged: dict[UUID, HouseManagingOrganization] = {}
    for row in rows:
        provenance = row.provenance if isinstance(row.provenance, dict) else {}
        contact_source = provenance.get("contact_source")
        source = HouseDataSource(
            code=row.source_code,
            url=contact_source if isinstance(contact_source, str) else row.source_url,
            data_kind=row.data_kind,
            retrieved_at=row.retrieved_at,
        )
        entry = merged.get(row.organization_id)
        if entry is None:
            entry = merged[row.organization_id] = HouseManagingOrganization(
                name=row.name,
                type=row.type,
                inn=None,
                ogrn=None,
                phones=[],
                email=None,
                website=None,
                basis=None,
                period_from=None,
                is_platform_manager=False,
                sources=[],
            )
        entry.inn = entry.inn or row.inn
        entry.ogrn = entry.ogrn or row.ogrn
        entry.email = entry.email or row.email
        entry.website = entry.website or row.website
        entry.basis = entry.basis or row.basis
        entry.period_from = entry.period_from or row.period_from
        for phone in row.phones or []:
            if phone not in entry.phones:
                entry.phones.append(phone)
        entry.sources.append(source)
    for entry in merged.values():
        entry.is_platform_manager = bool(platform_inn and entry.inn == platform_inn)
    return list(merged.values())
