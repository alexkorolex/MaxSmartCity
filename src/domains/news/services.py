from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from src.domains.news.models import NewsPost
from src.domains.news.repositories import NewsPostRepository


class NewsPostService(SQLAlchemyAsyncRepositoryService[NewsPost]):
    repository_type = NewsPostRepository
