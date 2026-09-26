from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from src.common.models import Entity


class NewsPost(Entity):
    __tablename__ = "news_post"
    __table_args__ = ({"schema": "news"},)

    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    author_operator_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.operator_user.id"))
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.organization.id"), index=True)
