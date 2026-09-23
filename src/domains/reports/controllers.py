import hashlib
from collections.abc import Sequence
from typing import Annotated
from uuid import UUID, uuid4

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, delete, get, patch, post
from litestar.datastructures import UploadFile
from litestar.di import NamedDependency, Provide
from litestar.dto import DTOData
from litestar.enums import RequestEncodingType
from litestar.exceptions import HTTPException, PermissionDeniedException
from litestar.params import Body, FromPath, Parameter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.collaboration.models import Assignment
from src.domains.geo.models import Address, House
from src.domains.identity.admin_scope import resolve_organization_scope
from src.domains.incidents.models import Incident, IncidentReportLink
from src.domains.reports.enums import AttachmentType, ReportSourceType
from src.domains.reports.models import ProblemCategory, Report, ReportAttachment
from src.domains.reports.schemas import (
    ProblemCategoryCreateDTO,
    ProblemCategoryReadDTO,
    ProblemCategoryUpdateDTO,
    ReportAttachmentRead,
    ReportCreateDTO,
    ReportReadDTO,
)
from src.domains.reports.services import ProblemCategoryService, ReportService
from src.domains.reports.storage import S3Settings
from src.security.dependency import provide_principal
from src.security.guards import require_resident, require_roles
from src.security.principal import Principal

ALLOWED_ATTACHMENT_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024


def provide_problemcategory_service(
    db_session: NamedDependency[AsyncSession],
) -> ProblemCategoryService:
    return ProblemCategoryService(session=db_session, auto_commit=True)


class ProblemCategoryController(Controller):
    path = "/reports/categories"
    tags = ("reports",)
    return_dto = ProblemCategoryReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {"service": Provide(provide_problemcategory_service, sync_to_thread=False)}

    @get("/", name="reports:ProblemCategory:list", cache=True)
    async def list_items(
        self,
        service: NamedDependency[ProblemCategoryService],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[ProblemCategory]:
        with database_action("list", "reports.ProblemCategory"):
            return await service.get_many(LimitOffset(limit=limit, offset=offset), order_by=("id", False))

    @get("/{item_id:uuid}", name="reports:ProblemCategory:get")
    async def get_item(
        self, item_id: FromPath[UUID], service: NamedDependency[ProblemCategoryService]
    ) -> ProblemCategory:
        with database_action("get", "reports.ProblemCategory"):
            return await service.get(item_id)

    @post("/", dto=ProblemCategoryCreateDTO, name="reports:ProblemCategory:create")
    async def create_item(
        self, data: DTOData[ProblemCategory], service: NamedDependency[ProblemCategoryService]
    ) -> ProblemCategory:
        with database_action("create", "reports.ProblemCategory"):
            return await service.create(data)

    @patch("/{item_id:uuid}", dto=ProblemCategoryUpdateDTO, name="reports:ProblemCategory:update")
    async def update_item(
        self,
        item_id: FromPath[UUID],
        data: DTOData[ProblemCategory],
        service: NamedDependency[ProblemCategoryService],
    ) -> ProblemCategory:
        with database_action("update", "reports.ProblemCategory"):
            return await service.update(data, item_id=item_id)

    @delete("/{item_id:uuid}", return_dto=None, name="reports:ProblemCategory:delete")
    async def delete_item(
        self, item_id: FromPath[UUID], service: NamedDependency[ProblemCategoryService]
    ) -> None:
        with database_action("delete", "reports.ProblemCategory"):
            await service.delete(item_id)


def provide_report_service(db_session: NamedDependency[AsyncSession]) -> ReportService:
    return ReportService(session=db_session, auto_commit=True)


def provide_s3_settings() -> S3Settings:
    return S3Settings.from_environment()


class ReportController(Controller):
    path = "/reports"
    tags = ("reports",)
    return_dto = ReportReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "service": Provide(provide_report_service, sync_to_thread=False),
            "principal": Provide(provide_principal),
            "s3_settings": Provide(provide_s3_settings, sync_to_thread=False),
        }

    @get(
        "/",
        name="reports:Report:list",
        guards=[require_roles("admin", "district_admin", "housing_worker")],
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
                in_scope_report_ids = (
                    select(IncidentReportLink.report_id)
                    .join(Incident, Incident.id == IncidentReportLink.incident_id)
                    .join(Assignment, Assignment.incident_id == Incident.id)
                    .where(
                        IncidentReportLink.is_active.is_(True),
                        Assignment.organization_id == scope.organization_id,
                    )
                )
                criteria.append(Report.id.in_(in_scope_report_ids))
            return await service.get_many(
                LimitOffset(limit=limit, offset=offset), *criteria, order_by=("received_at", True)
            )

    @get("/mine", name="reports:Report:mine", guards=[require_resident()])
    async def list_mine(
        self,
        service: NamedDependency[ReportService],
        principal: NamedDependency[Principal],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[Report]:
        with database_action("list", "reports.Report"):
            return await service.get_many(
                LimitOffset(limit=limit, offset=offset),
                Report.resident_id == principal.actor_id,
                order_by=("received_at", True),
            )

    @get("/{item_id:uuid}", name="reports:Report:get")
    async def get_item(self, item_id: FromPath[UUID], service: NamedDependency[ReportService]) -> Report:
        with database_action("get", "reports.Report"):
            return await service.get(item_id)

    @post(
        "/",
        dto=ReportCreateDTO,
        name="reports:Report:create",
        guards=[require_resident()],
    )
    async def create_item(
        self,
        data: DTOData[Report],
        service: NamedDependency[ReportService],
        principal: NamedDependency[Principal],
    ) -> Report:
        with database_action("create", "reports.Report"):
            report = data.create_instance()
            report.resident_id = principal.actor_id
            report.source_type = ReportSourceType.MAX
            return await service.create(report)

    @post(
        "/{item_id:uuid}/attachments",
        name="reports:Report:upload-attachment",
        guards=[require_resident()],
        return_dto=None,
    )
    async def upload_attachment(
        self,
        item_id: FromPath[UUID],
        data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
        service: NamedDependency[ReportService],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        s3_settings: NamedDependency[S3Settings],
    ) -> ReportAttachmentRead:
        with database_action("get", "reports.Report"):
            report = await service.get(item_id)
        if report.resident_id != principal.actor_id:
            raise PermissionDeniedException("Residents may only attach photos to their own reports")

        extension = ALLOWED_ATTACHMENT_CONTENT_TYPES.get(data.content_type)
        if extension is None:
            raise HTTPException(status_code=415, detail=f"Unsupported content type: {data.content_type}")

        body = await data.read()
        if len(body) > MAX_ATTACHMENT_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="File exceeds the 10 MB upload limit")

        checksum = hashlib.sha256(body).hexdigest()
        storage_key = f"reports/{item_id}/{uuid4()}{extension}"

        async with s3_settings.internal_client() as client:
            await client.put_object(
                Bucket=s3_settings.bucket, Key=storage_key, Body=body, ContentType=data.content_type
            )

        with database_action("create", "reports.ReportAttachment"):
            attachment = ReportAttachment(
                report_id=item_id,
                type=AttachmentType.IMAGE,
                storage_key=storage_key,
                original_name=data.filename,
                mime_type=data.content_type,
                size_bytes=len(body),
                checksum=checksum,
            )
            db_session.add(attachment)
            await db_session.commit()

        download_url = await s3_settings.presign_get_url(storage_key)
        return ReportAttachmentRead(
            id=str(attachment.id),
            original_name=attachment.original_name,
            mime_type=attachment.mime_type,
            size_bytes=attachment.size_bytes,
            created_at=attachment.created_at,
            download_url=download_url,
        )

    @get(
        "/{item_id:uuid}/attachments",
        name="reports:Report:list-attachments",
        guards=[require_resident()],
        return_dto=None,
    )
    async def list_attachments(
        self,
        item_id: FromPath[UUID],
        service: NamedDependency[ReportService],
        db_session: NamedDependency[AsyncSession],
        principal: NamedDependency[Principal],
        s3_settings: NamedDependency[S3Settings],
    ) -> Sequence[ReportAttachmentRead]:
        with database_action("get", "reports.Report"):
            report = await service.get(item_id)
        if report.resident_id != principal.actor_id:
            raise PermissionDeniedException("Residents may only view attachments on their own reports")

        with database_action("list", "reports.ReportAttachment"):
            result = await db_session.execute(
                select(ReportAttachment)
                .where(ReportAttachment.report_id == item_id)
                .order_by(ReportAttachment.created_at)
            )
            attachments = result.scalars().all()

        attachment_reads = []
        for attachment in attachments:
            download_url = await s3_settings.presign_get_url(attachment.storage_key)
            attachment_reads.append(
                ReportAttachmentRead(
                    id=str(attachment.id),
                    original_name=attachment.original_name,
                    mime_type=attachment.mime_type,
                    size_bytes=attachment.size_bytes,
                    created_at=attachment.created_at,
                    download_url=download_url,
                )
            )
        return attachment_reads
