from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from src.domains.notifications.models import Notification
from src.domains.notifications.repositories import NotificationRepository


class NotificationService(SQLAlchemyAsyncRepositoryService[Notification]):
    repository_type = NotificationRepository
