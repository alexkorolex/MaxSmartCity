"""Photos attached to a report (stored in S3, served through short-lived presigned URLs)."""

import hashlib
from collections.abc import Sequence
from typing import Annotated
from uuid import UUID, uuid4

from litestar import Controller, Router, get, post
from litestar.datastructures import UploadFile
from litestar.di import NamedDependency, Provide
from litestar.enums import RequestEncodingType
from litestar.exceptions import HTTPException, PermissionDeniedException
from litestar.params import Body, FromPath
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.logging import database_action
from src.domains.reports.controllers.reports import (
    authorize_report_access,
    provide_report_service,
    provide_s3_settings,
)
from src.domains.reports.enums import AttachmentType
from src.domains.reports.images import sniff_image_type
from src.domains.reports.models import ReportAttachment
from src.domains.reports.schemas import (
    ReportAttachmentRead,
    ReportReadDTO,
)
from src.domains.reports.services import (
    ReportService,
)
from src.domains.reports.storage import S3Settings
from src.security.dependency import provide_principal
from src.security.guards import require_resident
from src.security.principal import Principal

ALLOWED_ATTACHMENT_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024
MAX_ATTACHMENT_REQUEST_BYTES = MAX_ATTACHMENT_SIZE_BYTES + 256 * 1024


class ReportAttachmentController(Controller):
    """Upload and list a report's photos - the resident who filed it, or staff who may see it."""

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

    @post(
        "/{item_id:uuid}/attachments",
        name="reports:Report:upload-attachment",
        guards=[require_resident()],
        return_dto=None,
        request_max_body_size=MAX_ATTACHMENT_REQUEST_BYTES,
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

        if data.content_type not in ALLOWED_ATTACHMENT_CONTENT_TYPES:
            raise HTTPException(status_code=415, detail=f"Unsupported content type: {data.content_type}")

        body = await data.read()
        if len(body) > MAX_ATTACHMENT_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="File exceeds the 10 MB upload limit")
        content_type = sniff_image_type(body)
        if content_type is None:
            raise HTTPException(status_code=415, detail="The file is not a JPEG, PNG or WebP image")
        extension = ALLOWED_ATTACHMENT_CONTENT_TYPES[content_type]

        checksum = hashlib.sha256(body).hexdigest()
        storage_key = f"reports/{item_id}/{uuid4()}{extension}"

        async with s3_settings.internal_client() as client:
            await client.put_object(
                Bucket=s3_settings.bucket, Key=storage_key, Body=body, ContentType=content_type
            )

        with database_action("create", "reports.ReportAttachment"):
            attachment = ReportAttachment(
                report_id=item_id,
                type=AttachmentType.IMAGE,
                storage_key=storage_key,
                original_name=data.filename,
                mime_type=content_type,
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
        await authorize_report_access(db_session, report=report, principal=principal)

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
