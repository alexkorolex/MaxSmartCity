from collections.abc import Sequence

from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy import ColumnElement, and_, func, or_, select

from src.common.enums import ActorType
from src.domains.identity.admin_scope import is_platform_admin
from src.domains.news.audience import resident_audience, staff_audience
from src.domains.news.models import NewsPost
from src.domains.news.repositories import NewsPostRepository
from src.security.principal import Principal


def _visibility(principal: Principal) -> list[ColumnElement[bool]]:
    if principal.actor_type is ActorType.OPERATOR and is_platform_admin(principal):
        return []
    if principal.actor_type is ActorType.OPERATOR:
        return [
            or_(
                and_(NewsPost.is_published.is_(True), staff_audience(principal.organization_id)),
                NewsPost.author_operator_id == principal.actor_id,
            )
        ]
    return [NewsPost.is_published.is_(True), resident_audience(principal.actor_id)]


class NewsPostService(SQLAlchemyAsyncRepositoryService[NewsPost]):
    repository_type = NewsPostRepository

    async def feed(self, principal: Principal, *, limit: int, offset: int) -> Sequence[NewsPost]:
        statement = (
            select(NewsPost)
            .where(*_visibility(principal))
            .order_by(func.coalesce(NewsPost.published_at, NewsPost.created_at).desc(), NewsPost.id)
            .limit(limit)
            .offset(offset)
        )
        return (await self.repository.session.scalars(statement)).all()
