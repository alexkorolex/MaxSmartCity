from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from src.domains.notifications.models import Notification, OrganizationChannel
from src.domains.notifications.repositories import NotificationRepository, OrganizationChannelRepository


class NotificationService(SQLAlchemyAsyncRepositoryService[Notification]):
    repository_type = NotificationRepository


class OrganizationChannelService(SQLAlchemyAsyncRepositoryService[OrganizationChannel]):
    repository_type = OrganizationChannelRepository
