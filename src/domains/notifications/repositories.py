from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from src.domains.notifications.models import Notification, OrganizationChannel


class NotificationRepository(SQLAlchemyAsyncRepository[Notification]):
    model_type = Notification


class OrganizationChannelRepository(SQLAlchemyAsyncRepository[OrganizationChannel]):
    model_type = OrganizationChannel
