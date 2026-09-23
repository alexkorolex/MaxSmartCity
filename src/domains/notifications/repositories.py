from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from src.domains.notifications.models import Notification


class NotificationRepository(SQLAlchemyAsyncRepository[Notification]):
    model_type = Notification
