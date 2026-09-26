"""Resident reports: filing and closing one's own, grouping decisions, and the staff listing."""

from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, get, post
from litestar.di import NamedDependency, Provide
from litestar.dto import DTOData
from litestar.exceptions import ClientException, NotFoundException
from litestar.params import FromPath, Parameter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.enums import ActorType
from src.common.state_machine import InvalidStateTransition
from src.database.logging import database_action
from src.domains.geo.models import Address, House
from src.domains.identity.admin_scope import RESIDENT_DATA_ROLES, resolve_organization_scope
from src.domains.incidents.enums import GroupingMode
from src.domains.incidents.models import IncidentGroupingDecision
from src.domains.incidents.schemas import (
    CloseReportCommand,
    CloseReportResult,
    GroupReportCommand,
    GroupReportResult,
)
from src.domains.incidents.scope import organization_report_ids
from src.domains.incidents.services import (
    IncidentCoreConflictError,
    IncidentCoreNotFoundError,
    IncidentCoreService,
)
from src.domains.ml.client import MLDecisionClient
from src.domains.ml.report_grouping import ReportGroupingRecommendationService
from src.domains.reports.enums import ReportSourceType
from src.domains.reports.models import ProblemCategory, Report
from src.domains.reports.schemas import (
    CreateReportCommand,
    CreateReportResult,
    ReportCreateDTO,
    ReportReadDTO,
)
from src.domains.reports.services import (
    ReportIntakeConflictError,
    ReportIntakeNotFoundError,
    ReportIntakeService,
    ReportService,
)
from src.domains.reports.storage import S3Settings
from src.security.dependency import provide_principal
from src.security.guards import require_resident, require_roles
from src.security.principal import Principal


def provide_report_service(db_session: NamedDependency[AsyncSession]) -> ReportService:
    return ReportService(session=db_session, auto_commit=True)


def provide_s3_settings() -> S3Settings:
    return S3Settings.from_environment()


def provide_ml_decision_client() -> MLDecisionClient:
    return MLDecisionClient.from_environment()


_STAFF_ADMIN_ROLES = RESIDENT_DATA_ROLES


async def authorize_report_access(db_session: AsyncSession, *, report: Report, principal: Principal) -> None:
    """Raise ``NotFoundException`` unless the caller may view this report: the resident
    who submitted it, an admin (unrestricted), or a district_admin/housing_worker whose
    organization works on it (see ``src.domains.incidents.scope``). 404, not 403 - a
    report's existence is never revealed to a caller who isn't allowed to see it."""
    if principal.actor_type is ActorType.RESIDENT:
        if report.resident_id == principal.actor_id:
            return
        raise NotFoundException(f"Report {report.id} was not found")

    if not principal.has_role(*_STAFF_ADMIN_ROLES):
        raise NotFoundException(f"Report {report.id} was not found")

    scope = resolve_organization_scope(principal)
    if scope.is_admin:
        return
    if scope.organization_id is not None:
        in_scope = await db_session.scalar(
            select(Report.id).where(
                Report.id == report.id, Report.id.in_(organization_report_ids(scope.organization_id))
            )
        )
        if in_scope is not None:
            return
    raise NotFoundException(f"Report {report.id} was not found")


class ReportController(Controller):
    """Residents file, list and close their reports; staff browse them within their organization's scope."""

    path = "/reports"
    tags = ("reports",)
    return_dto = ReportReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "service": Provide(provide_report_service, sync_to_thread=False),
            "principal": Provide(provide_principal),
            "s3_settings": Provide(provide_s3_settings, sync_to_thread=False),
            "ml_client": Provide(provide_ml_decision_client, sync_to_thread=False),
        }

    @post(
        "/intake",
        status_code=201,
        return_dto=None,
        name="reports:Report:intake",
        guards=[require_resident()],
    )
    async def intake(
        self,
        data: CreateReportCommand,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> CreateReportResult:
        try:
            async with db_session.begin():
                return await ReportIntakeService(db_session).create(data, resident_id=principal.actor_id)
        except ReportIntakeNotFoundError as exc:
            raise NotFoundException(str(exc)) from exc
        except ReportIntakeConflictError as exc:
            raise ClientException(status_code=409, detail=str(exc)) from exc

    @get(
        "/mine",
        name="reports:Report:mine",
        guards=[require_resident()],
    )
    async def list_mine(
        self,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Report]:
        return list(
            (
                await db_session.scalars(
                    select(Report)
                    .where(Report.resident_id == principal.actor_id)
                    .order_by(Report.received_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
        )

    @get(
        "/{item_id:uuid}/grouping",
        return_dto=None,
        name="reports:Report:grouping",
        guards=[require_resident()],
    )
    async def get_grouping(
        self,
        item_id: FromPath[UUID],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        ml_client: NamedDependency[MLDecisionClient],
    ) -> GroupReportResult:
        report = await db_session.scalar(
            select(Report).where(Report.id == item_id, Report.resident_id == principal.actor_id)
        )
        if report is None:
            raise NotFoundException(f"Report {item_id} was not found")
        decision = await db_session.scalar(
            select(IncidentGroupingDecision)
            .where(IncidentGroupingDecision.report_id == item_id)
            .order_by(IncidentGroupingDecision.created_at.desc(), IncidentGroupingDecision.id.desc())
            .limit(1)
        )
        if decision is None:
            raise NotFoundException(f"Grouping for report {item_id} was not found")
        recommendations = await ReportGroupingRecommendationService(db_session, ml_client).recommend(
            report, decision
        )
        return GroupReportResult(
            report_id=report.id,
            outcome=decision.outcome,
            incident_id=decision.selected_incident_id,
            score=float(decision.score) if decision.score is not None else None,
            candidate_incident_ids=[item.incident_id for item in recommendations.candidates],
            candidate_incidents=recommendations.candidates,
            reason_codes=decision.reason_codes,
            policy_version=decision.policy_version,
            scorer_version=recommendations.scorer_version or decision.scorer_version,
        )

    @post(
        "/{item_id:uuid}/grouping-decision",
        status_code=200,
        return_dto=None,
        name="reports:Report:grouping-decision",
        guards=[require_resident()],
    )
    async def grouping_decision(
        self,
        item_id: FromPath[UUID],
        data: GroupReportCommand,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> GroupReportResult:
        if data.mode is GroupingMode.AUTO:
            raise ClientException(
                status_code=409,
                detail="Choose CONFIRM_INCIDENT or FORCE_NEW for a resident decision",
            )
        try:
            async with db_session.begin():
                resident_id = await db_session.scalar(select(Report.resident_id).where(Report.id == item_id))
                if resident_id != principal.actor_id:
                    raise ReportIntakeNotFoundError(f"Report {item_id} was not found")
                return await IncidentCoreService(db_session).group_report(item_id, data)
        except (ReportIntakeNotFoundError, IncidentCoreNotFoundError) as exc:
            raise NotFoundException(str(exc)) from exc
        except (IncidentCoreConflictError, InvalidStateTransition) as exc:
            raise ClientException(status_code=409, detail=str(exc)) from exc

    @get(
        "/",
        name="reports:Report:list",
        guards=[require_roles(*_STAFF_ADMIN_ROLES)],
    )
    async def list_items(
        self,
        service: NamedDependency[ReportService],
        principal: NamedDependency[Principal],
        resident_id: Annotated[UUID | None, Parameter()] = None,
        city: Annotated[str | None, Parameter()] = None,
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Report]:
        scope = resolve_organization_scope(principal)
        if scope.sees_nothing:
            return []
        with database_action("list", "reports.Report"):
            criteria = []
            if resident_id is not None:
                criteria.append(Report.resident_id == resident_id)
            if city and scope.is_admin:
                house_ids = (
                    select(House.id).join(Address, Address.id == House.address_id).where(Address.city == city)
                )
                criteria.append(Report.house_id.in_(house_ids))
            if not scope.is_admin:
                assert scope.organization_id is not None
                criteria.append(Report.id.in_(organization_report_ids(scope.organization_id)))
            return await service.get_many(
                LimitOffset(limit=limit, offset=offset), *criteria, order_by=("received_at", True)
            )

    @post(
        "/{item_id:uuid}/close",
        status_code=200,
        return_dto=None,
        name="reports:Report:close",
        guards=[require_resident()],
    )
    async def close(
        self,
        item_id: FromPath[UUID],
        data: CloseReportCommand,
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> CloseReportResult:
        """The resident closes their own report because the problem went away (see
        ``IncidentCoreService.close_by_resident`` for what happens to the incident)."""
        try:
            with database_action("update", "reports.Report"):
                result = await IncidentCoreService(db_session).close_by_resident(
                    item_id, data, resident_id=principal.actor_id
                )
        except IncidentCoreNotFoundError as exc:
            raise NotFoundException(str(exc)) from exc
        except (IncidentCoreConflictError, InvalidStateTransition) as exc:
            raise ClientException(status_code=409, detail=str(exc)) from exc
        await db_session.commit()
        return result

    @get("/{item_id:uuid}", name="reports:Report:get")
    async def get_item(
        self,
        item_id: FromPath[UUID],
        service: NamedDependency[ReportService],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> Report:
        with database_action("get", "reports.Report"):
            report = await service.get(item_id)
        await authorize_report_access(db_session, report=report, principal=principal)
        return report

    @post(
        "/",
        dto=ReportCreateDTO,
        name="reports:Report:create",
        guards=[require_resident()],
    )
    async def create_item(
        self,
        data: DTOData[Report],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
    ) -> Report:
        """The resident app's "Сообщить о проблеме". Goes through the same intake as
        ``/reports/intake`` (``ReportIntakeService.accept_new``): grouped into an incident,
        so the house's УК/ТСЖ is notified and staff see it."""
        with database_action("create", "reports.Report"):
            report = data.create_instance()
            report.resident_id = principal.actor_id
            report.source_type = ReportSourceType.MAX
            if report.house_id is not None and await db_session.get(House, report.house_id) is None:
                raise NotFoundException(f"House {report.house_id} was not found")
            category_id = report.category_id
            if category_id is not None and await db_session.get(ProblemCategory, category_id) is None:
                raise NotFoundException(f"Category {category_id} was not found")
            db_session.add(report)
            await db_session.flush()
            try:
                await ReportIntakeService(db_session).accept_new(report, resident_id=principal.actor_id)
            except (IncidentCoreConflictError, InvalidStateTransition) as exc:
                raise ClientException(status_code=409, detail=str(exc)) from exc
            await db_session.commit()
            return report
