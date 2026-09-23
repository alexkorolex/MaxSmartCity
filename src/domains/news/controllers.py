from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from advanced_alchemy.filters import LimitOffset
from litestar import Controller, Router, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.dto import DTOData
from litestar.exceptions import PermissionDeniedException
from litestar.params import FromPath, Parameter
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.enums import ActorType
from src.database.logging import database_action
from src.domains.identity.admin_scope import is_platform_admin
from src.domains.news.models import NewsPost
from src.domains.news.schemas import NewsPostCreateDTO, NewsPostReadDTO, NewsPostUpdateDTO
from src.domains.news.services import NewsPostService
from src.security.dependency import provide_principal
from src.security.guards import require_staff
from src.security.principal import Principal


def provide_newspost_service(db_session: NamedDependency[AsyncSession]) -> NewsPostService:
    return NewsPostService(session=db_session, auto_commit=True)


class NewsController(Controller):
    path = "/news"
    tags = ("news",)
    return_dto = NewsPostReadDTO

    def __init__(self, owner: Router) -> None:
        super().__init__(owner)
        self.dependencies = {
            "service": Provide(provide_newspost_service, sync_to_thread=False),
            "principal": Provide(provide_principal),
        }

    @get("/", name="news:NewsPost:list")
    async def list_items(
        self,
        service: NamedDependency[NewsPostService],
        principal: NamedDependency[Principal],
        limit: Annotated[int, Parameter(ge=1, le=100)] = 50,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> Sequence[NewsPost]:
        # Residents (and any non-staff caller) always get published-only, unchanged. Staff
        # get broader visibility: `admin` sees every post (published or draft); a
        # district_admin/housing_worker sees published posts plus their *own* drafts.
        with database_action("list", "news.NewsPost"):
            if principal.actor_type is ActorType.OPERATOR and is_platform_admin(principal):
                criteria = ()
            elif principal.actor_type is ActorType.OPERATOR:
                criteria = (
                    or_(NewsPost.is_published.is_(True), NewsPost.author_operator_id == principal.actor_id),
                )
            else:
                criteria = (NewsPost.is_published.is_(True),)
            return await service.get_many(
                LimitOffset(limit=limit, offset=offset),
                *criteria,
                order_by=("published_at", True),
            )

    @get("/{item_id:uuid}", name="news:NewsPost:get")
    async def get_item(
        self,
        item_id: FromPath[UUID],
        service: NamedDependency[NewsPostService],
        principal: NamedDependency[Principal],
    ) -> NewsPost:
        # `principal` is unused beyond dependency resolution: any authenticated caller
        # may fetch a post by id, published or not.
        with database_action("get", "news.NewsPost"):
            return await service.get(item_id)

    @post(
        "/",
        dto=NewsPostCreateDTO,
        name="news:NewsPost:create",
        guards=[require_staff()],
    )
    async def create_item(
        self,
        data: DTOData[NewsPost],
        service: NamedDependency[NewsPostService],
        principal: NamedDependency[Principal],
    ) -> NewsPost:
        with database_action("create", "news.NewsPost"):
            # Authorship always comes from the authenticated principal, never trusted from
            # client input - otherwise a non-admin could post a draft under someone else's
            # name and see it in their own "published + own drafts" listing regardless.
            post = data.create_instance()
            post.author_operator_id = principal.actor_id
            return await service.create(post)

    @patch(
        "/{item_id:uuid}",
        dto=NewsPostUpdateDTO,
        name="news:NewsPost:update",
        guards=[require_staff()],
    )
    async def update_item(
        self,
        item_id: FromPath[UUID],
        data: DTOData[NewsPost],
        service: NamedDependency[NewsPostService],
        principal: NamedDependency[Principal],
    ) -> NewsPost:
        with database_action("update", "news.NewsPost"):
            # Same ownership boundary as the listing: `admin` may edit any post, a
            # district_admin/housing_worker only their own - otherwise one org could
            # publish, alter, or unpublish another org's (or the admin's) announcement.
            existing = await service.get(item_id)
            if not is_platform_admin(principal) and existing.author_operator_id != principal.actor_id:
                raise PermissionDeniedException("Cannot modify another author's news post")
            return await service.update(data, item_id=item_id)

    @delete(
        "/{item_id:uuid}",
        return_dto=None,
        name="news:NewsPost:delete",
        guards=[require_staff()],
    )
    async def delete_item(
        self,
        item_id: FromPath[UUID],
        service: NamedDependency[NewsPostService],
        principal: NamedDependency[Principal],
    ) -> None:
        with database_action("delete", "news.NewsPost"):
            existing = await service.get(item_id)
            if not is_platform_admin(principal) and existing.author_operator_id != principal.actor_id:
                raise PermissionDeniedException("Cannot delete another author's news post")
            await service.delete(item_id)
