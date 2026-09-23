from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from src.domains.news.models import NewsPost


class NewsPostRepository(SQLAlchemyAsyncRepository[NewsPost]):
    model_type = NewsPost
