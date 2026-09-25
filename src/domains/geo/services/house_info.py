"""Reference data about a house for residents and admins: its management company from open
sources (ingestion) with contacts - the same company from several sources merged into one
entry - and the organization managing it on the platform."""

import re
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.models import utc_now
from src.domains.geo.models import HouseManagement
from src.domains.geo.schemas import (
    HouseDataSource,
    HouseManagingOrganization,
    HousePlatformManager,
)
from src.domains.identity.models import Organization
from src.domains.ingestion import models as ingestion

MANAGES_RELATIONSHIP = "MANAGES"


_LEGAL_FORMS = (
    ("ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ", "ООО"),
    ("ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО", "ПАО"),
    ("АКЦИОНЕРНОЕ ОБЩЕСТВО", "АО"),
    ("ТОВАРИЩЕСТВО СОБСТВЕННИКОВ ЖИЛЬЯ", "ТСЖ"),
    ("ТОВАРИЩЕСТВО СОБСТВЕННИКОВ НЕДВИЖИМОСТИ", "ТСН"),
    ("ЖИЛИЩНО-СТРОИТЕЛЬНЫЙ КООПЕРАТИВ", "ЖСК"),
    ("ЖИЛИЩНЫЙ КООПЕРАТИВ", "ЖК"),
    ("МУНИЦИПАЛЬНОЕ УНИТАРНОЕ ПРЕДПРИЯТИЕ", "МУП"),
    ("УПРАВЛЯЮЩАЯ КОМПАНИЯ", "УК"),
    ("ИНДИВИДУАЛЬНЫЙ ПРЕДПРИНИМАТЕЛЬ", "ИП"),
)


_NAME_NOISE = frozenset({short for _full, short in _LEGAL_FORMS} | {"ЗАО", "ОАО"})


def organization_name_key(name: str) -> str:
    """Comparable core of an organization name: legal form, "УК" and punctuation dropped,
    so «ООО ДОМ-ПЛЮС» and «ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "ДОМ-ПЛЮС"» match."""
    upper = name.upper().replace("Ё", "Е")
    for full, short in _LEGAL_FORMS:
        upper = upper.replace(full, short)
    words = re.findall(r"[А-ЯA-Z0-9]+", upper)
    core = [word for word in words if word not in _NAME_NOISE]
    return " ".join(core or words)


def _same_organization(
    entry: HouseManagingOrganization,
    entry_name_keys: set[str],
    ogrn: str | None,
    inn: str | None,
    name_key: str,
) -> bool:
    """Requisites decide when both sides have them (never merge two different OGRNs just
    because the names look alike); only without them does the name decide."""
    if ogrn and entry.ogrn:
        return ogrn == entry.ogrn
    if inn and entry.inn:
        return inn == entry.inn
    return bool(name_key) and name_key in entry_name_keys


async def load_platform_manager(session: AsyncSession, house_id: UUID) -> HousePlatformManager | None:
    row = (
        await session.execute(
            select(
                Organization.id,
                Organization.name,
                Organization.type,
                Organization.inn,
                Organization.ogrn,
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
        ogrn=row.ogrn,
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
    session: AsyncSession,
    house_id: UUID,
    *,
    platform_inn: str | None = None,
    platform_ogrn: str | None = None,
) -> list[HouseManagingOrganization]:
    """Management companies of the house from open sources, one entry per organization:
    the same company published by several sources (cian with contacts, GIS ЖКХ with the
    OGRN, ...) is merged, see ``_same_organization``."""
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

    # Rows are freshest first, so the first spelling of a name (usually the short, human
    # one from a contacts source) wins over e.g. the full legal name from GIS ЖКХ.
    merged: list[HouseManagingOrganization] = []
    name_keys: list[set[str]] = []
    for row in rows:
        provenance = row.provenance if isinstance(row.provenance, dict) else {}
        contact_source = provenance.get("contact_source")
        source = HouseDataSource(
            code=row.source_code,
            url=contact_source if isinstance(contact_source, str) else row.source_url,
            data_kind=row.data_kind,
            retrieved_at=row.retrieved_at,
        )
        name_key = organization_name_key(row.name)
        index = next(
            (
                position
                for position, entry in enumerate(merged)
                if _same_organization(entry, name_keys[position], row.ogrn, row.inn, name_key)
            ),
            None,
        )
        if index is None:
            merged.append(
                HouseManagingOrganization(
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
            )
            name_keys.append(set())
            index = len(merged) - 1
        entry = merged[index]
        name_keys[index].add(name_key)
        entry.inn = entry.inn or row.inn
        entry.ogrn = entry.ogrn or row.ogrn
        entry.email = entry.email or row.email
        entry.website = entry.website or row.website
        entry.basis = entry.basis or row.basis
        entry.period_from = entry.period_from or row.period_from
        for phone in row.phones or []:
            if phone not in entry.phones:
                entry.phones.append(phone)
        if source not in entry.sources:
            entry.sources.append(source)
    for entry in merged:
        entry.is_platform_manager = bool(
            (platform_inn and entry.inn == platform_inn) or (platform_ogrn and entry.ogrn == platform_ogrn)
        )
    return merged
