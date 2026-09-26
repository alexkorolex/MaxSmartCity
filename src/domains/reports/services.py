import hashlib
from uuid import UUID

from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.enums import ActorType, Priority
from src.domains.geo.models import House
from src.domains.incidents.schemas import GroupReportCommand, GroupReportResult
from src.domains.incidents.services import IncidentCoreService
from src.domains.infrastructure.models import OutboxEvent
from src.domains.reports.enums import ReportSourceType, ReportStatus
from src.domains.reports.models import ProblemCategory, Report, ReportStatusHistory
from src.domains.reports.repositories import ProblemCategoryRepository, ReportRepository
from src.domains.reports.schemas import CreateReportCommand, CreateReportResult


class ReportIntakeError(RuntimeError):
    pass


class ReportIntakeNotFoundError(ReportIntakeError):
    pass


class ReportIntakeConflictError(ReportIntakeError):
    pass


class ProblemCategoryService(SQLAlchemyAsyncRepositoryService[ProblemCategory]):
    repository_type = ProblemCategoryRepository


class ReportService(SQLAlchemyAsyncRepositoryService[Report]):
    repository_type = ReportRepository


class ReportIntakeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, command: CreateReportCommand, *, resident_id: UUID) -> CreateReportResult:
        external_id = command.source_external_id.strip()
        body = command.text.strip()
        category_code = command.category_code.strip()
        if not external_id or len(external_id) > 255:
            raise ReportIntakeConflictError("source_external_id must contain 1-255 characters")
        if not body or len(body) > 10_000:
            raise ReportIntakeConflictError("text must contain 1-10000 characters")
        if not category_code or len(category_code) > 64:
            raise ReportIntakeConflictError("category_code must contain 1-64 characters")
        if command.occurred_at is not None and command.occurred_at.tzinfo is None:
            raise ReportIntakeConflictError("occurred_at must include a timezone")

        digest = hashlib.blake2b(external_id.encode(), digest_size=8).digest()
        lock_key = int.from_bytes(digest, byteorder="big", signed=True)
        await self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
        existing = await self.session.scalar(
            select(Report)
            .where(
                Report.source_type == ReportSourceType.MAX,
                Report.source_external_id == external_id,
            )
            .with_for_update()
        )
        if existing is not None:
            if existing.resident_id != resident_id:
                raise ReportIntakeConflictError("source_external_id belongs to another resident")
            existing_category = await self.session.scalar(
                select(ProblemCategory).where(ProblemCategory.id == existing.category_id)
            )
            effective_urgency = (
                Priority.CRITICAL
                if existing_category is not None and existing_category.is_critical
                else command.urgency or Priority.NORMAL
            )
            if (
                existing.house_id != command.house_id
                or existing_category is None
                or existing_category.code != category_code
                or existing.text != body
                or existing.urgency != effective_urgency
                or existing.problem_continues != command.problem_continues
                or existing.occurred_at != command.occurred_at
            ):
                raise ReportIntakeConflictError(
                    "source_external_id was already used with a different payload"
                )
            grouping = await IncidentCoreService(self.session).group_report(
                existing.id, GroupReportCommand(request_id=command.request_id)
            )
            return CreateReportResult(report_id=existing.id, grouping=grouping)

        category = await self.session.scalar(
            select(ProblemCategory).where(
                ProblemCategory.code == category_code,
                ProblemCategory.enabled.is_(True),
            )
        )
        if category is None:
            raise ReportIntakeNotFoundError(f"Category {category_code!r} was not found")
        if await self.session.get(House, command.house_id) is None:
            raise ReportIntakeNotFoundError(f"House {command.house_id} was not found")

        report = Report(
            resident_id=resident_id,
            source_type=ReportSourceType.MAX,
            source_external_id=external_id,
            text=body,
            category_id=category.id,
            house_id=command.house_id,
            urgency=Priority.CRITICAL if category.is_critical else command.urgency or Priority.NORMAL,
            problem_continues=command.problem_continues,
            occurred_at=command.occurred_at,
        )
        self.session.add(report)
        await self.session.flush()
        grouping = await self.accept_new(report, resident_id=resident_id, request_id=command.request_id)
        return CreateReportResult(report_id=report.id, grouping=grouping)

    async def accept_new(
        self, report: Report, *, resident_id: UUID, request_id: UUID | None = None
    ) -> GroupReportResult:
        """Everything a freshly saved resident report goes through, whichever endpoint
        created it: the ``RECEIVED`` history entry, the ``REPORT_RECEIVED`` event, and
        grouping into an incident - which is what routes it to the house's УК/ТСЖ (their
        notification) and into the staff's incident list."""
        category_code = await self.session.scalar(
            select(ProblemCategory.code).where(ProblemCategory.id == report.category_id)
        )
        self.session.add_all(
            [
                ReportStatusHistory(
                    report_id=report.id,
                    from_status=None,
                    to_status=ReportStatus.RECEIVED,
                    changed_by_type=ActorType.RESIDENT,
                    changed_by_id=resident_id,
                    reason="Resident report received",
                ),
                OutboxEvent(
                    aggregate_type="REPORT",
                    aggregate_id=report.id,
                    event_type="REPORT_RECEIVED",
                    payload={
                        "report_id": str(report.id),
                        "resident_id": str(resident_id),
                        "house_id": str(report.house_id) if report.house_id else None,
                        "category_code": category_code,
                    },
                ),
            ]
        )
        return await IncidentCoreService(self.session).group_report(
            report.id, GroupReportCommand(request_id=request_id)
        )
