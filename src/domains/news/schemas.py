"""Litestar contracts generated from the news domain's SQLAlchemy models."""

from typing import ClassVar

from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig

from src.domains.news.models import NewsPost


class NewsPostCreateDTO(SQLAlchemyDTO[NewsPost]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"id", "created_at", "updated_at", "author_operator_id", "organization_id"},
        forbid_unknown_fields=True,
    )


class NewsPostReadDTO(SQLAlchemyDTO[NewsPost]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig()


class NewsPostUpdateDTO(SQLAlchemyDTO[NewsPost]):
    config: ClassVar[SQLAlchemyDTOConfig] = SQLAlchemyDTOConfig(
        exclude={"id", "created_at", "updated_at", "author_operator_id", "organization_id"},
        partial=True,
        forbid_unknown_fields=True,
    )
